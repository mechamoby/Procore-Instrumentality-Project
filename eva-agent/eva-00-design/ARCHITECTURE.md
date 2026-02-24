# EVA-00: The Master Clerk & Project Historian — System Architecture

## Overview

EVA-00 is the central knowledge base for the Evangelion construction AI platform. It ingests, indexes, and serves all project data — past and present — so that downstream EVA agents (submittals, RFIs, scheduling, etc.) can query institutional knowledge instantly.

**Core principle:** Data never leaves the client's building. EVA-00 runs entirely on a local mini-server at the GC's office.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT'S LOCAL NETWORK                       │
│                                                                     │
│  ┌──────────┐     ┌──────────────────────────────────────────────┐  │
│  │ Procore  │────▶│              EVA-00 SERVER                   │  │
│  │  (Cloud) │◀────│                                              │  │
│  └──────────┘     │  ┌─────────────┐   ┌─────────────────────┐  │  │
│                   │  │  Sync Agent │   │  Ingestion Pipeline │  │  │
│  ┌──────────┐     │  │  (polling/  │   │  (PDF parse, OCR,   │  │  │
│  │  Manual  │────▶│  │  webhooks)  │   │  chunking, embed)   │  │  │
│  │  Upload  │     │  └──────┬──────┘   └──────────┬──────────┘  │  │
│  └──────────┘     │         │                     │              │  │
│                   │         ▼                     ▼              │  │
│                   │  ┌──────────────────────────────────────┐   │  │
│                   │  │           PostgreSQL 16              │   │  │
│                   │  │  ┌────────────┐  ┌───────────────┐  │   │  │
│                   │  │  │ Relational │  │   pgvector     │  │   │  │
│                   │  │  │   Tables   │  │  Embeddings    │  │   │  │
│                   │  │  └────────────┘  └───────────────┘  │   │  │
│                   │  │  ┌────────────────────────────────┐  │   │  │
│                   │  │  │   Full-Text Search (tsvector)  │  │   │  │
│                   │  │  └────────────────────────────────┘  │   │  │
│                   │  └──────────────────────────────────────┘   │  │
│                   │                                              │  │
│                   │  ┌──────────┐   ┌──────────────────────┐    │  │
│                   │  │  Redis   │   │   File Storage       │    │  │
│                   │  │  Cache   │   │   (NVMe /data/files) │    │  │
│                   │  └──────────┘   └──────────────────────┘    │  │
│                   │                                              │  │
│                   │  ┌──────────────────────────────────────┐   │  │
│                   │  │          EVA-00 Query API            │   │  │
│                   │  │     (REST + gRPC, port 8400)         │   │  │
│                   │  └──────────────┬───────────────────────┘   │  │
│                   └─────────────────┼────────────────────────────┘  │
│                                     │                               │
│                   ┌─────────────────┼──────────────────┐            │
│                   │                 │                  │            │
│               ┌───▼───┐      ┌─────▼─────┐     ┌─────▼─────┐      │
│               │EVA-01 │      │  EVA-02   │     │  EVA-03   │      │
│               │Submit │      │   RFI     │     │ Schedule  │      │
│               │Agent  │      │  Agent    │     │  Agent    │      │
│               └───────┘      └───────────┘     └───────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Hardware Requirements

**Minimum spec (local mini-server):**
- CPU: AMD Ryzen 9 / Intel i9 (16+ cores) — embedding generation is CPU-heavy if no GPU
- RAM: 64GB DDR5
- Storage: 2TB NVMe (primary) + 4TB NVMe or SSD (file storage)
- GPU (optional but recommended): NVIDIA RTX 4060+ for local embedding model inference
- Network: Gigabit Ethernet to office LAN

**Storage budget estimate (per client):**
| Data Type | Est. per Project | 20 Projects |
|-----------|-----------------|-------------|
| Drawings (PDFs) | 2-5 GB | 40-100 GB |
| Photos | 1-3 GB | 20-60 GB |
| Documents (specs, reports) | 500 MB | 10 GB |
| Database (structured + vectors) | 200 MB | 4 GB |
| Thumbnails/previews | 100 MB | 2 GB |
| **Total** | | **~80-180 GB** |

---

## Container Architecture (Docker Compose)

```yaml
services:
  postgres:        # PostgreSQL 16 + pgvector
  redis:           # Cache layer + rate limiter + job queues
  eva00-api:       # Query API server (Python/FastAPI — pragmatic, fast to build)
  eva00-sync:      # Procore sync agent (Python — reuses proven procore client code)
  eva00-ingest:    # Document ingestion workers (Python — PyMuPDF, ezdxf, pdfplumber)
  eva00-embed:     # Embedding generation service (Ollama)
  oda-converter:   # DWG→DXF conversion service (ODA File Converter, headless)
```

All services on a single Docker host. No orchestrator needed — this is one machine.

> **Note on language choice:** Original design said Rust or Go for the API. After hands-on
> testing, Python is the pragmatic choice for Phase 1. The entire extraction pipeline
> (PyMuPDF, ezdxf, pdfplumber, Procore client) is Python. Adding a Go/Rust API means
> maintaining two codebases. Python FastAPI is fast enough for single-server local deployment.
> Optimize later only if query latency becomes an issue.

---

## Core Components

### 1. PostgreSQL 16 + pgvector

The single source of truth. Stores:
- **Relational data**: Projects, submittals, RFIs, contacts, companies, drawings, specs, schedules, daily reports, meeting minutes, change orders
- **Full-text search**: `tsvector` columns on all text-heavy fields (RFI questions/answers, submittal descriptions, meeting minutes, daily report narratives)
- **Vector embeddings**: `vector(1024)` columns in a dedicated `document_chunks` table via pgvector, enabling semantic similarity search

### 2. Redis Cache

- Hot query results (TTL 5-15 min)
- Procore sync state (last poll timestamps, cursor positions)
- Rate limiter for API calls
- Session/auth tokens for EVA agents

### 3. File Storage

- Direct NVMe filesystem at `/data/files/`
- Path convention: `/data/files/{project_id}/{doc_type}/{file_hash}.{ext}`
- Content-addressed storage: SHA-256 hash deduplication
- Thumbnails generated on ingest: `/data/files/{project_id}/thumbs/{file_hash}_thumb.webp`

### 4. Embedding Service

- **Model**: `nomic-embed-text-v1.5` (768-dim) or `mxbai-embed-large-v1` (1024-dim) via Ollama
- Runs locally — no API calls, no data leaving the building
- Processes document chunks through a queue (Redis-backed)
- Batch processing: 32 chunks per batch for throughput

### 5. Query API

- REST API on port 8400
- Endpoints for structured queries, semantic search, and hybrid search
- Authentication via API keys (one per EVA agent)
- Rate limiting per agent

---

## Embedding Strategy

### Model Selection

**Primary: `nomic-embed-text-v1.5`** via Ollama (local inference)
- 768 dimensions (good balance of quality vs storage)
- 8192 token context window (critical for long construction docs)
- Matryoshka embeddings — can truncate to 256-dim for faster approximate search
- Apache 2.0 license

**Why not OpenAI/cloud embeddings?** Data never leaves the building. Period.

### Chunking Strategy for Construction Documents

Construction docs are unique — they have:
- Numbered sections (CSI MasterFormat divisions)
- Tables (submittal logs, schedules)
- References to other documents (spec section → drawing number)
- Legal/contractual language that must not be split mid-clause

**Chunking approach:**
1. **Spec sections**: Split by CSI section number (e.g., Section 03 30 00 - Cast-in-Place Concrete). Each section = 1-3 chunks depending on length.
2. **Drawings**: Metadata chunk (drawing number, title, discipline, revision) + OCR text chunk from title block + any extracted notes.
3. **RFIs/Submittals**: One chunk per item (question + answer together for RFIs; description + review comments together for submittals). Keep the context unified.
4. **Meeting minutes**: Split by agenda item / topic header.
5. **Daily reports**: One chunk per report (they're typically short).
6. **General documents**: Recursive character splitting at 1000 tokens with 200 token overlap, respecting paragraph boundaries.

**Chunk metadata stored alongside each embedding:**
- `project_id`, `document_id`, `document_type`
- `section_number` (CSI code if applicable)
- `page_number`, `chunk_index`
- `created_at`, `updated_at`

### Vector Index

```sql
CREATE INDEX idx_chunks_embedding ON document_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 300);
```

IVFFlat with ~300 lists for datasets up to ~500K chunks. Rebuild index periodically as data grows. Switch to HNSW if query latency becomes an issue:

```sql
CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);
```

---

## Security Model

- All services on localhost / Docker bridge network only
- No ports exposed to WAN
- EVA agents authenticate via API key (stored in Redis, rotated monthly)
- PostgreSQL: role-per-service with minimal privileges
- File storage: OS-level permissions, no public access
- Audit log table for all data access
- Encryption at rest via LUKS on the NVMe volume

---

## Monitoring & Maintenance

- **Health checks**: Docker healthchecks on all containers
- **Metrics**: Prometheus + Grafana (optional, lightweight)
- **Disk usage alerts**: Threshold at 80% capacity
- **Backup**: Nightly pg_dump + rsync of file storage to secondary drive
- **Vector index rebuild**: Weekly cron job during off-hours
- **Log rotation**: 7-day retention, structured JSON logs

---

## Scalability Path

EVA-00 is designed for a single-server deployment per client. If a client's data grows beyond one server:

1. **Phase 1** (current): Single server, all-in-one Docker Compose
2. **Phase 2**: Separate file storage to a NAS on local network
3. **Phase 3**: Read replicas for PostgreSQL if query volume demands it

For now, Phase 1 handles 20+ projects with thousands of documents comfortably on the specified hardware.

---

## Lessons Learned from Sandbox Testing (Feb 2026)

These findings are from hands-on Procore API integration and real drawing extraction tests.
They directly impact EVA-00's design and should be referenced during implementation.

### Procore API Constraints

1. **Rate limit is 100 requests per ~60s window** (not 3,600/hr as documented).
   The `X-Rate-Limit-Limit: 100` header is authoritative. Budget sync schedules accordingly.
   Connection errors occur if you exceed this — implement exponential backoff + retry.

2. **`drawings` endpoint 404s — use `drawing_revisions` instead.** This is a Procore bug/quirk
   that has persisted across API versions. Always use the revisions endpoint.

3. **Vendor creation requires `{"vendor": {...}}` NOT `{"company": {...}}`.**
   The API silently rejects the wrong wrapper key.

4. **No spec section list/create endpoint exists.** Spec sections can only be created via
   the Procore UI. There is no API endpoint to list or search them by name/number. If you
   need spec section IDs, the user must grab them from the Procore UI URL manually, or you
   must brute-force scan ID ranges (impractical at 100 req/min).

5. **API-created users cannot be submittal/RFI managers or participants.** Only users who
   were created through the Procore UI (built-in sandbox users) are accepted for workflow
   roles. API-created users are silently rejected for `rfi_manager_id`, `assignee_ids`, etc.

6. **Submittal/RFI status cannot be changed via API.** PATCH requests that include `status`
   are accepted (200 OK) but the status field is silently ignored. You cannot close, approve,
   or advance workflow via the API. Status data is read-only for sync purposes.

7. **File attachments may not persist on sandbox.** Upload requests return 200/201 but
   attachments don't appear on the entity. This may be sandbox-specific — test on production.

8. **RFI replies require `{"reply": {"body": ...}}` wrapper.** Without the `reply` wrapper,
   the API returns 400 "param is missing." Submittal attachments use
   `submittal[attachments][]` as multipart form field.

9. **OAuth refresh tokens expire after extended inactivity.** If the Procore API is not used
   for days/weeks, the refresh token becomes invalid and requires full re-authorization.
   **Solution:** Run a keepalive cron every 12 hours that refreshes the token.
   See `scripts/procore-keepalive.py`.

10. **Cover sheet PDFs contain embedded signed download URLs.** When exported from Procore,
    submittal cover sheets contain clickable links (extractable via PyMuPDF) that point to
    the original attachment files on `storage.procore.com`. These links are long-lived.
    This enables a zero-API-cost bulk import pipeline: export cover sheets → parse links →
    download attachments directly.

### Drawing & Document Extraction

11. **Text extraction (PyMuPDF) dramatically outperforms AI vision on CAD-generated PDFs.**
    In direct testing, PyMuPDF extracted NGVD elevations (10'-1") and grid dimensions
    (20'-7 29/32") with 100% accuracy, $0 cost, in milliseconds. AI vision models gave
    incorrect answers (30'-0" for a 20'-7 29/32" dimension) at higher cost and latency.
    **Design implication:** Tier 0 and Tier 1 extraction should NEVER use AI vision for
    CAD-generated PDFs. Reserve AI for scanned/raster-only drawings.

12. **DXF files (via ezdxf) provide perfect structured data extraction.** 14 test files from
    the 1750 project parsed instantly: room identifiers (L01-024 "Residential Lobby"), layer
    separation by discipline (A-DOOR, S-STRS, P-SANR-FIXT, E-LITE-EQPM), structural grids
    (A-D, 2-9), all at $0 cost. DXF/CAD > PDF for structured extraction (~99% vs ~80%).

13. **DXF files lack cross-sheet data.** Floor plans and RCPs don't contain elevation data
    (NGVD) — that's on structural sections (A-200 series), civil sheets, and general notes.
    EVA-00 must correlate data across multiple sheets to answer elevation questions.

14. **DWG binary format requires ODA File Converter or LibreDWG.** ezdxf reads DXF only.
    LibreDWG compile fails on machines with <64GB RAM (OOM). ODA File Converter runs headless
    on Linux and converts in seconds. Include ODA in the Docker stack for NERV deployments.

15. **RFI log PDFs parse cleanly with PyMuPDF text extraction.** A 98-page, 186-RFI log
    was parsed into structured data (questions, answers, dates, authors, cost codes, statuses)
    in under 1 second. The PDF table format is messy (multiline cells, page breaks) but
    deterministic patterns (Q:/A: markers, attachment filenames with RFI numbers) make
    reliable parsing possible. This confirms the bulk import pipeline is viable at $0 cost.

### Data Migration & Onboarding

16. **Initial data load is Procore-rate-limited, not compute-limited.** Loading 134 RFIs
    with 328 responses took ~8 minutes, of which ~7 minutes was rate limit pauses. The actual
    parsing and API call construction was negligible. Plan for overnight unattended migrations.

17. **Batch operations need connection-aware throttling.** The first batch upload crashed
    with `ConnectionError: Max retries exceeded` from sending requests too fast. Sleep between
    requests (minimum 0.5s per request, with 65s pauses every 85 requests) prevents this.

18. **PDF log parsing as an alternative to API extraction.** For onboarding existing clients,
    exporting RFI/submittal logs as PDFs from Procore and parsing them locally is faster and
    cheaper than pulling each item via API. The PDF contains all text data (questions, answers,
    dates, people) minus attachments. Use API sync for ongoing updates; PDF parse for initial
    bulk load.

### Embedding & Search Implications

19. **RFI chunks should include full Q&A threads, not just questions.** Our RFI extraction
    confirmed that answers often contain critical information (specific dimensions, product
    approvals, code references). The chunk template in QUERY-PATTERNS.md is correct — always
    concatenate question + all answers into a single chunk for embedding.

20. **Cost code / CSI section data is extractable from PDF logs.** The metadata table in
    Procore exports includes cost codes (e.g., "16-0500 - Electrical") that map to CSI
    divisions. This provides free cross-referencing between RFIs and spec sections.
