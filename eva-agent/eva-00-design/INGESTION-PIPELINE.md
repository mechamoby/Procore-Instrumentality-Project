# EVA-00: Document Ingestion Pipeline

## Overview

The ingestion pipeline transforms raw files (PDFs, images, Procore API payloads) into structured database records + vector embeddings. It's the critical path that turns a GC's decades of project history into queryable institutional knowledge.

---

## Pipeline Architecture

```
                    ┌─────────────┐     ┌──────────────┐
                    │ Procore API │     │ Manual Upload │
                    │  Sync Agent │     │  (Web UI/CLI) │
                    └──────┬──────┘     └──────┬────────┘
                           │                   │
                           ▼                   ▼
                    ┌──────────────────────────────┐
                    │      Ingestion Queue          │
                    │      (Redis Stream)           │
                    │  XADD eva00:ingest:queue ...  │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │    Stage 1: RECEIVE & STORE   │
                    │  - Deduplicate (SHA-256)      │
                    │  - Store file to NVMe         │
                    │  - Create DB record           │
                    │  - Generate thumbnail          │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │    Stage 2: PARSE & EXTRACT   │
                    │  - PDF → text (PyMuPDF/fitz)  │
                    │  - DWG → DXF (ODA Converter)  │
                    │  - DXF → structured (ezdxf)   │
                    │  - OCR if scanned (Tesseract) │
                    │  - Table extraction            │
                    │  - Metadata extraction         │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │    Stage 3: CLASSIFY & CHUNK  │
                    │  - Identify document type      │
                    │  - Apply chunking strategy     │
                    │  - Extract CSI references       │
                    │  - Link to related entities     │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │    Stage 4: EMBED             │
                    │  - Generate vector embeddings  │
                    │  - Store in document_chunks    │
                    │  - Update ingestion status     │
                    └──────────────────────────────┘
```

---

## Stage 1: Receive & Store

### Input Sources

**Procore API sync:**
- Sync agent polls Procore REST API (see SYNC-STRATEGY.md)
- Receives JSON payloads + file download URLs
- Downloads files to local storage

**Manual upload:**
- Web UI or CLI tool for bulk import
- Drag-and-drop PDFs, plan sets, historical project archives
- Accepts: PDF, DOCX, XLSX, JPG/PNG/TIFF, DWG, DXF, RVT (metadata only), P6 XML

**PDF log import (bulk historical data):**
- Client exports RFI/Submittal logs as PDFs from Procore
- PyMuPDF parses all text into structured data ($0, <1 second for 98 pages)
- Bypasses API rate limits for initial data load
- See SYNC-STRATEGY.md "Alternative: PDF Log Import" section

### File Deduplication

```
1. Compute SHA-256 hash of incoming file
2. Check documents.file_hash for existing match
3. If duplicate:
   a. Same project → skip (log as duplicate)
   b. Different project → create new DB record, point to same file path
4. If new → store file
```

### File Storage Layout

```
/data/files/
├── {project_uuid}/
│   ├── drawings/
│   │   ├── {file_hash}.pdf
│   │   └── ...
│   ├── submittals/
│   ├── rfis/
│   ├── daily_reports/
│   ├── photos/
│   │   ├── {file_hash}.jpg
│   │   └── ...
│   ├── specs/
│   ├── schedules/
│   └── other/
├── company/                    # company-wide docs (not project-specific)
│   ├── standards/
│   └── templates/
└── thumbs/
    └── {file_hash}_thumb.webp  # 400px wide thumbnails
```

### Thumbnail Generation

- **PDFs/drawings**: First page rendered at 400px width via `pdftoppm` → WebP
- **Photos**: ImageMagick resize to 400px width → WebP
- Generated asynchronously, non-blocking
- Stored in `thumbs/` directory, path saved to entity's `thumbnail_path`

---

## Stage 2: Parse & Extract

### Document Text Extraction

**Decision tree (UPDATED based on real testing):**

```
What is the file format?
├── DWG (binary CAD)
│   └── ODA File Converter → DXF → ezdxf pipeline (see below)
├── DXF (open CAD)
│   └── ezdxf → structured extraction (layers, rooms, grids, text) — $0, instant, ~99% accuracy
├── PDF
│   ├── CAD-generated (has embedded text)?
│   │   └── PyMuPDF (fitz) — $0, instant, 100% accuracy on text content
│   │       NOTE: PyMuPDF outperforms pdftotext for construction drawings.
│   │       Tested: correctly extracted NGVD elevations, grid dimensions, room names.
│   │       AI vision FAILED on same data (wrong dimension: 30'-0" vs actual 20'-7 29/32")
│   └── Scanned/image-based?
│       └── Tesseract OCR with:
│           - Preprocessing: deskew, denoise (ImageMagick)
│           - Language: eng
│           - PSM mode 3 (fully automatic page segmentation)
│           - For drawings: PSM mode 11 (sparse text)
├── DOCX → python-docx
└── XLSX → openpyxl
```

**CRITICAL DESIGN PRINCIPLE:** Text extraction first, AI vision LAST RESORT.
In direct A/B testing, PyMuPDF text extraction was faster, cheaper ($0), and MORE ACCURATE
than AI vision models on CAD-generated construction drawings. AI vision should only be used
for scanned/raster drawings where no text layer exists.

**Libraries/tools (all local, containerized):**
- `PyMuPDF` (fitz) — primary PDF parser (text + link extraction from CAD-generated PDFs)
- `ezdxf` — DXF/CAD structured data extraction (layers, entities, text, blocks)
- `ODA File Converter` — DWG→DXF headless conversion (Docker service)
- `poppler-utils` (pdftoppm) — PDF page rendering for thumbnails
- `pdfplumber` — table boundary detection for schedule extraction
- `tesseract-ocr` 5.x — OCR fallback for scanned documents only
- `python-docx` for DOCX parsing
- `openpyxl` for XLSX parsing

### DWG/DXF Extraction Pipeline (NEW)

CAD files provide dramatically superior structured data vs PDFs. This is the competitive moat.

```
DWG file received
  → ODA File Converter (headless Linux) → DXF output (~2-5 sec per file)
  → ezdxf parses DXF:
     → Extract all layers (discipline separation: A-DOOR, S-STRS, P-SANR-FIXT, etc.)
     → Extract text entities (room names, identifiers, notes)
     → Extract block references (doors, windows, equipment symbols)
     → Extract dimension entities (measurements, grid spacing)
     → Extract structural grid (column lines A-Z, 1-N)
  → Structure into JSON per sheet
  → Store in PostgreSQL (drawings table + document_chunks for search)
  → $0 cost, instant processing, ~99% accuracy
```

**Tested results (14 DXF files from 1750 project):**
- 24-51 layers per sheet, full discipline separation
- Room identifiers: Residential Lobby (L01-024), Retail (L01-014), Mail Room, etc.
- Structural grid: A-D, 2-9 fully readable
- Processing time: milliseconds per file

**Limitation:** DXF floor plans lack elevation data (NGVD). That data is on:
- Structural sections (A-200 series) → need PDF extraction for these
- Civil/site sheets (C-series)
- General notes pages
EVA-00 must correlate data across multiple sheets and formats to answer elevation queries.

### Construction-Specific Extraction

**Drawing title blocks:**
- For CAD-generated PDFs: PyMuPDF text extraction gets title block data with 100% accuracy
- Regex patterns for: drawing number, title, revision, date, discipline
- Common formats: `A-201`, `S-100.1`, `M-401`, `E-001`
- Title block typically in lower-right corner
- For scanned drawings only: crop and OCR that region specifically
- For DXF: title block data is in dedicated layers/blocks — extract directly

**Spec sections:**
- Parse CSI MasterFormat section numbers: `XX XX XX` pattern
- Extract section title from header
- Split content by subsection (Part 1 - General, Part 2 - Products, Part 3 - Execution)

**Submittal packages:**
- Extract cover sheet data (submittal number, spec reference, contractor)
- Product data sheets: manufacturer, model, specifications table

---

## Stage 3: Classify & Chunk

### Document Classification

For manually uploaded docs without explicit type:

1. **Filename patterns**: `RFI-023.pdf` → RFI, `Daily Report 2024-01-15.pdf` → daily report
2. **Content-based**: Check first page for keywords ("REQUEST FOR INFORMATION", "SUBMITTAL", "MEETING MINUTES", "DAILY REPORT")
3. **Fallback**: Classify as `other`, flag for manual review

### Chunking Strategies by Document Type

| Document Type | Strategy | Target Chunk Size | Overlap |
|---|---|---|---|
| **Specifications** | Split by CSI section/subsection | 800-1200 tokens | 100 tokens |
| **Drawings** | One chunk per drawing (metadata + OCR text) | Varies | None |
| **Submittals** | One chunk per submittal (description + all review comments concatenated) | Varies | None |
| **RFIs** | One chunk per RFI (question + official answer + key responses) | Varies | None |
| **Daily Reports** | One chunk per report (all narrative fields concatenated) | Varies | None |
| **Meeting Minutes** | One chunk per agenda item | 400-800 tokens | None |
| **Change Orders** | One chunk per CO (description + justification) | Varies | None |
| **Photos** | One chunk per photo (metadata + description + tags) | Short | None |
| **General Documents** | Recursive character split respecting paragraphs | 1000 tokens | 200 tokens |

### Chunk Content Template

Each chunk's `content` field is formatted for maximum embedding quality:

```
# RFI Example:
"Project: Riverside Medical Center | RFI #023 | Spec: 03 30 00 Cast-in-Place Concrete |
Subject: Concrete mix design clarification for post-tensioned slabs |
Question: The spec calls for 5000 PSI at 28 days but the structural drawings note
6000 PSI for the PT slabs. Please clarify the required strength. |
Answer: Use 6000 PSI for all post-tensioned elements per structural drawings. Spec
section 03 30 00 will be revised via ASI. |
Status: Closed | Date: 2024-03-15"
```

Prefix with project name + document type + key identifiers for embedding context.

### Cross-Reference Extraction

During chunking, scan content for references to other entities:
- Drawing numbers (`A-201`, `S-100`) → link to `drawings` table
- Spec sections (`03 30 00`, `Section 09 91 23`) → link to `spec_sections`
- RFI/Submittal numbers → link to respective tables
- Company names → fuzzy match against `companies` table

Store cross-references as metadata in the chunk and as explicit relationships where possible.

---

## Stage 4: Embed

### Embedding Generation

```python
# Pseudocode for embedding pipeline
for chunk in chunks_to_embed:
    # Prefix with search type hint for nomic-embed
    text = f"search_document: {chunk.content}"
    
    # Call local Ollama instance
    embedding = ollama.embeddings(
        model="nomic-embed-text",
        prompt=text
    )
    
    chunk.embedding = embedding
    chunk.embedded_at = now()
    chunk.embedding_model = "nomic-embed-text-v1.5"
```

### Batch Processing

- Pull chunks from Redis queue in batches of 32
- Process through Ollama embedding endpoint
- Bulk INSERT into `document_chunks` table
- On GPU (RTX 4060): ~500 chunks/minute
- On CPU only: ~50 chunks/minute

### Re-embedding

Triggered when:
- Embedding model is upgraded (new model version)
- Chunk content is updated (e.g., RFI answer added to an RFI that was previously open)
- Manual re-index requested

Process: Set `embedded_at = NULL` on affected chunks → they re-enter the embedding queue.

---

## Error Handling

| Error | Handling |
|---|---|
| PDF parse failure | Retry with OCR fallback. If both fail, mark `ingestion_status = 'failed'`, store error in `ingestion_error`. Alert operator. |
| Corrupt file | Store file but mark failed. Log hash for dedup so we don't retry same corrupt file. |
| Embedding service down | Chunks stay in queue (Redis persistent). Stage 1-3 complete independently. Embeddings catch up when service recovers. |
| Duplicate detection | Log and skip. No error state. |
| Out of disk space | Alert operator at 80% threshold. Pipeline pauses at 95%. |

---

## Performance Targets

| Metric | Target |
|---|---|
| Single PDF ingestion (text-based, 10 pages) | < 5 seconds (parse + chunk) |
| Single PDF ingestion (scanned, 10 pages) | < 30 seconds (OCR) |
| Single DXF ingestion (CAD file) | < 1 second (structured extraction) |
| DWG → DXF conversion | ~2-5 seconds per file |
| PDF log parsing (98-page RFI log, 186 RFIs) | < 1 second |
| Embedding generation (per chunk) | < 200ms (GPU) / < 2s (CPU) |
| Bulk import (1000 documents) | < 2 hours (with GPU) |
| Bulk API upload (134 RFIs + 328 replies) | ~8 min (rate-limited by Procore) |
| Initial project history load (5 years, ~5000 docs) | < 8 hours overnight |

---

## Initial Data Load Process

For onboarding a new GC client:

1. **Connect Procore** — Configure API credentials, select projects to sync
2. **Full sync** — Pull all historical data from Procore API (rate-limited, may take hours)
3. **Bulk upload** — Client provides any docs not in Procore (old archives, local files)
4. **Processing** — Pipeline processes everything through stages 1-4
5. **Verification** — Dashboard shows ingestion progress per project, flags failures
6. **Index rebuild** — After bulk load, rebuild IVFFlat vector index for optimal performance:
   ```sql
   REINDEX INDEX idx_chunks_embedding;
   ```
7. **Ready** — EVA agents can now query the knowledge base
