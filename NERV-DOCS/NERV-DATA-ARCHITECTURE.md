# NERV Data Architecture
## Database + File System + Naming Conventions
*Draft: February 24, 2026*

---

## Design Principles

1. **PM-intuitive first** — A PM with zero AI experience should look at this and think "that makes sense"
2. **AI-parseable second** — Predictable paths, consistent naming, rich metadata = fast retrieval
3. **Procore-aligned** — Mirror Procore's mental model where possible (PMs already think this way)
4. **Zero ambiguity** — One file, one location, one name. No guessing.

---

## Real-World Reference

Analyzed 6 real project folders across two GCs (APCB + Miller Construction).
Used as input to understand PM mental models — NOT as a template to copy.
The goal: design what they *should* have, not replicate what they *do* have.

### Problems Observed in Real Folders
- No consistency between projects at the same company
- Loose files at project root (PDFs floating next to folders)
- Duplicate/overlapping categories (`Schedule` AND `Schedules` in same project)
- No status tracking in folder structure — everything dumped flat
- No naming convention — impossible to sort, search, or automate against
- Division folders are the only universally consistent element (CSI standard)
- Pay Apps split into individual folders but nothing else is — inconsistent logic
- Project-specific one-offs scattered everywhere with no designated area

---

## Part 1: File Folder Structure

### Design Philosophy
This isn't how PMs currently organize files. It's how they *should* — designed for a PM working alongside an AI agent. Every folder answers a question a PM asks daily. Every naming pattern enables the AI to act without guessing.

**The 3 rules:**
1. **If you can't find it in 2 clicks, the structure failed**
2. **If the AI can't parse the path to know what's inside, the naming failed**
3. **No loose files — everything has a home**

```
{project}/
│
├── 01 - Preconstruction/
│   ├── Bidding/
│   ├── Buyout/
│   ├── Contracts & Agreements/
│   ├── Permits/
│   └── Schedules & Surveys/
│
├── 02 - Specifications/                    ← CSI MasterFormat 2020 Divisions
│   ├── Div 00 - Procurement and Contracting/
│   ├── Div 01 - General Requirements/
│   ├── Div 02 - Existing Conditions/
│   ├── Div 03 - Concrete/
│   ├── Div 04 - Masonry/
│   ├── Div 05 - Metals/
│   ├── Div 06 - Wood, Plastics, and Composites/
│   ├── Div 07 - Thermal and Moisture Protection/
│   ├── Div 08 - Openings/
│   ├── Div 09 - Finishes/
│   ├── Div 10 - Specialties/
│   ├── Div 11 - Equipment/
│   ├── Div 12 - Furnishings/
│   ├── Div 13 - Special Construction/
│   ├── Div 14 - Conveying Equipment/
│   ├── Div 21 - Fire Suppression/
│   ├── Div 22 - Plumbing/
│   ├── Div 23 - HVAC/
│   ├── Div 26 - Electrical/
│   ├── Div 27 - Communications/
│   ├── Div 28 - Electronic Safety and Security/
│   ├── Div 31 - Earthwork/
│   ├── Div 32 - Exterior Improvements/
│   └── Div 33 - Utilities/
│
├── 03 - Drawings & Models/
│   ├── CAD/                                ← DXF format (converted for AI readability)
│   └── BIM/                                ← IFC/RVT files
│   NOTE: Live drawing sets stay in Procore Drawings module.
│   This folder is for source files the AI needs to read directly.
│
├── 04 - Submittals/                        ← Agent-managed (EVA-01)
│   ├── 01 - Open/                          ← Active pipeline
│   ├── 02 - Under Review/
│   ├── 03 - Approved/
│   ├── 04 - Revise and Resubmit/
│   └── 05 - Rejected/
│
├── 05 - RFIs/                              ← Agent-managed (EVA-02)
│   ├── 01 - Open/
│   ├── 02 - Answered/
│   └── 03 - Closed/
│
├── 06 - Change Orders/
│   ├── Pending/
│   ├── Approved/
│   └── Rejected/
│
├── 07 - Meetings/
│   ├── OAC/                                ← Owner-Architect-Contractor
│   ├── Subcontractor/
│   └── Internal/
│
├── 08 - Safety/
│   ├── Plans/
│   ├── Inspections/
│   ├── Incidents/
│   └── Certifications/
│
├── 09 - Reports & Daily Logs/
│   ├── Daily Reports/
│   ├── Inspections/
│   └── Photos/                             ← Subfoldered by YYYY-MM
│
├── 10 - Financial/
│   ├── Pay Applications/                   ← Files named PAY-001, PAY-002 etc.
│   ├── Invoices/
│   ├── Budget/
│   └── Tax Refund - Material Invoices/
│
├── 11 - Subcontractors/
│   ├── Agreements/
│   ├── Contact Info/
│   └── Insurance Certificates/
│
├── 12 - Closeout/
│   ├── Warranties/
│   ├── O&M Manuals/
│   ├── As-Built Drawings/
│   ├── Lien Releases/
│   ├── Punchlist/
│   ├── Commissioning/
│   ├── Training Records/
│   ├── Attic Stock/
│   └── LEED & Sustainability/
│
├── 13 - Correspondence/
│   ├── Owner/
│   ├── Architect/
│   ├── Subs/
│   └── Internal/
│
├── 14 - Schedule/
│   ├── Baseline/
│   ├── Updates/                            ← Named with date: Schedule Update 2026-02-24
│   └── Look Aheads/
│
├── _Inbox/                                 ← DROP ZONE: Unsorted files land here
│                                              AI classifies and moves them automatically
│
└── _Archive/                               ← Superseded/old files. AI deprioritizes.
```

### What Makes This Better Than What Exists

**For the PM:**
- **Numbered top-level folders** follow the project lifecycle (pre-con → closeout). Natural reading order.
- **Status subfolders in Submittals/RFIs/COs** — glance at a folder and know your pipeline. No spreadsheet needed.
- **`Current Set` in Drawings** — always the latest. No more "which PDF is the real one?"
- **`_Inbox` drop zone** — PM doesn't have to think about where to put a file. Drop it, the AI sorts it. This alone saves hours.
- **CSI divisions tucked under `02 - Specifications`** — still there, still standard, but not dominating the root with 18 folders.
- **Consistent depth** — max 3 levels. Root → Category → Status/Type → File.
- **Pay Apps stay as files, not individual folders** — `PAY-001-february-2026.pdf` is cleaner than 10 empty folders with one file each.

**For the AI:**
- **Numbered prefixes on every top-level folder** = deterministic sort, parseable routing
- **Status subfolders are numbered** (`01 - Open`, `02 - Under Review`) = pipeline stage is in the path
- **`_Inbox`** = the AI's workqueue. New file appears → classify → move to correct location → index in DB
- **`_Archive` prefix** = AI knows to lower retrieval priority on these files
- **`Current Set`** = AI always knows where the authoritative drawings are
- **CSI under one parent** = AI can glob `02 - Specifications/Div */` instead of scanning root
- **No loose files at root** — enforced by `_Inbox` pattern. If it's at root, it's a folder.

---

## Part 1.5: Procore ↔ NERV Data Sync

### The Critical Question
*"If a super uploads a daily log from the field to Procore, how long before NERV has it?"*

### Answer: Seconds — via Procore Webhooks + API Pull

Procore natively supports webhooks. When an event occurs in Procore (web, mobile, or API), Procore sends an HTTPS POST to NERV's endpoint with the event details. NERV then pulls the full record via API.

### Sync Architecture

```
┌─────────────┐     webhook (instant)     ┌─────────────┐
│   PROCORE    │ ──────────────────────── │    NERV      │
│              │                           │              │
│  Super uploads│     POST /events         │  Webhook     │
│  daily log   │ ─────────────────────── │  Receiver    │
│  from field  │                           │      │       │
│              │     GET /daily_logs/{id}   │      ▼       │
│              │ ◄─────────────────────── │  API Pull    │
│              │     (full record + files)  │      │       │
│              │ ─────────────────────── │      ▼       │
│              │                           │  Classify +  │
│              │                           │  File + Index│
│              │                           │      │       │
│              │                           │      ▼       │
│              │                           │  Agent Queue │
└─────────────┘                           └─────────────┘
```

### Three Ingest Channels

| Channel | Latency | How It Works |
|---------|---------|--------------|
| **Procore Webhooks** | ~5 seconds | Procore fires event → NERV catches it → API pull for full data |
| **Email** | ~30 seconds | Email arrives → parsed → classified → filed → routed to agent |
| **_Inbox Drop** | ~60 seconds | File appears in _Inbox → AI classifies → moves + indexes |

### Procore Webhook Events We Subscribe To

| Resource | Events | Why |
|----------|--------|-----|
| Submittals | create, update | EVA-01 processing pipeline |
| RFIs | create, update | EVA-02 processing pipeline |
| Daily Logs | create, update | Morning report compilation |
| Documents | create, update | File sync + classification |
| Change Orders | create, update | CO tracking + cost impact |
| Drawings | create, update | Revision tracking (metadata only — live set stays in Procore) |
| Meeting Minutes | create | Filing + distribution tracking |
| Inspections | create, update | Compliance monitoring |

### Polling Safety Net

Even with webhooks, we run a background poll every **15 minutes** that:
1. Queries Procore for anything modified since last sync timestamp
2. Compares against local DB records
3. Pulls anything missing (webhook could have failed/been missed)
4. Logs discrepancies for monitoring

This means the absolute worst-case latency is 15 minutes. Typical case is under 10 seconds.

### NERV → Procore (Write-Back)

When agents create drafts (submittal reviews, RFI responses), they stage locally first. Nothing pushes to Procore until the PM approves. Flow:

```
Agent creates draft → Staged in NERV → PM reviews → PM approves → API push to Procore
```

**Rule: NERV never writes to Procore without human approval.** This is a core trust boundary.

### Deployment Requirement

For webhooks to work, NERV needs an HTTPS endpoint reachable by Procore's servers. Options:
1. **Cloudflare Tunnel / ngrok** — NERV box on client LAN, tunneled to public URL
2. **VPS relay** — Lightweight webhook receiver on a $5/mo VPS, forwards to NERV
3. **Client static IP** — If client has one, direct port forward (less common)

Option 2 (VPS relay) is the most reliable for client deployments. The relay is stateless — just forwards webhook payloads to the NERV box's local endpoint.

---

### The _Inbox Workflow (Key Differentiator)

This is one of the biggest selling points to a PM:

```
PM gets a submittal PDF via email
  → Drops it in _Inbox (or emails it to the project inbox)
  → AI detects new file in _Inbox
  → AI reads the document, classifies it: "This is a submittal for Div 08 - storefront glazing"
  → AI renames it: {ProjectCode}-SUB-007-storefront-glazing-2026-02-24.pdf
  → AI moves it to: 04 - Submittals/01 - Open/
  → AI creates DB record in submittals table
  → AI routes to EVA-01 for review
  → PM gets notification: "New submittal filed and queued for review"
```

**The PM's effort: drag one file. The AI does the rest.**

### Training Guide (Client Deliverable)

Part of the $15K setup includes a simple best-practices guide:

> **"Working with your AI Agent — File Management"**
>
> 1. **Use the _Inbox** — Don't worry about where files go. Drop them in _Inbox and your agent will sort, rename, and file them for you.
> 2. **Don't rename files the agent has named** — The naming convention is how the agent tracks documents. If you rename it, the agent loses the link.
> 3. **Check status folders, not spreadsheets** — Want to know which submittals are pending? Open `04 - Submittals/01 - Open/`. Done.
> 4. **Current Set = the truth** — `03 - Drawings/Current Set/` always has the latest drawings. Old sets are in Archive.
> 5. **One file, one location** — Don't copy files between folders. If you need to reference a submittal in a Division folder, the agent handles cross-referencing in the system.
> 6. **Let the agent move files between status folders** — When a submittal is approved, the agent moves it from `Open` to `Approved`. You just confirm the approval.

---

## Part 2: File Naming Convention

### The Formula

```
{Project Code}-{Category}-{Sequence}-{Description}-{Date}-{Revision}.{ext}
```

### Broken Down

| Component | Format | Example | Required? |
|-----------|--------|---------|-----------|
| Project Code | Short alphanumeric | `1750NW15` | Yes |
| Category | 2-3 letter code | `SUB`, `RFI`, `CO`, `DWG` | Yes |
| Sequence | Zero-padded number | `001`, `042` | Yes |
| Description | Kebab-case, concise | `storefront-glazing` | Yes |
| Date | YYYY-MM-DD | `2026-02-24` | Yes |
| Revision | `vN` or `rN` | `r1`, `r2` | If applicable |

### Category Codes

| Code | Meaning |
|------|---------|
| `SUB` | Submittal |
| `RFI` | RFI |
| `CO` | Change Order |
| `DWG` | Drawing |
| `SPEC` | Specification |
| `MTG` | Meeting Minutes |
| `DLY` | Daily Report |
| `PAY` | Pay Application |
| `INV` | Invoice |
| `COR` | Correspondence |
| `PHO` | Photo |
| `SAF` | Safety |
| `CON` | Contract |
| `PER` | Permit |
| `ASI` | Architect's Supplemental Instruction |
| `BUL` | Bulletin |
| `TRN` | Transmittal |
| `PLI` | Punchlist Item |
| `WRN` | Warranty |
| `INS` | Inspection Report |
| `BND` | Bond |
| `LNW` | Lien Waiver |

### Real Examples

```
1750NW15-SUB-007-storefront-glazing-2026-02-24-r1.pdf
1750NW15-RFI-023-slab-edge-detail-2026-02-20.pdf
1750NW15-CO-003-added-blocking-2026-02-18.pdf
1750NW15-DWG-A301-floor-plan-level-3-2026-01-15-r4.pdf
1750NW15-MTG-012-oac-weekly-2026-02-21.pdf
1750NW15-DLY-2026-02-24.pdf
1750NW15-PAY-06-february-2026.pdf
```

### Why This Naming Works

**For the PM:**
- Scan any folder and instantly know: which project, what type, what it is, when
- Sort by name = sort by sequence. Sort by date = chronological.
- No ambiguity — "SUB-007" is always submittal #7

**For the AI:**
- 100% parseable by regex — every component extractable programmatically
- Project code = instant project association without reading file contents
- Category code = instant routing to correct agent (SUB → EVA-01, RFI → EVA-02)
- Date = instant timeline placement
- Revision = instant version tracking without opening the file
- Consistent format = zero edge cases in file processing pipelines

---

## Part 3: Database Schema

### Core Tables

```sql
-- =============================================
-- COMPANY & PROJECT
-- =============================================

CREATE TABLE companies (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,       -- e.g., 'miller-construction'
    procore_id      BIGINT,                     -- linked Procore company ID
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE projects (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    name            TEXT NOT NULL,
    code            TEXT NOT NULL,               -- e.g., '1750NW15' (used in file naming)
    slug            TEXT NOT NULL,               -- e.g., '1750-nw-15th-st'
    address         TEXT,
    city            TEXT,
    state           TEXT DEFAULT 'FL',
    procore_id      BIGINT,                      -- linked Procore project ID
    status          TEXT DEFAULT 'active',        -- active | on-hold | closed
    start_date      DATE,
    target_completion DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, code)
);

-- =============================================
-- CONTACTS & ROLES
-- =============================================

CREATE TABLE contacts (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    name            TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    role            TEXT,                         -- PM, Super, Exec, Architect, etc.
    organization    TEXT,                         -- their firm name
    procore_id      BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE project_contacts (
    project_id      INT REFERENCES projects(id),
    contact_id      INT REFERENCES contacts(id),
    role_on_project TEXT NOT NULL,                -- PM, Owner Rep, Architect, Sub, etc.
    is_primary      BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (project_id, contact_id)
);

-- =============================================
-- DOCUMENTS (the file index)
-- =============================================

CREATE TABLE documents (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    category        TEXT NOT NULL,                -- SUB, RFI, CO, DWG, etc.
    sequence_num    INT,                          -- the 001, 002 in naming
    title           TEXT NOT NULL,                -- human-readable title
    description     TEXT,
    file_path       TEXT NOT NULL,                -- relative path in project folder
    file_name       TEXT NOT NULL,                -- the actual filename
    file_size       BIGINT,
    mime_type       TEXT,
    revision        INT DEFAULT 1,
    status          TEXT,                          -- category-specific status
    source          TEXT,                          -- 'upload' | 'email' | 'procore' | 'ai-generated'
    uploaded_by     INT REFERENCES contacts(id),
    procore_id      BIGINT,
    checksum        TEXT,                          -- SHA-256 for dedup
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_category ON documents(project_id, category);
CREATE INDEX idx_documents_status ON documents(project_id, category, status);

-- =============================================
-- SUBMITTALS
-- =============================================

CREATE TABLE submittals (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    number          INT NOT NULL,                 -- Submittal number (SUB-007)
    title           TEXT NOT NULL,
    spec_section    TEXT,                          -- e.g., '08 44 13'
    status          TEXT DEFAULT 'open',           -- open | under-review | approved | revise-resubmit | rejected
    priority        TEXT DEFAULT 'normal',         -- low | normal | high | critical
    submitted_by    INT REFERENCES contacts(id),   -- which sub
    assigned_to     INT REFERENCES contacts(id),   -- which PM/reviewer
    due_date        DATE,
    closed_date     DATE,
    procore_id      BIGINT,
    document_id     INT REFERENCES documents(id),  -- link to PDF
    ai_review_json  JSONB,                          -- EVA-01 review output
    ai_reviewed_at  TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, number)
);

-- =============================================
-- RFIs
-- =============================================

CREATE TABLE rfis (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    number          INT NOT NULL,
    subject         TEXT NOT NULL,
    question        TEXT,
    answer          TEXT,
    status          TEXT DEFAULT 'open',           -- open | answered | closed
    priority        TEXT DEFAULT 'normal',
    initiated_by    INT REFERENCES contacts(id),
    assigned_to     INT REFERENCES contacts(id),
    due_date        DATE,
    answered_date   DATE,
    cost_impact     BOOLEAN,
    schedule_impact BOOLEAN,
    procore_id      BIGINT,
    document_id     INT REFERENCES documents(id),
    ai_draft_json   JSONB,                          -- EVA-02 draft output
    ai_drafted_at   TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, number)
);

-- =============================================
-- DAILY REPORTS
-- =============================================

CREATE TABLE daily_reports (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    report_date     DATE NOT NULL,
    weather         JSONB,                          -- temp, conditions, wind
    manpower        JSONB,                          -- [{trade, count, hours}]
    work_performed  TEXT,
    delays          TEXT,
    visitors        TEXT,
    safety_notes    TEXT,
    document_id     INT REFERENCES documents(id),
    ai_generated    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, report_date)
);

-- =============================================
-- CHANGE ORDERS
-- =============================================

CREATE TABLE change_orders (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    number          INT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT DEFAULT 'pending',         -- pending | approved | rejected
    amount          DECIMAL(12,2),
    days_impact     INT DEFAULT 0,
    initiated_by    INT REFERENCES contacts(id),
    procore_id      BIGINT,
    document_id     INT REFERENCES documents(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, number)
);

-- =============================================
-- AI ACTIVITY LOG (everything the agents do)
-- =============================================

CREATE TABLE ai_activity_log (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    agent           TEXT NOT NULL,                  -- 'eva-01', 'eva-02', 'katsuragi', etc.
    action          TEXT NOT NULL,                  -- 'review', 'draft', 'classify', 'flag', 'route'
    target_type     TEXT,                           -- 'submittal', 'rfi', 'email', 'document'
    target_id       INT,                            -- FK to relevant table
    input_summary   TEXT,                           -- what was fed to the agent
    output_summary  TEXT,                           -- what the agent produced
    confidence      DECIMAL(3,2),                   -- 0.00 - 1.00
    duration_ms     INT,                            -- processing time
    status          TEXT DEFAULT 'completed',        -- completed | failed | needs-review
    reviewed_by     INT REFERENCES contacts(id),    -- human who reviewed the output
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_log_project ON ai_activity_log(project_id);
CREATE INDEX idx_ai_log_agent ON ai_activity_log(agent);
CREATE INDEX idx_ai_log_created ON ai_activity_log(created_at);

-- =============================================
-- EMAIL INGEST (for email triage)
-- =============================================

CREATE TABLE emails (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),    -- NULL if unclassified
    message_id      TEXT UNIQUE NOT NULL,            -- email Message-ID header
    from_address    TEXT NOT NULL,
    from_contact    INT REFERENCES contacts(id),
    to_addresses    TEXT[],
    cc_addresses    TEXT[],
    subject         TEXT NOT NULL,
    body_text       TEXT,
    received_at     TIMESTAMPTZ NOT NULL,
    priority        TEXT DEFAULT 'normal',           -- AI-assigned: low | normal | high | urgent
    category        TEXT,                            -- AI-assigned: submittal | rfi | schedule | financial | general
    routed_to       TEXT,                            -- which agent handled it
    status          TEXT DEFAULT 'unread',            -- unread | triaged | actioned | archived
    attachments     JSONB,                           -- [{filename, path, size, mime_type}]
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_emails_project ON emails(project_id);
CREATE INDEX idx_emails_status ON emails(status);

-- =============================================
-- MORNING REPORTS
-- =============================================

CREATE TABLE morning_reports (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    report_date     DATE NOT NULL,
    content         JSONB NOT NULL,                  -- structured report data
    delivered_at    TIMESTAMPTZ,
    delivery_method TEXT,                             -- 'telegram' | 'email' | 'nerv'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, report_date)
);
```

### Why This Schema Works

**For the PM (via NERV interface):**
- Every record links to a project → simple filtering
- Status fields match the language PMs already use (open, approved, revise-resubmit)
- Contact/role tracking means the AI knows who to route things to
- Document table is the single source of truth for "where is this file?"

**For the AI:**
- `ai_review_json` / `ai_draft_json` = structured agent output, reviewable and auditable
- `ai_activity_log` = complete audit trail of everything agents did, with confidence scores
- `source` field on documents = AI knows if it ingested the file or a human uploaded it
- `emails` table with AI-assigned priority/category = automatic triage pipeline
- `morning_reports` as structured JSONB = templatable, consistent delivery
- Every table has timestamps = full timeline reconstruction
- Procore IDs on everything = bidirectional sync capability

---

## Part 3.5: Additional Tables (MAGI Research — 2026-02-25)

Based on exhaustive research into PM document management best practices, the following tables
are required to support the full institutional knowledge vision.

```sql
-- =============================================
-- DOCUMENT EMBEDDINGS (semantic search via pgvector)
-- =============================================

CREATE TABLE document_embeddings (
    id              SERIAL PRIMARY KEY,
    document_id     INT REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,                -- position within document
    chunk_text      TEXT NOT NULL,                -- the actual text chunk
    embedding       vector(1536),                -- OpenAI ada-002 or equivalent
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_embeddings_vector ON document_embeddings USING ivfflat (embedding vector_cosine_ops);

-- =============================================
-- TRANSMITTALS (formal document transfer tracking)
-- =============================================

CREATE TABLE transmittals (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    number          INT NOT NULL,
    from_contact    INT REFERENCES contacts(id),
    to_contact      INT REFERENCES contacts(id),
    subject         TEXT NOT NULL,
    items           JSONB NOT NULL,              -- [{document_id, description, copies, action}]
    sent_date       DATE NOT NULL,
    received_date   DATE,
    method          TEXT,                         -- email | hand-delivery | mail | courier
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, number)
);

-- =============================================
-- VENDOR PERFORMANCE (cross-project intelligence)
-- =============================================

CREATE TABLE vendor_performance (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),  -- the GC client
    vendor_name     TEXT NOT NULL,
    vendor_contact  INT REFERENCES contacts(id),
    trade           TEXT,                           -- e.g., 'concrete', 'electrical', 'drywall'
    project_id      INT REFERENCES projects(id),
    rating          INT CHECK (rating BETWEEN 1 AND 5),
    quality_score   DECIMAL(3,2),                   -- 0.00-1.00
    timeliness_score DECIMAL(3,2),
    responsiveness_score DECIMAL(3,2),
    notes           TEXT,
    issues          JSONB,                           -- [{date, description, severity, resolved}]
    would_rehire    BOOLEAN,
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vendor_perf_trade ON vendor_performance(trade);
CREATE INDEX idx_vendor_perf_company ON vendor_performance(company_id);

-- =============================================
-- LESSONS LEARNED (institutional knowledge)
-- =============================================

CREATE TABLE lessons_learned (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    project_id      INT REFERENCES projects(id),   -- NULL if company-wide
    category        TEXT NOT NULL,                   -- 'design', 'procurement', 'construction', 'safety', 'closeout'
    trade           TEXT,                            -- CSI division or trade name
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    impact          TEXT,                            -- what went wrong or right
    recommendation  TEXT,                            -- what to do next time
    severity        TEXT DEFAULT 'medium',           -- low | medium | high | critical
    source          TEXT,                            -- 'manual' | 'ai-detected' | 'meeting-minutes'
    tags            TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lessons_category ON lessons_learned(category);
CREATE INDEX idx_lessons_trade ON lessons_learned(trade);

-- =============================================
-- BID HISTORY (historical pricing intelligence)
-- =============================================

CREATE TABLE bid_history (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    project_id      INT REFERENCES projects(id),
    trade           TEXT NOT NULL,
    scope_description TEXT,
    bid_amount      DECIMAL(14,2),
    awarded_amount  DECIMAL(14,2),
    final_amount    DECIMAL(14,2),                  -- after COs
    bidder_name     TEXT,
    awarded         BOOLEAN,
    unit_prices     JSONB,                           -- [{item, unit, price}] for cost/SF etc.
    square_footage  DECIMAL(12,2),
    bid_date        DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bid_history_trade ON bid_history(trade);

-- =============================================
-- INSURANCE CERTIFICATES (expiration tracking)
-- =============================================

CREATE TABLE insurance_certificates (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    vendor_name     TEXT NOT NULL,
    contact_id      INT REFERENCES contacts(id),
    policy_type     TEXT NOT NULL,                   -- 'GL', 'WC', 'auto', 'umbrella', 'professional'
    carrier         TEXT,
    policy_number   TEXT,
    effective_date  DATE NOT NULL,
    expiration_date DATE NOT NULL,
    document_id     INT REFERENCES documents(id),
    alert_sent      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insurance_expiry ON insurance_certificates(expiration_date);

-- =============================================
-- PUNCHLIST ITEMS (individual item tracking)
-- =============================================

CREATE TABLE punchlist_items (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    number          INT NOT NULL,
    location        TEXT NOT NULL,                   -- room/area description
    description     TEXT NOT NULL,
    assigned_to     TEXT,                            -- sub/trade responsible
    status          TEXT DEFAULT 'open',              -- open | in-progress | complete | verified
    priority        TEXT DEFAULT 'normal',
    photo_ids       INT[],                            -- references to documents (photos)
    due_date        DATE,
    completed_date  DATE,
    verified_by     INT REFERENCES contacts(id),
    procore_id      BIGINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, number)
);

-- =============================================
-- CLOSEOUT CHECKLIST (auto-generated from specs)
-- =============================================

CREATE TABLE closeout_checklist (
    id              SERIAL PRIMARY KEY,
    project_id      INT REFERENCES projects(id),
    spec_section    TEXT NOT NULL,                    -- CSI section number
    item_type       TEXT NOT NULL,                    -- 'warranty', 'o_and_m', 'as_built', 'attic_stock', 'training', 'leed'
    description     TEXT NOT NULL,
    responsible_sub TEXT,
    status          TEXT DEFAULT 'pending',            -- pending | submitted | approved | na
    document_id     INT REFERENCES documents(id),
    due_date        DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- DOCUMENT RETENTION POLICY
-- =============================================

CREATE TABLE retention_policies (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    document_type   TEXT NOT NULL,                    -- 'contract', 'pay_app', 'daily_log', etc.
    retention_years INT NOT NULL DEFAULT 13,          -- Florida: statute of repose (10) + 3
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Ball-in-Court Tracking (added to existing tables)

```sql
-- Add to submittals table
ALTER TABLE submittals ADD COLUMN ball_in_court INT REFERENCES contacts(id);
ALTER TABLE submittals ADD COLUMN ball_in_court_since TIMESTAMPTZ;

-- Add to rfis table
ALTER TABLE rfis ADD COLUMN ball_in_court INT REFERENCES contacts(id);
ALTER TABLE rfis ADD COLUMN ball_in_court_since TIMESTAMPTZ;

-- Add to change_orders table
ALTER TABLE change_orders ADD COLUMN ball_in_court INT REFERENCES contacts(id);
ALTER TABLE change_orders ADD COLUMN ball_in_court_since TIMESTAMPTZ;

-- Add version chain to documents
ALTER TABLE documents ADD COLUMN parent_document_id INT REFERENCES documents(id);
```

---

## Part 4: How It All Connects

```
Email arrives
  → emails table (classified by AI)
  → attachment saved to file system (correct folder + naming)
  → documents table (indexed)
  → routed to agent (EVA-01 for submittals, EVA-02 for RFIs)
  → agent processes → output saved to submittals/rfis table
  → ai_activity_log records the action
  → morning_report compiles overnight activity
  → delivered to PM at 6 AM
```

**File system = human interface** (browse, find, read)
**Database = AI interface** (query, filter, track, report)
**Both stay in sync** — every file has a documents row, every document row has a file_path.

---

## Part 5: Migration Path

For existing projects:
1. Procore Drive bulk import → dump into raw staging folder
2. AI classifies and renames files using the naming convention
3. Files moved to correct project folder structure
4. Documents table populated with metadata
5. PM reviews and corrects any misclassifications (training data for the AI)

This means onboarding an existing project isn't manual data entry — the AI does the heavy lifting and the PM just validates.
