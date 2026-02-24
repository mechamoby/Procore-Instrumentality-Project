-- =============================================================================
-- EVA-00: Master Clerk & Project Historian — PostgreSQL 16 Schema
-- =============================================================================
-- 
-- This schema supports the full lifecycle of construction project data:
-- projects, companies, contacts, drawings, specs, submittals, RFIs,
-- daily reports, meeting minutes, schedules, change orders, photos,
-- documents, and vector embeddings for semantic search.
--
-- Conventions:
--   - All tables use UUID primary keys (for Procore sync + deduplication)
--   - procore_id columns store the Procore API object ID for sync
--   - All timestamps are timestamptz (UTC stored, local display in app)
--   - Soft deletes via is_deleted + deleted_at (construction data = legal record)
--   - Full-text search via tsvector columns with GIN indexes
--   - Vector embeddings in document_chunks table via pgvector
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";        -- pgvector
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- trigram fuzzy matching

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

CREATE TYPE submittal_status AS ENUM (
    'draft', 'open', 'submitted', 'under_review', 'approved',
    'approved_as_noted', 'revise_and_resubmit', 'rejected', 'closed', 'void'
);

CREATE TYPE rfi_status AS ENUM (
    'draft', 'open', 'answered', 'closed', 'void'
);

CREATE TYPE change_order_status AS ENUM (
    'draft', 'pending', 'approved', 'rejected', 'void'
);

CREATE TYPE drawing_discipline AS ENUM (
    'architectural', 'structural', 'mechanical', 'electrical',
    'plumbing', 'fire_protection', 'civil', 'landscape', 'other'
);

CREATE TYPE document_type AS ENUM (
    'drawing', 'specification', 'submittal', 'rfi', 'daily_report',
    'meeting_minutes', 'schedule', 'change_order', 'photo', 'contract',
    'insurance', 'permit', 'inspection', 'correspondence', 'closeout', 'other'
);

CREATE TYPE sync_status AS ENUM (
    'pending', 'synced', 'conflict', 'error', 'local_only'
);

CREATE TYPE ingestion_status AS ENUM (
    'queued', 'processing', 'parsed', 'embedded', 'complete', 'failed'
);

-- =============================================================================
-- COMPANIES & CONTACTS
-- =============================================================================

CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procore_id      BIGINT UNIQUE,
    name            TEXT NOT NULL,
    trade           TEXT,                   -- e.g., 'Concrete', 'Electrical', 'Mechanical'
    license_number  TEXT,
    address         JSONB,                  -- {street, city, state, zip}
    phone           TEXT,
    email           TEXT,
    website         TEXT,
    notes           TEXT,
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    -- Full-text search
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(trade, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(notes, '')), 'C')
    ) STORED
);

CREATE TABLE contacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procore_id      BIGINT UNIQUE,
    company_id      UUID REFERENCES companies(id),
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    title           TEXT,
    email           TEXT,
    phone           TEXT,
    mobile          TEXT,
    is_primary      BOOLEAN DEFAULT FALSE,  -- primary contact for the company
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(first_name || ' ' || last_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(title, '')), 'B')
    ) STORED
);

-- =============================================================================
-- PROJECTS
-- =============================================================================

CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    procore_id      BIGINT UNIQUE,
    name            TEXT NOT NULL,
    number          TEXT,                   -- project number (e.g., "2024-015")
    description     TEXT,
    address         JSONB,
    client_company_id UUID REFERENCES companies(id),
    status          TEXT DEFAULT 'active',  -- active, completed, archived
    start_date      DATE,
    estimated_completion DATE,
    actual_completion DATE,
    contract_value  NUMERIC(15,2),
    project_type    TEXT,                   -- commercial, residential, industrial, etc.
    square_footage  INTEGER,
    
    -- Procore sync metadata
    procore_project_id BIGINT,
    last_synced_at  TIMESTAMPTZ,
    sync_status     sync_status DEFAULT 'pending',
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(number, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED
);

-- Junction table: which companies are on which projects, in what role
CREATE TABLE project_companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    company_id      UUID NOT NULL REFERENCES companies(id),
    role            TEXT NOT NULL,          -- 'gc', 'owner', 'architect', 'subcontractor', 'supplier'
    trade           TEXT,                   -- specific trade on this project
    contract_value  NUMERIC(15,2),
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, company_id, role)
);

-- =============================================================================
-- SPECIFICATIONS
-- =============================================================================

CREATE TABLE spec_sections (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    number          TEXT NOT NULL,          -- CSI number: "03 30 00"
    title           TEXT NOT NULL,          -- "Cast-in-Place Concrete"
    division        INTEGER,               -- CSI division: 3
    full_text       TEXT,                   -- full section content (parsed from PDF)
    revision        TEXT,
    issue_date      DATE,
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(number, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(full_text, '')), 'B')
    ) STORED,
    
    UNIQUE(project_id, number)
);

-- =============================================================================
-- DRAWINGS
-- =============================================================================

CREATE TABLE drawings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    number          TEXT NOT NULL,          -- "A-201", "S-100"
    title           TEXT,
    discipline      drawing_discipline,
    set_name        TEXT,                   -- "Issued for Construction", "ASI #3"
    revision        TEXT DEFAULT '0',
    revision_date   DATE,
    received_date   DATE,
    current         BOOLEAN DEFAULT TRUE,   -- is this the current revision?
    
    -- File references
    file_hash       TEXT,                   -- SHA-256 of the file
    file_path       TEXT,                   -- relative path in file storage
    file_size_bytes BIGINT,
    thumbnail_path  TEXT,
    page_count      INTEGER DEFAULT 1,
    
    -- Extracted metadata
    ocr_text        TEXT,                   -- OCR'd text from drawing
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(number, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(set_name, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(ocr_text, '')), 'C')
    ) STORED
);

-- Track drawing revision history
CREATE TABLE drawing_revisions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drawing_id      UUID NOT NULL REFERENCES drawings(id),
    revision        TEXT NOT NULL,
    revision_date   DATE,
    file_hash       TEXT,
    file_path       TEXT,
    change_summary  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SUBMITTALS (with full workflow history)
-- =============================================================================

CREATE TABLE submittals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    number          TEXT NOT NULL,          -- "001", "002.1" (with revisions)
    revision        INTEGER DEFAULT 0,
    title           TEXT NOT NULL,
    description     TEXT,
    
    -- Classification
    spec_section_id UUID REFERENCES spec_sections(id),
    spec_section_number TEXT,               -- denormalized for quick display
    submittal_type  TEXT,                   -- 'shop_drawing', 'product_data', 'sample', 'mock_up', etc.
    
    -- Workflow
    status          submittal_status DEFAULT 'draft',
    submitted_by_company_id UUID REFERENCES companies(id),
    submitted_by_contact_id UUID REFERENCES contacts(id),
    submitted_date  DATE,
    required_date   DATE,                   -- when it's needed on site
    
    -- Review
    responsible_contractor_id UUID REFERENCES companies(id),
    approver_id     UUID REFERENCES contacts(id),
    ball_in_court_id UUID REFERENCES contacts(id),
    received_date   DATE,
    returned_date   DATE,
    
    -- Linked drawings
    drawing_ids     UUID[],                 -- drawings this submittal references
    
    -- Cost
    cost_impact     BOOLEAN DEFAULT FALSE,
    cost_amount     NUMERIC(15,2),
    
    -- Schedule
    schedule_impact BOOLEAN DEFAULT FALSE,
    lead_time_days  INTEGER,
    
    -- Source tracking
    import_source   TEXT,                   -- 'procore_api', 'pdf_log_import', 'cover_sheet_import', 'manual'
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(number, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(spec_section_number, '')), 'B')
    ) STORED
);

-- Every status change, comment, and review action
CREATE TABLE submittal_workflow_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submittal_id    UUID NOT NULL REFERENCES submittals(id),
    action          TEXT NOT NULL,          -- 'created', 'submitted', 'reviewed', 'commented', 'returned', 'resubmitted'
    from_status     submittal_status,
    to_status       submittal_status,
    actor_contact_id UUID REFERENCES contacts(id),
    actor_company_id UUID REFERENCES companies(id),
    comment         TEXT,
    stamp           TEXT,                   -- 'approved', 'approved_as_noted', 'revise_and_resubmit', 'rejected'
    attachments     JSONB,                  -- [{file_hash, file_path, filename}]
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- RFIs (with responses)
-- =============================================================================

CREATE TABLE rfis (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    number          TEXT NOT NULL,
    subject         TEXT NOT NULL,
    question        TEXT NOT NULL,
    
    -- Classification
    spec_section_id UUID REFERENCES spec_sections(id),
    spec_section_number TEXT,
    drawing_ids     UUID[],                 -- referenced drawings
    location        TEXT,                   -- building area / grid reference
    
    -- Workflow
    status          rfi_status DEFAULT 'draft',
    initiated_by_contact_id UUID REFERENCES contacts(id),
    initiated_by_company_id UUID REFERENCES companies(id),
    assigned_to_contact_id UUID REFERENCES contacts(id),
    assigned_to_company_id UUID REFERENCES companies(id),
    ball_in_court_id UUID REFERENCES contacts(id),
    
    -- Dates
    date_initiated  DATE,
    due_date        DATE,
    date_answered   DATE,
    date_closed     DATE,
    
    -- Impact
    cost_impact     BOOLEAN DEFAULT FALSE,
    cost_amount     NUMERIC(15,2),
    schedule_impact BOOLEAN DEFAULT FALSE,
    schedule_impact_days INTEGER,
    
    -- Answer
    official_answer TEXT,
    answered_by_contact_id UUID REFERENCES contacts(id),
    
    -- Cost tracking
    cost_code       TEXT,                   -- e.g., "16-0500 - Electrical" (CSI-based)
    
    -- Source tracking (for data provenance)
    import_source   TEXT,                   -- 'procore_api', 'pdf_log_import', 'manual'
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(number, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(subject, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(question, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(official_answer, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(location, '')), 'C')
    ) STORED
);

CREATE TABLE rfi_responses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rfi_id          UUID NOT NULL REFERENCES rfis(id),
    responder_contact_id UUID REFERENCES contacts(id),
    responder_company_id UUID REFERENCES companies(id),
    body            TEXT NOT NULL,
    is_official     BOOLEAN DEFAULT FALSE,
    attachments     JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- DAILY REPORTS
-- =============================================================================

CREATE TABLE daily_reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    report_date     DATE NOT NULL,
    created_by_contact_id UUID REFERENCES contacts(id),
    
    -- Weather
    weather         JSONB,                  -- {high_temp, low_temp, conditions, wind, precipitation}
    
    -- Narrative
    work_performed  TEXT,
    delays          TEXT,
    safety_notes    TEXT,
    visitors        TEXT,
    general_notes   TEXT,
    
    -- Workforce (denormalized summary)
    total_workers   INTEGER,
    workforce       JSONB,                  -- [{company_id, trade, headcount, hours}]
    
    -- Equipment
    equipment       JSONB,                  -- [{name, hours, status}]
    
    -- Deliveries
    deliveries      JSONB,                  -- [{description, supplier, quantity}]
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(work_performed, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(delays, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(safety_notes, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(general_notes, '')), 'B')
    ) STORED,
    
    UNIQUE(project_id, report_date)
);

-- =============================================================================
-- MEETING MINUTES
-- =============================================================================

CREATE TABLE meetings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    title           TEXT NOT NULL,          -- "OAC Meeting #14"
    meeting_type    TEXT,                   -- 'OAC', 'subcontractor', 'safety', 'preconstruction'
    meeting_date    DATE NOT NULL,
    location        TEXT,
    
    attendees       JSONB,                  -- [{contact_id, name, company, present}]
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending'
);

CREATE TABLE meeting_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id      UUID NOT NULL REFERENCES meetings(id),
    item_number     TEXT,
    topic           TEXT NOT NULL,
    discussion      TEXT,
    action_required TEXT,
    responsible_contact_id UUID REFERENCES contacts(id),
    due_date        DATE,
    status          TEXT DEFAULT 'open',    -- open, closed, ongoing
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(topic, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(discussion, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(action_required, '')), 'B')
    ) STORED
);

-- =============================================================================
-- SCHEDULES
-- =============================================================================

CREATE TABLE schedules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    name            TEXT NOT NULL,          -- "Master Schedule Rev 5"
    schedule_type   TEXT,                   -- 'master', 'lookahead', 'phase'
    revision        TEXT,
    effective_date  DATE,
    file_hash       TEXT,
    file_path       TEXT,
    
    is_current      BOOLEAN DEFAULT TRUE,
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending'
);

CREATE TABLE schedule_activities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id     UUID NOT NULL REFERENCES schedules(id),
    activity_id     TEXT,                   -- WBS code
    name            TEXT NOT NULL,
    start_date      DATE,
    finish_date     DATE,
    actual_start    DATE,
    actual_finish   DATE,
    duration_days   INTEGER,
    percent_complete NUMERIC(5,2) DEFAULT 0,
    predecessors    TEXT[],                 -- array of activity_ids
    responsible_company_id UUID REFERENCES companies(id),
    is_critical     BOOLEAN DEFAULT FALSE,
    is_milestone    BOOLEAN DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- CHANGE ORDERS
-- =============================================================================

CREATE TABLE change_orders (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    number          TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    
    status          change_order_status DEFAULT 'draft',
    change_reason   TEXT,                   -- 'owner_change', 'design_error', 'unforeseen_condition', etc.
    
    -- Financial
    amount          NUMERIC(15,2),
    
    -- Schedule
    schedule_impact_days INTEGER,
    
    -- References
    related_rfi_ids UUID[],
    related_submittal_ids UUID[],
    
    -- Workflow
    initiated_by_company_id UUID REFERENCES companies(id),
    approved_by_contact_id UUID REFERENCES contacts(id),
    date_initiated  DATE,
    date_approved   DATE,
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(number, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED
);

-- =============================================================================
-- PHOTOS
-- =============================================================================

CREATE TABLE photos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    procore_id      BIGINT,
    
    title           TEXT,
    description     TEXT,
    location        TEXT,                   -- where on site
    photo_date      DATE,
    taken_by_contact_id UUID REFERENCES contacts(id),
    
    -- Albums / categories
    album           TEXT,                   -- 'Progress', 'Safety', 'Punchlist', etc.
    tags            TEXT[],
    
    -- File
    file_hash       TEXT,
    file_path       TEXT,
    thumbnail_path  TEXT,
    file_size_bytes BIGINT,
    
    -- EXIF metadata
    exif_data       JSONB,                  -- {lat, lon, camera, exposure, etc.}
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(location, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(album, '')), 'C')
    ) STORED
);

-- =============================================================================
-- GENERIC DOCUMENTS (catch-all for files not fitting above categories)
-- =============================================================================

CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id),  -- NULL = company-wide (standards, etc.)
    procore_id      BIGINT,
    
    title           TEXT NOT NULL,
    description     TEXT,
    doc_type        document_type DEFAULT 'other',
    category        TEXT,                   -- freeform category / folder path
    
    -- File
    file_hash       TEXT,
    file_path       TEXT,
    file_name       TEXT,
    file_size_bytes BIGINT,
    mime_type       TEXT,
    page_count      INTEGER,
    
    -- Parsed content
    extracted_text  TEXT,                   -- full text extracted from PDF/doc
    
    -- Metadata
    author          TEXT,
    issue_date      DATE,
    version         TEXT,
    tags            TEXT[],
    
    -- Ingestion tracking
    ingestion_status ingestion_status DEFAULT 'queued',
    ingestion_error  TEXT,
    ingested_at     TIMESTAMPTZ,
    
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    sync_status     sync_status DEFAULT 'pending',
    
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(extracted_text, '')), 'C')
    ) STORED
);

-- =============================================================================
-- CAD EXTRACTION DATA (DWG/DXF structured data)
-- =============================================================================
-- Stores structured data extracted from CAD files via ezdxf.
-- This is the competitive moat: instant, $0 extraction at ~99% accuracy.

CREATE TABLE drawing_cad_data (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drawing_id      UUID NOT NULL REFERENCES drawings(id),
    
    -- Source file
    source_format   TEXT NOT NULL,          -- 'dxf', 'dwg' (converted to dxf)
    source_file_path TEXT,
    
    -- Extracted layers
    layers          JSONB,                  -- [{name: "A-DOOR", entity_count: 45, color: 7}, ...]
    layer_count     INTEGER,
    
    -- Extracted rooms/spaces
    rooms           JSONB,                  -- [{name: "RESIDENTIAL LOBBY", id: "L01-024", centroid: [x,y]}, ...]
    
    -- Structural grid
    grid_lines      JSONB,                  -- {horizontal: ["A","B","C","D"], vertical: ["1","2","3"...]}
    grid_dimensions JSONB,                  -- [{from: "4", to: "5", dimension: "20'-7 29/32\""}, ...]
    
    -- Extracted text entities
    text_entities   JSONB,                  -- [{text: "10'-1\" (NGVD)", layer: "A-ANNO-NOTE", position: [x,y]}, ...]
    
    -- Block references (doors, windows, equipment)
    block_refs      JSONB,                  -- [{name: "Door-Single", count: 24, layer: "A-DOOR"}, ...]
    block_ref_count INTEGER,
    
    -- Dimension entities
    dimensions      JSONB,                  -- [{value: "20'-6\"", layer: "A-ANNO-DIMS", start: [x,y], end: [x,y]}, ...]
    
    -- Extraction metadata
    extracted_at    TIMESTAMPTZ DEFAULT NOW(),
    extraction_time_ms INTEGER,             -- how long extraction took
    ezdxf_version   TEXT
);

CREATE INDEX idx_cad_data_drawing ON drawing_cad_data(drawing_id);

COMMENT ON TABLE drawing_cad_data IS 'Structured data extracted from DWG/DXF files via ezdxf. $0 cost, instant, ~99% accuracy. The competitive moat.';

-- =============================================================================
-- DOCUMENT CHUNKS + VECTOR EMBEDDINGS (pgvector)
-- =============================================================================

CREATE TABLE document_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Polymorphic reference: what entity does this chunk belong to?
    source_type     TEXT NOT NULL,          -- 'document', 'submittal', 'rfi', 'daily_report', 'meeting_item', 'spec_section', 'drawing', 'change_order'
    source_id       UUID NOT NULL,          -- ID in the source table
    project_id      UUID REFERENCES projects(id),
    
    -- Chunk content
    content         TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL,       -- ordering within the source document
    page_number     INTEGER,
    token_count     INTEGER,
    
    -- Classification metadata (denormalized for fast filtering)
    doc_type        document_type,
    spec_section    TEXT,                   -- CSI section number if applicable
    discipline      TEXT,                   -- architectural, structural, etc.
    
    -- The embedding vector (768 dimensions for nomic-embed-text-v1.5)
    embedding       vector(768),
    
    -- Embedding metadata
    embedding_model TEXT DEFAULT 'nomic-embed-text-v1.5',
    embedded_at     TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SYNC TRACKING
-- =============================================================================

CREATE TABLE sync_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type     TEXT NOT NULL,          -- 'project', 'submittal', 'rfi', etc.
    entity_id       UUID NOT NULL,
    procore_id      BIGINT,
    action          TEXT NOT NULL,          -- 'create', 'update', 'delete'
    procore_updated_at TIMESTAMPTZ,
    local_updated_at TIMESTAMPTZ,
    sync_direction  TEXT,                   -- 'procore_to_local', 'local_to_procore'
    status          TEXT DEFAULT 'success', -- 'success', 'conflict', 'error'
    error_message   TEXT,
    payload_hash    TEXT,                   -- hash of the synced payload for change detection
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sync_cursors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type     TEXT NOT NULL UNIQUE,   -- 'submittals', 'rfis', etc.
    project_id      UUID REFERENCES projects(id),
    last_synced_at  TIMESTAMPTZ NOT NULL,
    last_procore_id BIGINT,
    cursor_token    TEXT,                   -- Procore pagination cursor
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================

CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    agent           TEXT NOT NULL,          -- 'eva-00', 'eva-01-submittal', 'eva-02-rfi', 'system'
    action          TEXT NOT NULL,          -- 'query', 'create', 'update', 'delete', 'sync'
    entity_type     TEXT,
    entity_id       UUID,
    query_text      TEXT,                   -- for search queries, the search string
    result_count    INTEGER,
    ip_address      INET,
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Full-text search GIN indexes
CREATE INDEX idx_companies_search ON companies USING GIN (search_vector);
CREATE INDEX idx_contacts_search ON contacts USING GIN (search_vector);
CREATE INDEX idx_projects_search ON projects USING GIN (search_vector);
CREATE INDEX idx_spec_sections_search ON spec_sections USING GIN (search_vector);
CREATE INDEX idx_drawings_search ON drawings USING GIN (search_vector);
CREATE INDEX idx_submittals_search ON submittals USING GIN (search_vector);
CREATE INDEX idx_rfis_search ON rfis USING GIN (search_vector);
CREATE INDEX idx_daily_reports_search ON daily_reports USING GIN (search_vector);
CREATE INDEX idx_meeting_items_search ON meeting_items USING GIN (search_vector);
CREATE INDEX idx_change_orders_search ON change_orders USING GIN (search_vector);
CREATE INDEX idx_photos_search ON photos USING GIN (search_vector);
CREATE INDEX idx_documents_search ON documents USING GIN (search_vector);

-- Vector similarity index (IVFFlat — rebuild after bulk loads)
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 300);

-- Trigram indexes for fuzzy matching on key fields
CREATE INDEX idx_companies_name_trgm ON companies USING GIN (name gin_trgm_ops);
CREATE INDEX idx_drawings_number_trgm ON drawings USING GIN (number gin_trgm_ops);
CREATE INDEX idx_submittals_number_trgm ON submittals USING GIN (number gin_trgm_ops);
CREATE INDEX idx_rfis_number_trgm ON rfis USING GIN (number gin_trgm_ops);

-- Foreign key & query pattern indexes
CREATE INDEX idx_contacts_company ON contacts(company_id);
CREATE INDEX idx_project_companies_project ON project_companies(project_id);
CREATE INDEX idx_project_companies_company ON project_companies(company_id);

CREATE INDEX idx_spec_sections_project ON spec_sections(project_id);
CREATE INDEX idx_spec_sections_number ON spec_sections(project_id, number);

CREATE INDEX idx_drawings_project ON drawings(project_id);
CREATE INDEX idx_drawings_project_discipline ON drawings(project_id, discipline);
CREATE INDEX idx_drawings_number ON drawings(project_id, number);
CREATE INDEX idx_drawings_current ON drawings(project_id, current) WHERE current = TRUE;

CREATE INDEX idx_submittals_project ON submittals(project_id);
CREATE INDEX idx_submittals_status ON submittals(project_id, status);
CREATE INDEX idx_submittals_spec ON submittals(spec_section_id);
CREATE INDEX idx_submittals_company ON submittals(submitted_by_company_id);
CREATE INDEX idx_submittal_history_submittal ON submittal_workflow_history(submittal_id);

CREATE INDEX idx_rfis_project ON rfis(project_id);
CREATE INDEX idx_rfis_status ON rfis(project_id, status);
CREATE INDEX idx_rfis_spec ON rfis(spec_section_id);
CREATE INDEX idx_rfi_responses_rfi ON rfi_responses(rfi_id);

CREATE INDEX idx_daily_reports_project_date ON daily_reports(project_id, report_date DESC);

CREATE INDEX idx_meetings_project ON meetings(project_id);
CREATE INDEX idx_meetings_date ON meetings(project_id, meeting_date DESC);
CREATE INDEX idx_meeting_items_meeting ON meeting_items(meeting_id);

CREATE INDEX idx_schedules_project ON schedules(project_id);
CREATE INDEX idx_schedule_activities_schedule ON schedule_activities(schedule_id);
CREATE INDEX idx_schedule_activities_dates ON schedule_activities(start_date, finish_date);

CREATE INDEX idx_change_orders_project ON change_orders(project_id);

CREATE INDEX idx_photos_project ON photos(project_id);
CREATE INDEX idx_photos_date ON photos(project_id, photo_date DESC);
CREATE INDEX idx_photos_album ON photos(project_id, album);

CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_ingestion ON documents(ingestion_status) WHERE ingestion_status != 'complete';

-- Document chunks: filtered queries
CREATE INDEX idx_chunks_source ON document_chunks(source_type, source_id);
CREATE INDEX idx_chunks_project ON document_chunks(project_id);
CREATE INDEX idx_chunks_type ON document_chunks(doc_type);
CREATE INDEX idx_chunks_spec ON document_chunks(spec_section) WHERE spec_section IS NOT NULL;

-- Sync tracking
CREATE INDEX idx_sync_log_entity ON sync_log(entity_type, entity_id);
CREATE INDEX idx_sync_log_created ON sync_log(created_at DESC);
CREATE INDEX idx_sync_cursors_type ON sync_cursors(entity_type);

-- Audit log (time-series, recent queries)
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_log_agent ON audit_log(agent, created_at DESC);

-- Procore ID lookups (for sync)
CREATE INDEX idx_drawings_procore ON drawings(procore_id) WHERE procore_id IS NOT NULL;
CREATE INDEX idx_submittals_procore ON submittals(procore_id) WHERE procore_id IS NOT NULL;
CREATE INDEX idx_rfis_procore ON rfis(procore_id) WHERE procore_id IS NOT NULL;
CREATE INDEX idx_daily_reports_procore ON daily_reports(procore_id) WHERE procore_id IS NOT NULL;
CREATE INDEX idx_meetings_procore ON meetings(procore_id) WHERE procore_id IS NOT NULL;
CREATE INDEX idx_change_orders_procore ON change_orders(procore_id) WHERE procore_id IS NOT NULL;
CREATE INDEX idx_photos_procore ON photos(procore_id) WHERE procore_id IS NOT NULL;
CREATE INDEX idx_documents_procore ON documents(procore_id) WHERE procore_id IS NOT NULL;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY[
        'companies', 'contacts', 'projects', 'spec_sections', 'drawings',
        'submittals', 'rfis', 'daily_reports', 'meetings', 'schedules',
        'change_orders', 'photos', 'documents'
    ]) LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at()',
            t, t
        );
    END LOOP;
END;
$$;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE document_chunks IS 'Chunked text with vector embeddings for semantic search across all document types';
COMMENT ON COLUMN document_chunks.source_type IS 'Polymorphic ref: document, submittal, rfi, daily_report, meeting_item, spec_section, drawing, change_order';
COMMENT ON COLUMN document_chunks.embedding IS '768-dim vector from nomic-embed-text-v1.5 via Ollama (local inference)';
COMMENT ON TABLE sync_log IS 'Tracks every Procore sync operation for debugging and conflict resolution';
COMMENT ON TABLE sync_cursors IS 'Stores last-synced position per entity type for incremental polling';
COMMENT ON TABLE audit_log IS 'Records all data access by EVA agents for compliance and debugging';
