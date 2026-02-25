# NERV Command Session Review — Improvements & Gaps
> Analyzed: 2026-02-25 00:50 AM
> Source: SESSION-EXPORT-2026-02-24-NERV.md

## Items Discussed That Need Follow-Through

### 1. Database Architecture Gaps Identified
- **No `embeddings` table** — We discussed the embedding pipeline (8GB index for 15TB), but the schema doesn't have a table for vector embeddings. Need a `document_embeddings` table with pgvector.
- **No `smartsheet_sync` table** — Smartsheet integration was locked in as entry strategy, but no schema exists for tracking Smartsheet row ↔ NERV record mappings.
- **No `vendor_history` / `lessons_learned` tables** — We said institutional knowledge is the moat (old bids, vendor history, lessons learned), but the schema only covers active project documents. Need tables for:
  - `vendor_performance` — track sub reliability, quality, responsiveness across projects
  - `lessons_learned` — tagged insights from past projects, searchable by category/trade
  - `bid_history` — historical bid data for cost estimation intelligence
- **No `user_profiles` table** — Multi-project deployment means multiple PMs. Need user/role/permission tracking per project.

### 2. CSI Division Structure — Outdated
- Schema uses Divisions 00-17 (1995 CSI MasterFormat). Current standard is MasterFormat 2020 with Divisions 00-49. While Div 00-17 covers most of what a mid-size GC uses, we should at minimum support Div 21 (Fire Suppression), Div 22 (Plumbing), Div 23 (HVAC), Div 26 (Electrical), Div 27 (Communications), Div 28 (Electronic Safety), Div 31 (Earthwork), Div 32 (Exterior Improvements), Div 33 (Utilities).
- MAGI research (Task 3) should confirm this.

### 3. Smartsheet Integration — Not Yet Designed
- Decision: Smartsheet is the entry point for client adoption
- Needed: webhook receiver for Smartsheet events, API adapter for read/write, mapping logic between Smartsheet rows and NERV records
- This is a Phase 1 priority per the strategic discussion

### 4. CAD → DXF Conversion Pipeline
- Mentioned but not designed. Need to spec:
  - Input formats (DWG, RVT, IFC)
  - Conversion tooling (ODA File Converter for DWG→DXF, IfcOpenShell for IFC)
  - Automation trigger (new file in CAD folder → convert → index)

### 5. NERV Box Deployment Architecture
- VPS relay for webhooks mentioned but not specced
- Cloudflare Tunnel vs VPS relay decision needed
- Client network requirements doc needed for sales

### 6. Morning Report Template
- `morning_reports` table exists but no template for what the report actually contains
- Should define sections: overnight activity summary, deadline alerts, pipeline status, risk flags, draft items for review

### 7. Procore Drive Bulk Import
- One-time onboarding process described (7-33 hours transfer, overnight catalog, 15-30 min embed)
- No actual script/tooling exists yet
- Need: Procore Drive API integration, bulk download orchestrator, classification pipeline

## Ideas for Improvement (Not Discussed But Valuable)

### A. Document Version Chain
- Current `documents` table has `revision` as an INT but no link between versions
- Add `parent_document_id` to create version chains (r1 → r2 → r3)
- Enables "show me the history of this submittal" queries

### B. Automated Deadline Tracking
- Submittals and RFIs have `due_date` but no escalation logic
- Add `escalation_rules` table or JSONB config: "if RFI is 3 days from due and unanswered, escalate to PM + architect"

### C. Cross-Project Intelligence
- The moat is institutional knowledge across ALL projects
- Need query patterns that span projects: "what was our average submittal turnaround on the last 3 projects?"
- `vendor_performance` table should aggregate across projects automatically

### D. Photo Intelligence
- Daily report photos are filed but not analyzed
- GPU on the NERV box could run local vision models for: progress tracking, safety compliance (PPE detection), quality issues
- Future feature but architecturally plan for it now (add `ai_analysis_json` to photos)

## Priority Actions
1. Add missing tables (embeddings, smartsheet_sync, vendor_performance, lessons_learned, bid_history, user_profiles)
2. Update CSI divisions to MasterFormat 2020 (pending MAGI research confirmation)
3. Design Smartsheet adapter schema
4. Create morning report template
5. Add document version chains
