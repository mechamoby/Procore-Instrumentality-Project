# Implementation Plan: Drawing Analysis for EVA

## Phased Build Plan

---

## Phase 1: Foundation (Weeks 1-4)

**Goal:** Every uploaded drawing is indexed, searchable, and browseable. Tier 0 complete.

### Week 1-2: Core Infrastructure
- [ ] **Drawing storage service** — S3-compatible storage for original PDFs + generated assets
- [ ] **Database schema** for drawings (see below)
- [ ] **PDF ingestion worker** — accepts PDF upload, splits into pages, stores
- [ ] **PyMuPDF text extraction** — extract all text with coordinates per page
- [ ] **Thumbnail generation** — 1000px-wide PNG per sheet

### Week 3-4: Title Block & Classification
- [ ] **Title block region detection** — heuristic (bottom-right quadrant) + VLM fallback
- [ ] **Title block field extraction** — sheet number, title, discipline, revision, scale
- [ ] **Sheet type classification** — plan/elevation/section/detail/schedule/notes
- [ ] **Full-text search index** — Postgres full-text or Meilisearch on extracted text
- [ ] **Drawing viewer UI** — thumbnail grid, sheet browser, text search

### Deliverable
Upload a PDF drawing set → get a browseable, searchable sheet catalog in <30 seconds for a 500-sheet set.

**Cost:** Nearly free (PyMuPDF is local, VLM fallback ~$1/set)

---

## Phase 2: Schedule Extraction (Weeks 5-8)

**Goal:** Reliably extract door, window, finish, and equipment schedules into structured data.

### Week 5-6: Extraction Pipeline
- [ ] **Schedule sheet detection** — flag sheets classified as "schedule" in Phase 1
- [ ] **pdfplumber table extraction** — primary path for vector PDFs
- [ ] **VLM table extraction** — Gemini 2.5 Flash, fallback path
- [ ] **Combined pipeline** — try pdfplumber, fall back to VLM, VLM-validate low-confidence results

### Week 7-8: Normalization & Storage
- [ ] **Header normalization** — map varied column names to canonical names
- [ ] **Schedule type classification** — door/window/finish/equipment/hardware
- [ ] **Abbreviation dictionary** — construction abbreviation expansion
- [ ] **Validation rules** — range checks, enum checks per schedule type
- [ ] **Confidence scoring** — flag low-confidence extractions
- [ ] **Multi-page schedule merging**
- [ ] **Human review UI** — show extracted table with original drawing side-by-side, allow corrections
- [ ] **Schedule query API** — "get door schedule for project X" → structured JSON

### Deliverable
Upload a drawing set → door/window/finish schedules extracted to structured data. Human review UI for corrections. API for EVA agents to query.

**Cost:** ~$5-25 per drawing set for VLM calls

---

## Phase 3: Agent Integration (Weeks 9-12)

**Goal:** EVA agents can query drawing data to do their jobs.

### Week 9-10: Query Layer
- [ ] **Drawing query service** — unified API for all tiers of drawing data
  - `GET /drawings/{project}/sheets` — list all sheets with metadata
  - `GET /drawings/{project}/schedules?type=door` — get door schedule data
  - `GET /drawings/{project}/search?q=lobby ceiling` — full-text search
  - `GET /drawings/{project}/sheets/{id}/text` — full extracted text
  - `GET /drawings/{project}/sheets/{id}/image` — rendered image
- [ ] **Natural language drawing query** — "What hardware set is specified for door 101?" → query schedule → return answer
- [ ] **Drawing reference resolver** — agent says "see A-201" → return sheet metadata + thumbnail

### Week 11-12: Submittal Agent Integration
- [ ] **Submittal checking against schedules** — compare submitted product data against schedule requirements
- [ ] **Spec cross-reference** — link schedule entries to specification sections
- [ ] **RFI drawing reference** — when drafting RFI, pull relevant drawing info

### Deliverable
EVA Submittal Agent can check a door hardware submittal against the door schedule automatically. EVA RFI Agent can reference drawing details.

---

## Phase 4: Spatial Understanding (Weeks 13-20)

**Goal:** Tier 2 spatial extraction for key floor plans. Rooms identified and mapped.

### Week 13-16: Room Extraction
- [ ] **High-res rendering pipeline** — 300 DPI rendering, tiling for large sheets
- [ ] **Room identification via VLM** — extract room names, numbers, approximate locations
- [ ] **Grid line extraction** — column/row grid references
- [ ] **Room-to-schedule linking** — connect rooms from plans to finish schedule entries
- [ ] **Spatial index** — store room bounding boxes for queries

### Week 17-20: Element Mapping
- [ ] **Door/window identification on plans** — map plan symbols to schedule entries
- [ ] **Detail callout extraction** — identify section marks, detail markers, and their target sheets
- [ ] **Cross-sheet navigation** — "Detail 3 on A-201 → see A-501"
- [ ] **Spatial query API** — "What rooms are on the second floor?" "What doors are in the lobby?"

### Deliverable
EVA agents can ask spatial questions: "What's the ceiling finish in Room 201?" → look up room on plan → cross-reference finish schedule.

---

## Database Schema

```sql
-- Core drawing tables
CREATE TABLE drawing_sets (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL,                    -- "Construction Documents Rev 3"
    uploaded_at TIMESTAMPTZ NOT NULL,
    total_sheets INTEGER,
    tier0_complete BOOLEAN DEFAULT FALSE,
    tier1_complete BOOLEAN DEFAULT FALSE
);

CREATE TABLE sheets (
    id UUID PRIMARY KEY,
    drawing_set_id UUID NOT NULL REFERENCES drawing_sets(id),
    page_number INTEGER NOT NULL,          -- page index in PDF
    sheet_number TEXT,                      -- "A-201"
    sheet_title TEXT,                       -- "FIRST FLOOR PLAN"
    discipline TEXT,                        -- architectural, structural, mechanical, electrical, plumbing, civil
    sheet_type TEXT,                        -- plan, elevation, section, detail, schedule, notes, cover
    revision TEXT,
    revision_date DATE,
    scale TEXT[],                           -- array of scales on sheet
    is_scanned BOOLEAN DEFAULT FALSE,
    pdf_path TEXT NOT NULL,                 -- path to original PDF
    thumbnail_path TEXT,                    -- path to thumbnail PNG
    full_text TEXT,                         -- all extracted text for search
    tier0_processed_at TIMESTAMPTZ,
    tier1_processed_at TIMESTAMPTZ,
    tier2_processed_at TIMESTAMPTZ
);

CREATE INDEX idx_sheets_project ON sheets(drawing_set_id);
CREATE INDEX idx_sheets_number ON sheets(sheet_number);
CREATE INDEX idx_sheets_discipline ON sheets(discipline);
CREATE INDEX idx_sheets_fulltext ON sheets USING gin(to_tsvector('english', full_text));

-- Schedule extraction tables
CREATE TABLE schedules (
    id UUID PRIMARY KEY,
    sheet_id UUID NOT NULL REFERENCES sheets(id),
    schedule_type TEXT NOT NULL,            -- door_schedule, window_schedule, etc.
    title TEXT,                             -- "DOOR SCHEDULE"
    headers JSONB NOT NULL,                 -- ["MARK", "WIDTH", "HEIGHT", ...]
    row_count INTEGER,
    confidence FLOAT,
    extraction_method TEXT,                 -- pdfplumber, vlm, vlm_retry, manual
    validated_by UUID,                      -- user who reviewed
    validated_at TIMESTAMPTZ,
    extracted_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE schedule_rows (
    id UUID PRIMARY KEY,
    schedule_id UUID NOT NULL REFERENCES schedules(id),
    row_index INTEGER NOT NULL,
    data JSONB NOT NULL,                   -- {"MARK": "101", "WIDTH": "3'-0\"", ...}
    confidence FLOAT,
    warnings JSONB,                        -- validation warnings
    UNIQUE(schedule_id, row_index)
);

CREATE INDEX idx_schedule_rows_data ON schedule_rows USING gin(data);

-- Spatial extraction tables (Phase 4)
CREATE TABLE spaces (
    id UUID PRIMARY KEY,
    sheet_id UUID NOT NULL REFERENCES sheets(id),
    name TEXT,                              -- "LOBBY"
    number TEXT,                            -- "101"
    floor TEXT,                             -- "1", "2", "B1"
    grid_reference JSONB,                   -- {"from": "A/1", "to": "C/3"}
    bounding_box JSONB,                     -- {"x": 120, "y": 340, "w": 450, "h": 380}
    area_approx_sf FLOAT,
    finish_schedule_ref TEXT,               -- reference to finish schedule type
    elements JSONB,                         -- ["door:101", "door:102"]
    extracted_at TIMESTAMPTZ
);

-- Drawing cross-references
CREATE TABLE drawing_references (
    id UUID PRIMARY KEY,
    source_sheet_id UUID REFERENCES sheets(id),
    target_sheet_number TEXT,               -- "A-501" (may not exist yet)
    target_sheet_id UUID REFERENCES sheets(id),  -- resolved reference
    reference_type TEXT,                    -- section, detail, elevation, plan
    reference_mark TEXT,                    -- "3" (as in "Detail 3/A-501")
    location_on_source JSONB               -- approximate location on source sheet
);
```

---

## Technology Stack Summary

| Component | Technology | Why |
|-----------|-----------|-----|
| PDF parsing | PyMuPDF (fitz) | Fastest, best text extraction, image rendering |
| Table extraction | pdfplumber + Gemini Flash | pdfplumber for vector, Gemini for fallback/validation |
| Vision understanding | Gemini 2.5 Flash (primary), Gemini 2.5 Pro (complex) | Best benchmarked performance on construction tables |
| Text reasoning | Claude Opus 4 | Best for interpreting specs, notes, answering questions about drawings |
| Storage | S3-compatible (MinIO/AWS S3) | Drawing PDFs and rendered images |
| Database | PostgreSQL + JSONB | Structured schedule data, full-text search, spatial queries |
| Search | Postgres FTS or Meilisearch | Full-text search across drawing text |
| Worker queue | BullMQ / Celery | Async processing of drawing uploads through tiers |
| Image processing | Pillow, pdf2image | Rendering, tiling, thumbnail generation |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| VLM accuracy drops on unusual drawings | Human review UI; confidence scoring flags issues; never trust VLM output without validation |
| VLM cost spikes on large sets | Tier processing is on-demand, not automatic for Tier 1+; cost caps per project |
| Model API changes/deprecation | Abstract VLM calls behind interface; model-agnostic pipeline design |
| Scanned PDFs in "CAD" sets | Detect per-page, route to appropriate pipeline |
| Multi-page schedules missed | Tier 0 classification + naming pattern detection flags related sheets |
| Users don't review flagged items | Default to conservative (lower confidence = block automated use) |

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| 1 | Tier 0 processing time (500 sheets) | <60 seconds |
| 1 | Sheet classification accuracy | >90% |
| 2 | Schedule extraction accuracy (cell-level) | >85% on standard schedules |
| 2 | Human review rate (% needing correction) | <25% of schedules |
| 3 | Submittal agent query response time | <5 seconds |
| 3 | Correct schedule lookup rate | >90% |
| 4 | Room identification accuracy | >80% |
| 4 | Cross-reference resolution rate | >75% |
