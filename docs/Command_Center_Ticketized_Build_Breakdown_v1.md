# STEELSYNC

## Command Center & Intelligence Layer — Ticketized Build Breakdown

**Agent Framework Implementation Sequence**

Version 1.0 | March 2026

**CONFIDENTIAL — FOR INTERNAL USE ONLY**

---

## Overview

This document breaks the Command Center Implementation Plan v2 (Tasks 1–10) into discrete, self-contained tickets designed for direct handoff to Claude Code. Each ticket specifies a goal, inputs, expected outputs, agent implementation notes, and acceptance criteria. The format mirrors the Document Pipeline Ticketized Build Breakdown that has proven effective for agent-driven implementation.

The ticketized breakdown preserves the original task sequence and dependency structure from the Implementation Plan v2 while decomposing larger tasks into granular, testable units of work. Where the Implementation Plan says "2 sessions," this document specifies exactly what those sessions build.

### Relationship to Existing Specs

This document is implementation-focused. It incorporates requirements from the following specifications directly into the relevant tickets so the agent has everything in one place:

- **Intelligence Layer System Design v1** — signal schema, intelligence item taxonomy, synthesis cycle design, working memory lifecycle, decay/confidence models
- **Synthesis Prompt Templates v1** — all four production prompt templates (Morning Briefing, Midday Checkpoint, End-of-Day Consolidation, Escalation Review) are incorporated into Task 4 tickets
- **Signal Type Scoping Specification v1** — local LLM vs. Opus assignment matrix, output contract, category enforcement rules
- **Document Pipeline Integration Point Specification v1** — Path A (webhook) and Path B (document pipeline) hook points, signal_hints optimization, deduplication logic
- **Command Center & Radar Feature Specification v1** — dashboard modules, Radar item structure, monitoring mechanisms, role-based views
- **Radar Pipeline Integration Specification v1** — Radar active analysis embedded in synthesis cycle, passive monitoring pipeline, cost model
- **Baseline Establishment Mode Specification v1** — three-phase onboarding, calibration context block, go-live transition criteria

### Critical Path

**CC-1.1 → CC-2.1 → CC-2.2 → CC-2.3 → CC-3.1 → CC-3.2 → CC-3.3 → CC-3.5 → CC-4.1 → CC-4.2 → CC-6.3 → CC-6.4**

This is the intelligence cycle through to the Command Center. If the prototype proves one thing, it should be that the signal → synthesis → intelligence item → Command Center pipeline produces genuinely useful output against real project data.

### Parallel Tracks

- **Frontend Track:** CC-1.4 → CC-1.5 can run in parallel with CC-2.x (signal generation). The frontend scaffold doesn't depend on signals existing.
- **Radar Backend Track:** CC-5.1 can start as soon as CC-1.1 is done. CC-5.2–5.3 (UI) need the frontend scaffold (CC-1.5). CC-5.4–5.6 (monitoring) need the signal pipeline (CC-2.2).
- **Polish Track:** CC-6.1–6.2 can start once Phase 4 is functional. CC-6.3–6.4 require everything before them.

### Model Strategy

- **Signal Generation (Phase 2):** Deterministic code for mechanical signals (date comparisons, threshold checks). Local LLM (DeepSeek via Ollama) for signals requiring content interpretation. No Opus calls at ingestion time.
- **Synthesis Cycle (Phase 3):** Claude Opus exclusively. The synthesis cycle is the product's core analytical output. All four prompt templates target Opus.
- **Radar Judgment (Phase 5):** Opus for Stage 3 relevance judgment in the passive monitoring pipeline. Radar accuracy is a direct trust metric.

---

## Ticket Summary & Dependencies

| Ticket | Description | Depends On | Effort |
|--------|-------------|------------|--------|
| **Phase 1: Foundation** | | | |
| CC-1.1 | Intelligence Layer Schema Creation | None | 1 hour |
| CC-1.2 | Data API Endpoint Inventory & Creation | CC-1.1 | 2 hours |
| CC-1.3 | Intelligence Data API Endpoints | CC-1.1 | 1 hour |
| CC-1.4 | Frontend Scaffold & Project List | CC-1.2 | 2–3 hours |
| CC-1.5 | Command Center Layout & Navigation | CC-1.4 | 2 hours |
| **Phase 2: Signal Generation** | | | |
| CC-2.1 | Deterministic Signal Detectors | CC-1.1 | 2 hours |
| CC-2.2 | Signal Generation Service Core | CC-2.1 | 2–3 hours |
| CC-2.3 | Path A: Webhook → Signal Hook | CC-2.2 | 1–2 hours |
| CC-2.4 | Path B: Document Pipeline → Signal Hook | CC-2.2, Doc Pipeline Phase 5 | 1–2 hours |
| CC-2.5 | Reinforcement Candidate Pipeline | CC-2.2 | 1 hour |
| CC-2.6 | Signal Deduplication & Testing | CC-2.3, CC-2.4 | 1 hour |
| **Phase 3: Synthesis Cycle** | | | |
| CC-3.1 | Synthesis Engine Core & Scheduling | CC-2.1 | 2–3 hours |
| CC-3.2 | Prompt Template Implementation | CC-3.1 | 2–3 hours |
| CC-3.3 | Intelligence Item CRUD & Evidence Chain | CC-3.1 | 1–2 hours |
| CC-3.4 | Working Memory Lifecycle Manager | CC-3.3 | 1–2 hours |
| CC-3.5 | Synthesis Validation Gate | CC-3.2, CC-3.3 | 1–2 hours |
| **Phase 4: Command Center UI** | | | |
| CC-4.1 | Project Health Cards | CC-1.5, CC-3.1 | 2 hours |
| CC-4.2 | Intelligence Feed Panel | CC-4.1 | 2–3 hours |
| CC-4.3 | RFI/Submittal Tracker with Intelligence Overlay | CC-4.1 | 2 hours |
| CC-4.4 | Synthesis Cycle Status & Manual Trigger | CC-3.1, CC-4.1 | 1 hour |
| **Phase 5: Radar** | | | |
| CC-5.1 | Radar Schema & API Endpoints | CC-1.1 | 1–2 hours |
| CC-5.2 | Radar UI: Panel & Intake Form | CC-1.5, CC-5.1 | 2–3 hours |
| CC-5.3 | Radar Detail View & Activity Log | CC-5.2 | 1–2 hours |
| CC-5.4 | Radar Passive Monitoring Pipeline | CC-2.2, CC-5.1 | 2–3 hours |
| CC-5.5 | Radar Active Analysis (Synthesis Embed) | CC-3.2, CC-5.1 | 1–2 hours |
| CC-5.6 | Radar Signal Emission & Intelligence Link | CC-5.4, CC-5.5 | 1 hour |
| **Phase 6: Polish & Validation** | | | |
| CC-6.1 | False Positive Management & User Feedback | CC-4.2 | 1–2 hours |
| CC-6.2 | Baseline Establishment Mode | CC-3.1, CC-5.1 | 2–3 hours |
| CC-6.3 | End-to-End Validation Scenario | All above | 1–2 hours |
| CC-6.4 | Visual Polish & Brand Consistency | All above | 1–2 hours |

**Estimated total effort:** 35–50 hours of focused agent sessions. At the pace Claude Code has been executing on the Document Pipeline, this is achievable in approximately 1–2 weeks.

---

## Phase 1: Foundation

Get the intelligence layer schema created, existing data exposed through API endpoints, and a frontend scaffold connected to real data. Everything else depends on this phase.

---

### CC-1.1: Intelligence Layer Schema Creation

**Goal:** Create all database tables required by the intelligence layer. These tables store signals, synthesis cycle metadata, intelligence items, evidence chains, and working memory state. This is the data foundation for the entire intelligence cycle.

**Inputs:**
- Existing PostgreSQL schema (31+ tables from Procore sync + document pipeline)
- Signal schema from Intelligence Layer System Design v1 Section 8
- Intelligence item schema from System Design v1 Section 10
- Synthesis cycle schema from System Design v1 Section 11

**Expected Outputs:**
- `signals` table: id (UUID PK), project_id (FK), source_type (enum: procore_webhook, document_pipeline, radar_match, manual), source_document_id (UUID), signal_type (varchar), signal_category (enum: status_change, contradiction, reinforcement, timeline, actor_pattern, document_significance, cross_project, radar_match), summary (text), confidence (decimal 0.0–1.0), strength (decimal 0.0–1.0), effective_weight (decimal, computed), decay_profile (enum: fast_24h, medium_72h, slow_7d, persistent), entity_type (varchar), entity_value (varchar), supporting_context_json (JSONB), last_reinforced_at (timestamp), created_at (timestamp), resolved_at (timestamp), archived_at (timestamp), synthesis_cycle_id (UUID FK nullable)
- `synthesis_cycles` table: id (UUID PK), project_id (FK), cycle_type (enum: morning_briefing, midday_checkpoint, end_of_day, escalation_review), started_at, completed_at, signals_processed (int), items_created (int), items_updated (int), items_resolved (int), cycle_summary (text), overall_health (enum: green, yellow, red), model_used (varchar), input_tokens (int), output_tokens (int), error_log (text nullable)
- `intelligence_items` table: id (UUID PK), project_id (FK), item_type (enum: convergence, contradiction, pattern_match, decay_detection, cross_project_correlation, emerging_risk, watch_item), title (varchar), summary (text), severity (enum: critical, high, medium, low), confidence (decimal), status (enum: active, watch, resolved, archived), first_created_at, last_updated_at, last_reinforced_at, resolved_at, archived_at, synthesis_cycle_id (FK), source_evidence_count (int), recommended_attention_level (enum: immediate, today, tomorrow_morning, this_week, monitor), delivery_channels_json (JSONB)
- `intelligence_item_evidence` table: id (UUID PK), intelligence_item_id (FK), signal_id (FK), evidence_weight (enum: primary, supporting, circumstantial), added_at (timestamp), notes (text)
- `working_memory_state` table: id (UUID PK), project_id (FK), snapshot_at (timestamp), active_item_count (int), watch_item_count (int), total_signal_count_today (int), state_json (JSONB for tomorrow_watch_list, health_trend, etc.)
- `reinforcement_candidates` table: id (UUID PK), target_signal_id (FK), source_signal_id (FK), reason (text), confidence (decimal), status (enum: pending, promoted, discarded), created_at, evaluated_at
- All tables with appropriate indexes on project_id, created_at, status, signal_type, item_type
- Alembic migration file (or raw SQL migration) that can be applied cleanly

**Agent Implementation Notes:**
- Use UUID primary keys consistent with existing schema conventions
- Add indexes on: signals(project_id, created_at), signals(project_id, signal_category, archived_at), intelligence_items(project_id, status), intelligence_items(project_id, item_type, status)
- The effective_weight column on signals can be a stored computed column or populated by the signal generation service at write time. Formula: confidence × strength × source_multiplier × decay_factor. For now, default source_multiplier to 1.0 and decay_factor to 1.0 (decay computation comes later)
- Ensure the JSONB columns (supporting_context_json, delivery_channels_json, state_json) have GIN indexes for query performance
- Do NOT create any API endpoints in this ticket. Schema only.

**Acceptance Criteria:**
- ✓ All six tables created and accessible via psql
- ✓ Migration is repeatable (idempotent or versioned)
- ✓ Foreign key relationships enforced (project_id references projects table)
- ✓ Indexes verified with EXPLAIN on: SELECT from signals WHERE project_id = X AND archived_at IS NULL ORDER BY created_at DESC

---

### CC-1.2: Data API Endpoint Inventory & Creation

**Goal:** Audit what data exists in the database from the Procore sync, then create or verify REST API endpoints that expose this data for the Command Center frontend to consume. These endpoints serve the existing Procore-synced data (projects, RFIs, submittals, daily logs, schedule, change orders).

**Inputs:**
- Existing PostgreSQL schema with Procore sandbox data
- Existing API gateway / Flask routes
- Command Center Design Specification v1 (dashboard module data requirements)

**Expected Outputs:**
- Documented inventory of all tables with row counts, sample data, and data quality notes (which tables are populated vs. empty in sandbox)
- REST endpoints confirmed working: GET /api/projects (list with basic stats), GET /api/projects/:id (detail), GET /api/projects/:id/rfis (with status, due_date, aging), GET /api/projects/:id/submittals (with status, turnaround tracking), GET /api/projects/:id/daily-logs (with compliance status), GET /api/projects/:id/schedule (milestones, tasks), GET /api/projects/:id/change-orders (with financial summary)
- Each endpoint returns JSON with consistent pagination (limit/offset), sorting, and filtering parameters
- Response format includes metadata: total_count, page, and links to related resources

**Agent Implementation Notes:**
- Start by querying each table: SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM each. The sandbox may not have data in every table.
- Build as Flask/FastAPI routes. Authentication is not required for the prototype but structure the routes so auth middleware can be added later.
- For RFI and submittal endpoints, compute aging fields server-side: days_open, days_since_last_response, is_overdue (boolean). The frontend should not compute these.
- For daily logs, compute compliance_status: on_time, late, missing. Compare submitted_at against the expected submission time (configurable, default: next business day by 9 AM).
- If a table is empty in sandbox, the endpoint should still work and return an empty array with count: 0. Note empty tables in the inventory doc.

**Acceptance Criteria:**
- ✓ All listed endpoints return valid JSON with real sandbox data
- ✓ At least one endpoint returns non-empty data (projects endpoint)
- ✓ Aging and compliance computations are correct against manual verification
- ✓ Endpoints handle non-existent project_id with 404 (not 500)
- ✓ Table inventory document created with row counts

---

### CC-1.3: Intelligence Data API Endpoints

**Goal:** Create REST API endpoints that expose the intelligence layer data (signals, intelligence items, synthesis cycles) for the Command Center frontend. These endpoints read from the tables created in CC-1.1.

**Inputs:**
- Intelligence layer tables from CC-1.1
- Data API patterns established in CC-1.2

**Expected Outputs:**
- GET /api/projects/:id/signals — returns recent signals for a project. Filterable by signal_category, signal_type, date range. Default: last 72 hours, not archived. Sorted by effective_weight DESC.
- GET /api/projects/:id/intelligence-items — returns active + watch intelligence items. Filterable by item_type, severity, status. Sorted by severity DESC then last_updated_at DESC.
- GET /api/projects/:id/intelligence-items/:item_id — single item with full evidence chain (joined from intelligence_item_evidence + signals).
- GET /api/synthesis/cycles — recent synthesis cycle history. Filterable by project_id, cycle_type. Shows timing, item counts, health assessment.
- POST /api/synthesis/trigger — manual synthesis trigger for testing. Accepts project_id and optional cycle_type. Returns job ID for polling.
- GET /api/dashboard/overview — aggregated view across all projects: project count, active intelligence items by severity, last synthesis cycle time per project, overall health per project. This is the data source for the multi-project view.

**Agent Implementation Notes:**
- The intelligence-items endpoint must return the evidence chain inline when requested (query param ?include=evidence). Each evidence entry includes the linked signal's summary, signal_type, and source_type.
- The dashboard overview endpoint is performance-critical. Pre-aggregate where possible. A PX with 10 projects should get this response in under 200ms.
- The synthesis trigger endpoint is async. It queues the job and returns immediately. The frontend polls for completion or uses WebSocket for notification.
- All endpoints should return empty results gracefully when no intelligence data exists yet (pre-first-synthesis-cycle state).

**Acceptance Criteria:**
- ✓ All endpoints return valid JSON
- ✓ Intelligence items endpoint returns evidence chain when ?include=evidence is set
- ✓ Dashboard overview endpoint aggregates across all projects in a single response
- ✓ Synthesis trigger endpoint queues a job and returns a job_id
- ✓ Empty-state responses are clean (empty arrays, zero counts, no errors)

---

### CC-1.4: Frontend Scaffold & Project List

**Goal:** Create the React frontend application for the Command Center with a project list sidebar populated from real API data. This establishes the frontend foundation that all subsequent UI tickets build on.

**Inputs:**
- API endpoints from CC-1.2 and CC-1.3
- Existing portal codebase (for authentication integration reference)
- SteelSync brand direction: professional, dark navy/steel blue palette, no generic Bootstrap feel

**Expected Outputs:**
- React app (Vite + React) served at /command-center path
- Left sidebar with project list populated from GET /api/projects
- Each project in sidebar shows: project name, project number, colored status dot (placeholder — will be intelligence-driven in Phase 4)
- Clicking a project loads its detail area (empty placeholder panels for now)
- Tailwind CSS for styling with dark theme: navy (#1B2A4A) background, steel blue (#3B6B8A) accents, white text on dark surfaces
- Basic responsive layout: desktop-first, functional at 1920x1080 and 1440x900
- API service layer (axios or fetch wrapper) with base URL configuration and error handling

**Agent Implementation Notes:**
- Use React with Vite for fast development. Tailwind CSS for styling.
- The sidebar should show projects sorted by last activity. Active projects first, then archived.
- Implement a simple API service module that all components use. This keeps the API base URL, headers, and error handling in one place.
- The dark theme is non-negotiable for brand identity. Use navy as the primary background, steel blue for interactive elements, and ensure sufficient contrast ratios for accessibility.
- Set up React Router for navigation: /command-center (dashboard), /command-center/project/:id (project detail), /command-center/radar (Radar panel).
- Include a top bar with the SteelSync logo/wordmark area and a placeholder for user info.

**Acceptance Criteria:**
- ✓ React app loads at /command-center without errors
- ✓ Project list populated with real sandbox data from the API
- ✓ Clicking a project updates the URL and loads the detail area
- ✓ Dark theme applied consistently across all visible elements
- ✓ No console errors on initial load or navigation

---

### CC-1.5: Command Center Layout & Navigation

**Goal:** Build out the full Command Center layout with tabbed navigation, placeholder panel areas for all dashboard modules, and the Radar tab. This creates the skeleton that Phase 4 and Phase 5 tickets populate with real data.

**Inputs:**
- Frontend scaffold from CC-1.4
- Command Center & Radar Feature Specification v1 (Section 2.3: Dashboard Modules)

**Expected Outputs:**
- Project detail view with tabbed or sectioned layout containing placeholder areas for: Intelligence Feed (primary panel), Project Health summary, RFI/Submittal Tracker, Schedule Intelligence, Financial Snapshot, Daily Log Compliance
- Dedicated Radar tab in the main navigation (not buried in project detail — the Radar is a top-level feature)
- Multi-project dashboard view (the PX view): grid of project health cards as the landing page
- Navigation between: Dashboard (multi-project) → Project Detail → Radar
- Placeholder panels show placeholder content with the panel name and "Data will appear after synthesis cycle" message
- Loading states and empty states for all placeholder panels

**Agent Implementation Notes:**
- The Intelligence Feed should be the largest, most prominent panel in the project detail view. It occupies the center/main area. Other panels are secondary.
- The Radar tab should feel like a first-class destination, not a secondary feature. Give it its own route and a prominent icon in the navigation.
- Each placeholder panel should have a consistent container component: title bar, optional filter area, scrollable content area, and empty state. This component gets reused across all panels in Phase 4.
- Consider a collapsible sidebar on smaller viewports. The project list should not consume too much horizontal space on 1440px screens.
- Add a "Last updated" timestamp in the top bar showing the most recent synthesis cycle time. This is a trust signal — users need to know the data is fresh.

**Acceptance Criteria:**
- ✓ All placeholder panels render in correct layout positions
- ✓ Navigation between Dashboard, Project Detail, and Radar works without page reload
- ✓ Empty states display correctly for all panels
- ✓ Layout is functional at both 1920x1080 and 1440x900
- ✓ Radar tab is accessible from any view via the main navigation

---

## Phase 2: Signal Generation

Build the signal generation pipeline that produces structured signals from incoming data. This phase implements the first layer of the intelligence cycle: ingestion-time micro-analysis that converts raw events into typed, scored, decaying signal objects.

---

### CC-2.1: Deterministic Signal Detectors

**Goal:** Implement the signal types that do NOT require LLM inference. These are pure code: date comparisons, threshold checks, status field evaluations. Per the Signal Type Scoping Specification v1, several Category A (Status Change) and Category D (Timeline) signals are deterministic.

**Inputs:**
- Intelligence layer schema from CC-1.1 (signals table)
- Signal Type Scoping Specification v1 (Category A and D assignments)
- Local LLM Output Contract from Signal Type Scoping Spec Section 5
- Existing Procore data in database (RFIs with due dates, submittals with statuses, daily logs with timestamps)

**Expected Outputs:**
- Deterministic detector functions for: `rfi_became_overdue` (RFI due_date < current_date AND status != closed/answered), `submittal_rejected` (Procore status = rejected), `daily_log_missing` (expected log not received by threshold time, default 9 AM next business day), `schedule_milestone_approaching` (milestone date within configurable N days, default 14), `change_order_status_changed` (CO status field changed from previous value), `promised_date_passed` (stated delivery/response date has passed)
- Each detector writes signals to the signals table in the standard output contract format: signal_type, signal_category, summary, confidence, strength, decay_profile, entity_type, entity_value, supporting_context_json
- Confidence for deterministic signals is 0.95–1.0 (these are factual observations, not analytical judgments)
- A `SignalWriter` utility class that handles: validation against allowed categories, effective_weight computation, database write, and logging
- Unit tests for each detector with known test data

**Agent Implementation Notes:**
- These detectors run as pure Python functions. No LLM calls, no API calls. They query the database, evaluate conditions, and write signals.
- The `rfi_became_overdue` detector should check ALL open RFIs for the project, not just newly updated ones. This is a sweep function that can run on schedule (hourly or at each synthesis cycle start).
- `daily_log_missing` is a clock-based check. It should run once per morning (configurable) and flag any project that didn't receive yesterday's daily log.
- The `SignalWriter` utility is critical infrastructure. Every signal — deterministic and LLM-generated — flows through it. It must enforce: signal_category is in the allowed list, confidence is 0.0–1.0, required fields are present, and no duplicate signals (same source_document_id + signal_type within 1 hour).
- Write a sweep function that runs all deterministic detectors for a given project. This gets called at the start of each synthesis cycle (Phase 3) to ensure the signal set is current before synthesis runs.

**Acceptance Criteria:**
- ✓ Each detector produces correct signals against known test data (e.g., an RFI with due_date yesterday produces an rfi_became_overdue signal)
- ✓ SignalWriter rejects signals with invalid categories or missing required fields
- ✓ No duplicate signals written for the same source event within 1 hour
- ✓ Deterministic signals have confidence >= 0.95
- ✓ Sweep function runs all detectors for a project and returns count of signals generated

---

### CC-2.2: Signal Generation Service Core

**Goal:** Build the signal generation service that processes incoming data items through LLM-based signal detection. This handles signals that require content interpretation (reading email bodies, log notes, correspondence text). Implements the local LLM output contract and category enforcement.

**Inputs:**
- SignalWriter utility from CC-2.1
- Signal Type Scoping Specification v1 (full assignment matrix, output contract, category enforcement rules)
- Local LLM environment (DeepSeek via Ollama)
- Document Pipeline Integration Point Specification v1 (data available at each hook point)

**Expected Outputs:**
- `SignalGenerationService` class with methods: `evaluate_webhook_event(event_data, project_id)`, `evaluate_document(classification_data, extraction_data, project_id)`, `evaluate_batch(items, project_id)`
- LLM prompt template for signal generation: receives the data item + active signal summary for the project, returns structured JSON per the output contract
- Category enforcement: service validates LLM output against the assignment matrix. If LLM returns a contradiction, actor_pattern, or cross_project signal, the service logs the attempt but does NOT write it to the signals table.
- Output parsing: robust JSON parsing from LLM responses with fallback handling for malformed output (log error, skip signal, don't crash)
- Active signal summary builder: queries the signals table for the project's active (non-archived, non-resolved) signals and formats them as context for the LLM prompt. Bounded to last 50 signals to control context size.
- Async execution: signal generation runs in a background worker, not in the request path. Uses Redis pub/sub or a simple job queue.

**Agent Implementation Notes:**
- The LLM prompt for signal generation must be tight and structured. Include: the data item (webhook payload or document classification + extracted text), the active signal summary, a list of allowed signal types for this source_type, and the exact JSON output schema. Do NOT include vague instructions like "analyze this data."
- Category enforcement at the service level is mandatory. The local LLM will sometimes try to emit contradiction or actor_pattern signals. Log these (they're useful for understanding what the model sees) but never write them to the signals table. Only synthesis (Phase 3) produces those categories.
- For the prototype, use DeepSeek via Ollama for signal generation. The service should be model-agnostic — a config setting determines the endpoint and model name.
- The reinforcement_candidates output from the LLM is handled separately (see CC-2.5). The signal generation service writes signals to the signals table and reinforcement_candidates to the reinforcement_candidates table.
- Rate limiting: the local LLM processes one item at a time (no batching needed for prototype volumes). A simple queue with sequential processing is fine.

**Acceptance Criteria:**
- ✓ Service processes a sample webhook event and produces at least one valid signal in the database
- ✓ Service processes a sample document classification and produces a document_significance signal
- ✓ Category enforcement blocks a simulated contradiction signal from being written
- ✓ Malformed LLM output is logged but does not crash the service
- ✓ Active signal summary query returns bounded results (max 50) sorted by effective_weight

---

### CC-2.3: Path A — Webhook → Signal Generation Hook

**Goal:** Wire the signal generation service to fire asynchronously when the existing webhook receiver processes a Procore event. This is Path A from the Document Pipeline Integration Point Specification: structured API payloads that do NOT pass through the document pipeline.

**Inputs:**
- SignalGenerationService from CC-2.2
- Existing webhook receiver (services/webhook-receiver/orchestrator.py, processor.py)
- Document Pipeline Integration Point Spec v1, Section 3.1 (Path A hook point)

**Expected Outputs:**
- After the webhook receiver writes/updates a database record, it emits a signal generation job to the async queue
- The signal generation worker picks up the job, calls `SignalGenerationService.evaluate_webhook_event()` with the event payload and project_id
- Signal generation runs asynchronously and does NOT block the webhook receiver
- If signal generation fails, the webhook processing is not affected. Failure is logged and retried (3 attempts, exponential backoff).
- Logging: each signal generation attempt logged with: source event type, project_id, signals_produced count, duration_ms, success/failure

**Agent Implementation Notes:**
- The hook point is after the database write, not before. The webhook receiver must successfully write/update the record before emitting the signal generation job.
- Use Redis pub/sub or a simple database-backed job queue. The webhook receiver publishes to a channel; the signal generation worker subscribes. If Redis is already in the stack, use it. Otherwise, a PostgreSQL-backed NOTIFY/LISTEN or a simple polling table is fine for prototype.
- The first test should be: trigger a Procore webhook event from the sandbox, verify the database record is updated, then verify a signal appears in the signals table within 30 seconds.
- Create at least 5 test scenarios: RFI status change (overdue), submittal rejection, daily log submission, drawing upload, change order status change. Verify each produces appropriate signals.

**Acceptance Criteria:**
- ✓ Webhook event triggers signal generation within 30 seconds
- ✓ Signal generation failure does not block or error the webhook receiver
- ✓ At least 5 test scenarios produce correct signals
- ✓ Retry logic handles transient failures (simulate by temporarily stopping the LLM)
- ✓ Logs show signal generation timing and outcome for each event

---

### CC-2.4: Path B — Document Pipeline → Signal Generation Hook

**Goal:** Wire signal generation to fire after the document pipeline completes Stage 5 (Project Matching). This is Path B from the Integration Point Specification: documents that have been classified and matched to a project. Implements the signal_hints optimization to avoid duplicate LLM calls.

**Inputs:**
- SignalGenerationService from CC-2.2
- Document pipeline Stage 4 (Classification) and Stage 5 (Project Matching) outputs
- Document Pipeline Integration Point Spec v1, Sections 3.2 and 6 (Path B hook point, signal_hints optimization)

**Expected Outputs:**
- After Stage 5 completes, the pipeline emits a signal_generation_job to the async queue with: document_id, classification data (document_class, workflow_status, officiality), project match (matched_project_id, match_confidence), extracted text reference, parent correspondence context
- Signal generation reads the classifier's `signal_hints` block (if present) instead of invoking the LLM again for document significance signals. This halves per-document inference cost.
- If signal_hints are not present (classifier didn't produce them), the service falls back to a standard LLM evaluation
- For low-confidence project matches (below needs_pm_review threshold), signals carry a reduced source_multiplier in effective_weight calculation
- For NO project match, signal generation is skipped. The document enters the PM review queue. Signal generation fires after PM confirms the project (triggered by review queue resolution action).
- Pipeline continues to Stage 6 (Routing) immediately and in parallel — signal generation does not block the pipeline

**Agent Implementation Notes:**
- The signal_hints optimization is important for cost control. The Stage 4 classifier already does the heavy lifting of determining document_class and workflow_status. Extend the classifier output schema (if not already done in the document pipeline) to include a signal_hints block. The signal generation service then reads this block and writes the signals directly through the SignalWriter — no second LLM call needed.
- The review queue re-fire logic: when a PM resolves a review queue item and changes the classification or project match, the resolution handler emits a new signal_generation_job with a reclassification flag. The signal generator checks for and supersedes any prior signals for this document.
- This ticket depends on the document pipeline being functional through Phase 5. If the pipeline is still in progress, this ticket can be built with mock data and integrated once the pipeline is stable.

**Acceptance Criteria:**
- ✓ Document pipeline Stage 5 completion triggers signal generation asynchronously
- ✓ Signal generation does NOT block pipeline Stages 6–7
- ✓ signal_hints from classifier are read and converted to signals without a second LLM call
- ✓ Low-confidence project match produces signals with reduced effective_weight
- ✓ No-match documents skip signal generation (no error, no signal)

---

### CC-2.5: Reinforcement Candidate Pipeline

**Goal:** Implement the pipeline for reinforcement candidates: lightweight signals emitted by the local LLM when it detects entity overlap between a new data item and an existing active signal. Reinforcement candidates are NOT signals — they are pointers to existing signals that may be strengthened. The synthesis cycle (Phase 3) evaluates and promotes or discards them.

**Inputs:**
- SignalGenerationService from CC-2.2 (LLM output includes reinforcement_candidates array)
- reinforcement_candidates table from CC-1.1
- Signal Type Scoping Specification v1, Category C (Reinforcement Signals — Hybrid)

**Expected Outputs:**
- SignalGenerationService writes reinforcement_candidates to the reinforcement_candidates table (not the signals table) with: target_signal_id, source_signal_id, reason, confidence (0.50–0.70 typical), status = pending
- API endpoint: GET /api/projects/:id/reinforcement-candidates?status=pending — used by the synthesis engine to load pending candidates
- API endpoint: PATCH /api/reinforcement-candidates/:id — allows synthesis engine to update status to promoted or discarded, set evaluated_at
- When a candidate is promoted, the synthesis engine updates the target signal's last_reinforced_at timestamp and increments the related intelligence item's source_evidence_count

**Agent Implementation Notes:**
- Reinforcement candidates are the synthesis cycle's input, not its output. The local LLM says "I think this new RFI overdue event relates to existing signal sig-0089." Opus then decides whether that relationship is meaningful.
- Confidence for reinforcement candidates is moderate (0.50–0.70). The confidence is in the entity/topic match, not in the operational significance.
- The promotion logic (updating last_reinforced_at, incrementing evidence count) should be a utility function that the synthesis engine calls. The API endpoint just updates the candidate status; the promotion side-effects are handled by the caller.

**Acceptance Criteria:**
- ✓ Reinforcement candidates written to the correct table (not signals table)
- ✓ Pending candidates retrievable by project
- ✓ Promotion updates target signal's last_reinforced_at
- ✓ Discarded candidates marked with evaluated_at timestamp

---

### CC-2.6: Signal Deduplication & Integration Testing

**Goal:** Implement signal deduplication for cases where the same event triggers both Path A (webhook) and Path B (document pipeline). Run integration tests across the full signal generation pipeline.

**Inputs:**
- Path A hook from CC-2.3
- Path B hook from CC-2.4
- Document Pipeline Integration Point Spec v1, Section 5.5 (deduplication logic)

**Expected Outputs:**
- Deduplication check in SignalWriter: before writing a signal, check for existing signals with the same source_document_id AND signal_type created within the last 1 hour. If a match exists, the newer emission is logged but not written — unless it carries new information (in which case the existing signal is updated).
- Integration test suite covering: (1) Webhook event produces correct signals via Path A, (2) Document classification produces correct signals via Path B, (3) Same event via both paths produces only one signal (dedup works), (4) Deterministic sweep produces correct signals, (5) Category enforcement blocks prohibited categories, (6) Reinforcement candidates written separately from signals, (7) Failed signal generation retries correctly
- Signal generation dashboard query: a simple SQL query or API endpoint that shows signal generation statistics: total signals today, by category, by source_type, failures, retries

**Agent Implementation Notes:**
- Deduplication is timestamp-based with a 1-hour window. This is simple and sufficient for prototype. A more sophisticated approach (content hashing) can be added later if needed.
- The integration tests should use real sandbox data where possible. Trigger actual Procore webhook events, verify signals appear. If the document pipeline is running, push a test document through and verify Path B signals.
- The "carries new information" check for dedup updates: compare the supporting_context_json. If the newer signal has additional context fields not present in the existing signal, merge the context and update. Otherwise, skip.

**Acceptance Criteria:**
- ✓ Duplicate event via Path A + Path B produces exactly one signal in the database
- ✓ Update-on-new-info logic works: duplicate with additional context updates the existing signal
- ✓ All 7 integration test scenarios pass
- ✓ Signal generation statistics query returns correct counts

---

## Phase 3: Synthesis Cycle

Build the periodic synthesis engine that consumes signals, combines them with project state, and produces structured intelligence items. This is the analytical brain of the product. The synthesis cycle is the single most important component in the entire platform — it determines whether SteelSync produces genuine construction intelligence or reformatted data summaries.

---

### CC-3.1: Synthesis Engine Core & Scheduling

**Goal:** Build the synthesis engine that orchestrates the periodic intelligence cycle. The engine runs on schedule (configurable: 6 AM / 12 PM / 6 PM by default), can be triggered manually for testing, and processes one project at a time per cycle.

**Inputs:**
- Signals table populated by Phase 2
- Intelligence items and synthesis_cycles tables from CC-1.1
- Intelligence Layer System Design v1, Section 11 (synthesis cycle design)
- Synthesis Prompt Templates v1, Section 1 (template index, schedule, design principles)

**Expected Outputs:**
- `SynthesisEngine` class with methods: `run_cycle(project_id, cycle_type)`, `run_all_projects(cycle_type)`, `trigger_manual(project_id, cycle_type=None)`
- Scheduling via APScheduler or cron: morning_briefing at 6:00 AM, midday_checkpoint at 12:00 PM, end_of_day at 6:00 PM (all configurable via environment variables)
- Pre-synthesis steps: (1) Run deterministic signal sweep (from CC-2.1) to ensure signals are current, (2) Query new signals since last cycle for this project, (3) Load active/watch intelligence items, (4) Build project state snapshot from database
- Project state snapshot builder: assembles `project_snapshot_json` from the database. Includes: project name/number/phase, active trades, schedule milestones (next 30 days), open RFI/submittal counts and overdue counts, key entity list. Target: 800–1,200 tokens.
- Opus API call with structured prompt (prompt templates implemented in CC-3.2). System prompt as cached prefix.
- Response parsing: extract JSON from Opus response, validate against output schema, handle malformed responses gracefully
- Cycle metadata logging to synthesis_cycles table: cycle_type, signals_processed, items_created, items_updated, items_resolved, cycle_summary, overall_health, model_used, input/output tokens, timing
- POST /api/synthesis/trigger endpoint for manual triggering (returns immediately with job_id, runs async)
- GET /api/synthesis/status/:job_id for polling synthesis completion

**Agent Implementation Notes:**
- This is the most important task in the entire plan. The quality of the synthesis prompt determines whether the product generates genuine intelligence or reformatted summaries. Invest time here.
- The synthesis engine runs per-project. One Opus call per active project per cycle. For the prototype with 1–3 sandbox projects, this is 3–9 Opus calls per day total.
- The project state snapshot must be concise. Opus needs enough context to understand the project but not so much that signal analysis gets diluted. The 800–1,200 token target is intentional.
- Use Anthropic's prompt caching: structure the API call with the system prompt + output schema as the cached prefix. The system prompt is static per template type. At $0.50/M tokens for cache reads vs $5.00/M for fresh input, this reduces system prompt costs by 90%.
- The manual trigger is essential for development. Every prompt template iteration requires: trigger cycle → evaluate output → adjust prompt → repeat.
- Cross-project synthesis (comparing intelligence items across projects) is a second pass that runs after all per-project cycles complete. Defer to CC-3.5 or later phase if needed.

**Acceptance Criteria:**
- ✓ Synthesis engine runs a complete cycle for a sandbox project: queries signals, builds snapshot, calls Opus, parses response, writes intelligence items
- ✓ Scheduling fires at configured times (verify with manual time override for testing)
- ✓ Manual trigger via API endpoint works and returns results within 60 seconds
- ✓ Cycle metadata logged correctly to synthesis_cycles table
- ✓ Project state snapshot is within the 800–1,200 token target
- ✓ Prompt caching is enabled (verify via API response headers or token usage)

---

### CC-3.2: Prompt Template Implementation

**Goal:** Implement all four synthesis prompt templates as production code. Each template is a system prompt + user prompt pair with runtime variable substitution. The templates are defined in the Synthesis Prompt Templates v1 specification and should be implemented exactly as specified.

**Inputs:**
- SynthesisEngine from CC-3.1
- Synthesis Prompt Templates v1 (all four templates: A–D, full text)
- Signal Type Scoping Specification v1 Section 7 (impact on synthesis prompts: Opus must detect contradictions, actor patterns, and evaluate reinforcement candidates itself)

**Expected Outputs:**
- **Template A (Morning Briefing):** system prompt establishing Senior PM persona, morning cycle context, 5-point analytical mandate (what changed, convergences, contradictions, emerging signals, item status updates), anti-noise rules, state-your-assumptions mandate. User prompt with project_snapshot, signals_json, active_items_json, cycle_metadata. Output schema: cycle_summary, overall_health, intelligence_items array, working_memory_actions array. Max 5 new items per cycle.
- **Template B (Midday Checkpoint):** delta-focused analysis. Receives morning_cycle_summary as additional context. Anti-noise rules emphasize CHECKPOINT not re-analysis. Output includes morning_assessment_revisions array. Max 3 new items per cycle.
- **Template C (End-of-Day Consolidation):** full-day view. Receives all_today_signals_json + morning and midday summaries. Consolidation rules: merge related items, evaluate every active item, produce clean state for tomorrow. Output includes merge action type, persistence_note, tomorrow_watch_list (max 3). Max 7 new/merged items per cycle.
- **Template D (Escalation Review):** on-demand deep-dive on a specific item or cluster. Receives escalation_item_json, related_items_json, supporting_signals_json, cross_project_context_json. Output: escalation_assessment (justified, confidence, evidence quality, impact, recommended actions, assumptions), evidence_chain, related_context, updated_intelligence_item.
- Template variable resolver: a function that takes a template type and project_id, queries the database for all required variables, and returns the assembled system prompt + user prompt ready for the API call
- Template selection logic: given a cycle_type, return the correct template. Morning → A, Midday → B, EOD → C, Escalation → D.
- Add explicit notes to templates per Signal Type Scoping Spec Section 7: contradiction signals will NOT appear in the input signal set (Opus must detect them), actor pattern signals will NOT appear (Opus must detect behavioral patterns from accumulated status/timeline signals), reinforcement candidates WILL appear as a separate input block for evaluation.

**Agent Implementation Notes:**
- Implement the templates as string templates with `{{variable}}` substitution. The system prompt is static per type; the user prompt has variable blocks.
- Do NOT modify the prompt language from the spec without testing. The analytical mandates, anti-noise rules, and output schemas have been carefully designed. If you think something should change, run the change through a test cycle first.
- The output schema JSON in each template should be indented and readable. Opus is sensitive to output format instructions — a clear schema produces cleaner JSON output.
- Token budget monitoring: after each API call, log input_tokens and output_tokens. Compare against the estimates in Synthesis Prompt Templates v1 Section 6.2. If actual usage significantly exceeds estimates, the snapshot or signal context may be too large.
- Template D (Escalation) is on-demand only. It does not run on schedule. It is triggered by: an intelligence item reaching critical severity, a manual request from the user, or a cluster of related items crossing an attention threshold. Implement the trigger mechanism as a separate API endpoint: POST /api/synthesis/escalation with item_id.

**Acceptance Criteria:**
- ✓ All four templates produce valid Opus API calls that return structured JSON
- ✓ Template variable resolver correctly populates all `{{variable}}` blocks from the database
- ✓ Morning cycle produces cycle_summary and overall_health that reflect the actual signal content
- ✓ Midday cycle references the morning cycle summary and focuses on delta
- ✓ EOD cycle consolidates and evaluates all active items (every item appears in output)
- ✓ Escalation review produces actionable assessment with evidence chain
- ✓ Token usage logged and within expected ranges

---

### CC-3.3: Intelligence Item CRUD & Evidence Chain

**Goal:** Implement the logic that processes the synthesis cycle's output and creates, updates, reinforces, downgrades, resolves, merges, and archives intelligence items in the database. Each intelligence item maintains a linked evidence chain back to its source signals.

**Inputs:**
- SynthesisEngine from CC-3.1
- Prompt template output schemas from CC-3.2
- intelligence_items and intelligence_item_evidence tables from CC-1.1
- Intelligence Layer System Design v1, Section 10 (intelligence item lifecycle)

**Expected Outputs:**
- `ItemManager` class with methods for each action type: `create_item(synthesis_output)`, `update_item(item_id, synthesis_output)`, `reinforce_item(item_id, new_evidence)`, `downgrade_item(item_id, reason)`, `resolve_item(item_id, reason)`, `merge_items(surviving_id, source_ids, merged_output)`, `archive_item(item_id, reason)`
- Evidence chain management: when an intelligence item is created or updated, the source_signals from the synthesis output are written to intelligence_item_evidence with appropriate evidence_weight (primary, supporting, circumstantial)
- Merge logic: when EOD synthesis merges related items, the surviving item inherits the evidence chains of the merged items. Merged source items are archived with a note linking to the surviving item.
- Status transitions enforced: active → watch → archived (downgrade path), active → resolved (resolution), any → archived (manual or decay). No backward transitions (archived items cannot become active again — a new item must be created).
- Last_reinforced_at updates: when an item receives reinforcement (new evidence in the same direction), update last_reinforced_at. This timestamp drives decay detection.
- source_evidence_count maintained as a denormalized count on the intelligence item (COUNT of intelligence_item_evidence rows for this item). Updated on every evidence chain modification.

**Agent Implementation Notes:**
- The ItemManager is called by the synthesis engine after parsing the Opus response. The synthesis output contains an intelligence_items array where each entry has an "action" field. The ItemManager dispatches to the appropriate method based on the action.
- For "update" and "reinforce" actions, the synthesis output includes an existing_item_id. Validate that this ID exists and belongs to the same project. If it doesn't exist, log a warning and skip (don't crash).
- For "merge" actions (EOD only), the output includes merge_source_ids. Archive all source items and transfer their evidence chains to the surviving item.
- The confidence and severity on intelligence items come from the synthesis output, not from the source signals. Opus makes the judgment call about how confident it is in the item and how severe the operational impact is.

**Acceptance Criteria:**
- ✓ Create action produces a new intelligence item with evidence chain in the database
- ✓ Update action modifies an existing item and adds new evidence
- ✓ Reinforce action updates last_reinforced_at and increments evidence count
- ✓ Merge action archives source items and consolidates evidence into surviving item
- ✓ Resolve and archive actions set appropriate timestamps and status
- ✓ Invalid item_id references logged as warnings, not errors
- ✓ source_evidence_count matches actual evidence chain length

---

### CC-3.4: Working Memory Lifecycle Manager

**Goal:** Implement the decay and lifecycle rules that keep the intelligence working memory clean. Items that receive no reinforcement degrade over time. Items that are reinforced persist. This prevents stale intelligence from accumulating.

**Inputs:**
- ItemManager from CC-3.3
- working_memory_state table from CC-1.1
- Intelligence Layer System Design v1, Sections 7 (signal decay) and 14 (working memory management)

**Expected Outputs:**
- Signal decay computation: at each synthesis cycle, compute effective_weight for active signals based on their decay_profile and age. fast_24h: halves every 24 hours, medium_72h: halves every 72 hours, slow_7d: halves every 7 days, persistent: no decay. Signals with effective_weight below 0.1 are auto-archived.
- Intelligence item lifecycle rules: items with no reinforcement (no update to last_reinforced_at) for 6+ synthesis cycles downgrade from active to watch. Items in watch status with no reinforcement for 15+ cycles auto-archive.
- EOD synthesis produces working_memory_actions that explicitly downgrade, resolve, or archive items. The lifecycle manager also runs an automatic pass after synthesis to catch items the model missed.
- Working memory state snapshot: at the end of each synthesis cycle, write a snapshot to working_memory_state: active_item_count, watch_item_count, total_signal_count_today, tomorrow_watch_list (from EOD synthesis), health_trend.
- Cleanup: signals older than 30 days and in archived status can be soft-deleted (set a purge_after flag). Intelligence items are retained indefinitely for historical reference.

**Agent Implementation Notes:**
- The lifecycle manager runs as a post-synthesis step. After the synthesis engine processes the Opus response and the ItemManager writes items, the lifecycle manager sweeps for: (1) signals past their decay threshold, (2) items past the no-reinforcement downgrade threshold, (3) items past the auto-archive threshold.
- The "6+ cycles" and "15+ cycles" thresholds are configurable. With 3 cycles per day, 6 cycles = 2 business days, 15 cycles = 5 business days. These are the defaults from the System Design spec.
- The working memory state snapshot is consumed by the morning briefing template as context. It tells the synthesis engine: "yesterday we had 4 active items, 2 watch items, and the overall trend was declining."
- Signal decay should be computed lazily (at query time or at synthesis cycle start), not as a cron job. When the synthesis engine queries signals for a project, it computes effective_weight on the fly based on current time and the signal's decay_profile and created_at.

**Acceptance Criteria:**
- ✓ Signal effective_weight decreases correctly over time per decay profile
- ✓ Signals below 0.1 effective_weight are archived
- ✓ Intelligence items with no reinforcement for 6+ cycles downgrade to watch
- ✓ Watch items with no reinforcement for 15+ cycles auto-archive
- ✓ Working memory state snapshot written after each synthesis cycle
- ✓ Lifecycle manager does not re-downgrade items that synthesis explicitly maintained

---

### CC-3.5: Synthesis Validation Gate

**Goal:** Test the synthesis cycle against hand-crafted signal sets representing real construction scenarios. This is the quality gate: if the outputs feel generic, the prompt templates need rework before proceeding to the UI phase. **Do not move to Phase 4 until this gate passes.**

**Inputs:**
- Complete synthesis engine from CC-3.1–3.4
- Synthesis Prompt Templates v1 Section 6.3 (recommended test scenarios)
- Real Procore sandbox data

**Expected Outputs:**
- At least 5 test scenarios executed, drawn from real construction PM experience: (1) Mechanical rough-in falling behind while sub promises it's on track (contradiction: daily log manpower vs email assurances), (2) Multiple RFIs from different trades converging on the same coordination issue (convergence detection), (3) Submittal rejection followed by resubmission with no revision (pattern/decay detection), (4) Same subcontractor showing late response patterns across two projects (cross-project, if multiple sandbox projects exist), (5) A quiet day with no material changes (validates empty cycle produces "no material changes" output, not fabricated concerns)
- For each scenario: populate the signals table with realistic test data, trigger a manual synthesis cycle, capture the full Opus response, evaluate against quality criteria
- Quality criteria per Synthesis Prompt Templates v1 Section 6.4: Does the output distinguish between what the data shows and what is inferred? Does it produce actionable items a real PM would act on? Does it stay silent when there's nothing material? Does it avoid generic language like "continue to monitor"?
- Document the results: for each scenario, record the input signals, the synthesis output, and a pass/fail assessment with notes
- If any scenario fails quality criteria, iterate on the relevant prompt template and re-test before proceeding

**Agent Implementation Notes:**
- This is a human-judgment gate. The agent runs the tests and produces the outputs, but the quality evaluation requires construction domain expertise. The test results should be documented clearly enough that you (Moby) can evaluate them.
- Populate test data using direct SQL inserts or a test data script. Don't rely solely on live webhook data for testing — you need controlled scenarios.
- The "quiet day" scenario is as important as the others. If the system fabricates concerns when nothing is happening, trust is destroyed on day one.
- Run each scenario through at least the morning template. If time permits, run the full day: morning → midday (add new signals) → EOD (consolidate). This validates the cross-cycle continuity.

**Acceptance Criteria:**
- ✓ 5+ test scenarios executed with documented results
- ✓ Each scenario produces intelligence items that pass the 4 quality criteria
- ✓ The quiet-day scenario produces an empty or minimal output (not fabricated concerns)
- ✓ At least one scenario demonstrates contradiction detection by Opus
- ✓ At least one scenario demonstrates convergence detection
- ✓ Results documented in a format reviewable by the founder

---

## Phase 4: Command Center UI

Replace the placeholder panels from Phase 1 with real intelligence-driven UI components. Every element on the Command Center represents the system's judgment, not raw data. After this phase, the Command Center is functional and demonstrable.

---

### CC-4.1: Project Health Cards

**Goal:** Build the multi-project dashboard landing page with health cards for each active project. Each card displays the system's intelligence-derived health assessment, not raw metrics.

**Inputs:**
- Frontend scaffold from CC-1.5
- Dashboard overview API from CC-1.3
- Synthesis cycle output (cycle_summary, overall_health) from Phase 3
- Command Center & Radar Feature Spec v1, Section 2.3 (Project Health Cards)

**Expected Outputs:**
- Grid of project health cards on the dashboard landing page
- Each card shows: project name and number, status indicator (green/yellow/red dot derived from overall_health in the most recent synthesis cycle), 1–2 sentence plain-language summary (cycle_summary from synthesis), count of active intelligence items by severity (critical count in red, high in amber, medium in default), confidence indicator based on data completeness (how fresh is the data, how many data sources are active), last synthesis cycle timestamp
- Cards are clickable → navigate to the project detail view
- Cards are sorted by: projects with critical items first, then by overall_health (red → yellow → green), then alphabetically
- Empty state: if no synthesis cycles have run yet, cards show project name with "Awaiting first analysis" message and a neutral gray indicator

**Agent Implementation Notes:**
- The health card summary comes directly from the synthesis cycle output. Do NOT compute health from raw data on the frontend. The synthesis cycle's judgment IS the health assessment.
- The confidence indicator is a subtle but important trust signal. Show something like "High confidence — 5 data sources active" or "Limited data — daily logs not yet synced." This sets expectations when the data is thin.
- Use the SteelSync color palette for severity: critical = #DC2626 (red), high = #F59E0B (amber), medium = #3B82F6 (blue), low = #6B7280 (gray). Green status = #10B981.
- The card should feel substantial, not like a tiny widget. Give it enough height to display the summary comfortably. White or very light background on the card body with the dark navy sidebar as contrast.

**Acceptance Criteria:**
- ✓ Project health cards render with real data from the synthesis cycle
- ✓ Health status indicators (green/yellow/red) match synthesis output
- ✓ Cards navigate to project detail on click
- ✓ Empty state displays correctly when no synthesis has run
- ✓ Sort order puts critical items first

---

### CC-4.2: Intelligence Feed Panel

**Goal:** Build the primary panel in the project detail view: a chronological feed of intelligence items for the selected project. This is the most important UI component — it's where the PX sees the system's analytical output.

**Inputs:**
- Frontend scaffold from CC-1.5 (project detail layout)
- Intelligence items API from CC-1.3
- Intelligence item taxonomy from System Design v1 Section 9

**Expected Outputs:**
- Chronological feed of intelligence items for the selected project, most recent first
- Each item displays: item_type badge with icon (Convergence, Contradiction, Pattern Match, Decay Detection, Emerging Risk, Watch Item, Cross-Project), title, summary (2–4 sentences from synthesis), severity badge (Critical/High/Medium/Low with color), confidence indicator (numerical + visual bar), recommended_attention_level, source evidence count with expandable evidence chain (click to see linked signals with their summaries and source types), timestamp (first_created_at) and trend indicator (reinforced N times, last updated X hours ago)
- Filtering: by item_type (checkboxes), by severity (checkboxes), by status (active/watch/resolved). Default: active + watch, all types, all severities.
- Each item_type has a distinct visual treatment: Contradiction items have a warning/conflict icon, Convergence items show a merge/cluster icon, Pattern Match shows a trend icon, etc.
- Expandable evidence chain: clicking the evidence count reveals the linked signals in a dropdown. Each signal shows: signal_type, summary, source_type (Procore webhook / document pipeline / Radar), created_at, confidence.

**Agent Implementation Notes:**
- The Intelligence Feed is the product's primary value delivery surface. Every pixel here matters. The items should feel like intelligence briefings, not database records.
- Use distinct colors/icons for each item_type so the PX can scan quickly. Contradictions should visually pop (they're the most actionable). Watch items should be visually subdued (they're background awareness).
- The summary text is Opus-generated. It should render as clean, readable prose — not truncated or crammed. Give it room.
- The evidence chain expandable is a critical trust feature. Users need to see WHY the system flagged something. The evidence chain answers: "What data did you see that led to this conclusion?"
- Consider a subtle animation or highlight when new items appear (after a synthesis cycle runs). This reinforces the "live intelligence" feel.

**Acceptance Criteria:**
- ✓ Intelligence items render with all specified fields
- ✓ Filtering by type, severity, and status works correctly
- ✓ Evidence chain expands to show linked signals
- ✓ Item types have distinct visual treatments
- ✓ Empty state: "No intelligence items yet. First analysis will run at [next scheduled time]."

---

### CC-4.3: RFI/Submittal Tracker with Intelligence Overlay

**Goal:** Build the RFI and Submittal tracking panel that overlays intelligence context on top of raw Procore data. This module demonstrates the "intelligence layer above existing tools" positioning.

**Inputs:**
- Data API endpoints from CC-1.2 (RFIs, submittals with aging)
- Intelligence items API from CC-1.3
- Command Center & Radar Feature Spec v1, Section 2.3 (RFI & Submittal Tracker)

**Expected Outputs:**
- Table of open RFIs with columns: RFI number, title/subject, assignee, status, days open, aging indicator (color-coded: green = normal, yellow = 1.5x average, red = 2x average), linked intelligence badge (if a related intelligence item exists)
- Table of open submittals with same column structure adapted for submittal workflow
- Aging indicators computed against historical averages from the database (average days to close for RFIs, average turnaround for submittals). If insufficient historical data, use configurable defaults (RFI: 14 days normal / 21 yellow / 28 red; submittal: 10/15/20)
- Intelligence overlay: if an intelligence item references the same entity (RFI number, submittal, or related subcontractor/trade), show a linked badge on the row. Clicking the badge navigates to the intelligence item in the Intelligence Feed.
- Sortable columns. Default sort: aging indicator (red first), then days open descending.

**Agent Implementation Notes:**
- The intelligence overlay is what differentiates this from Procore's native RFI/submittal tracking. Procore shows you the RFI is overdue. SteelSync shows you the RFI is overdue AND there's a contradiction between the architect's email promise and the actual status AND this is part of a pattern with this architect across two projects.
- Aging averages should be computed from the actual database historical data if available. For the sandbox, you may need to use the configurable defaults.
- The intelligence link between an RFI row and an intelligence item is based on entity matching: if the intelligence item's source signals include a signal with entity_type = "rfi" and entity_value = the RFI number, they're linked.
- Keep the table clean and scannable. PMs are used to spreadsheet-style data. Don't over-design this — make it functional and fast.

**Acceptance Criteria:**
- ✓ RFI table renders with real data and correct aging colors
- ✓ Submittal table renders with real data
- ✓ Aging indicators match historical average calculations
- ✓ Intelligence overlay badges appear on rows with related intelligence items
- ✓ Clicking a badge navigates to the corresponding intelligence item
- ✓ Sort by aging indicator works correctly

---

### CC-4.4: Synthesis Cycle Status & Manual Trigger

**Goal:** Add a visible indicator of the synthesis cycle's status and a manual trigger button for testing and demonstration purposes. This gives the user visibility into when the system last ran and the ability to force a refresh.

**Inputs:**
- Synthesis engine from CC-3.1
- Synthesis cycle API from CC-1.3
- Frontend from CC-4.1

**Expected Outputs:**
- Status bar or indicator showing: last synthesis cycle time, cycle type (morning/midday/EOD), next scheduled cycle time, signals processed in last cycle, items created/updated
- Manual trigger button: "Run Analysis Now" with a loading state that shows progress
- After manual trigger completes: auto-refresh the Intelligence Feed, Project Health Cards, and any other panels that consume synthesis output
- If a synthesis cycle is already running, disable the trigger button and show "Analysis in progress..."

**Agent Implementation Notes:**
- This is a development and demo tool. In production, manual triggers may be restricted to admin users. For the prototype, make it accessible to any logged-in user.
- The loading state should show meaningful progress: "Querying signals..." → "Running analysis..." → "Processing results..." → "Complete." Even if these are approximate, they communicate that something is happening.
- Auto-refresh after synthesis is important for the demo flow: trigger analysis → watch the Command Center update in real time.

**Acceptance Criteria:**
- ✓ Status indicator shows correct last cycle time and type
- ✓ Manual trigger button fires synthesis and shows loading state
- ✓ Dashboard refreshes automatically after synthesis completes
- ✓ Concurrent trigger attempts are blocked with appropriate message

---

## Phase 5: Radar

Build the Radar: SteelSync's flagship feature for priority-driven monitoring. The Radar formalizes the PM's mental list of 2–5 critical concerns and applies continuous, automated surveillance. This phase builds the schema, UI, and monitoring pipeline. The Radar track can begin in parallel with Phase 3 for backend work (CC-5.1), but UI (CC-5.2–5.3) depends on the frontend scaffold, and monitoring (CC-5.4–5.6) depends on the signal pipeline.

---

### CC-5.1: Radar Schema & API Endpoints

**Goal:** Create the database tables and REST API endpoints for the Radar feature. This is the data foundation for Radar items, activity logs, watchers, and document links.

**Inputs:**
- Intelligence layer schema from CC-1.1
- Command Center & Radar Feature Spec v1, Sections 3.2 and 4.2 (Radar item structure, database schema additions)

**Expected Outputs:**
- `radar_items` table: id (UUID PK), project_id (FK), title (varchar), description (text), priority (enum: critical, high, watch), status (enum: active, resolved, archived), created_by (FK to users), monitoring_scope_json (JSONB — trades, entities, keywords to monitor), primary_target (text — the core thing being tracked), created_at, updated_at, resolved_at, archived_at
- `radar_watchers` table: id (UUID PK), radar_item_id (FK), user_id (FK), added_at, notification_preference (enum: all, critical_only, daily_digest)
- `radar_activity` table: id (UUID PK), radar_item_id (FK), activity_type (enum: system_detection, user_annotation, status_change, relevance_match), content (text), source_signal_id (FK nullable), source_document_id (FK nullable), severity (enum: low, medium, high), created_at, created_by (null for system entries)
- `radar_document_links` table: id (UUID PK), radar_item_id (FK), document_type (varchar — rfi, submittal, daily_log, etc.), document_id (UUID), relevance_score (decimal), linked_at, linked_by (enum: system, user)
- CRUD API endpoints: POST /api/radar/items (create), GET /api/radar/items (list, filterable by project_id, status, priority), GET /api/radar/items/:id (detail with activity log and document links), PATCH /api/radar/items/:id (update status, priority, description), POST /api/radar/items/:id/activity (add user annotation), POST /api/radar/items/:id/watchers (add watcher), DELETE /api/radar/items/:id/watchers/:user_id (remove watcher)

**Agent Implementation Notes:**
- The monitoring_scope_json field is critical for the monitoring pipeline (CC-5.4). It contains the structured criteria that the system evaluates incoming data against: which trades, entities, keywords, and document types are relevant to this Radar item. The intake form (CC-5.2) populates this.
- The primary_target field is the plain-language description of what's being tracked. It's used for embedding and semantic similarity matching.
- radar_activity is the Radar's timeline. Both system-generated entries (auto-detected updates) and user annotations live here. Sort by created_at DESC for display.
- Index radar_items on (project_id, status) and (status, priority) for fast queries. Index radar_activity on (radar_item_id, created_at) for timeline display.

**Acceptance Criteria:**
- ✓ All four tables created with appropriate indexes
- ✓ CRUD endpoints return valid JSON for all operations
- ✓ Creating a Radar item with watchers works in a single flow
- ✓ Activity log retrieval is sorted correctly (newest first)
- ✓ Filtering by project, status, and priority works

---

### CC-5.2: Radar UI — Panel & Structured Intake Form

**Goal:** Build the Radar panel (the top-level Radar view showing all active items) and the structured intake form for creating new Radar items. The intake form is critical to product identity — it must feel like a formal tracking request, not a chatbot prompt.

**Inputs:**
- Radar API endpoints from CC-5.1
- Frontend scaffold from CC-1.5 (Radar tab in navigation)
- Command Center & Radar Feature Spec v1, Section 3 (Radar concept and structure)

**Expected Outputs:**
- Radar Panel: list of all active Radar items across all projects. Each item shows: title, project(s), priority badge (Critical = red, High = amber, Watch = blue/gray), status, last activity timestamp, activity count
- Filterable by project, priority, and status
- Sortable by priority (Critical first), last activity, and creation date
- Structured Intake Form: modal or dedicated page for creating a new Radar item. Fields: Title (required, text), Project (required, dropdown from active projects), Priority (required, radio: Critical / High / Watch), Description (required, textarea — what is the concern and what should the system monitor for), Primary Target (required, text — the specific thing being tracked, e.g., "Mechanical rough-in schedule"), Monitoring Scope: Trades (multi-select from project's active trades), Monitoring Scope: Key Entities (text input, comma-separated — subcontractors, vendors, consultants), Monitoring Scope: Keywords (text input, comma-separated — terms to watch for in incoming documents), Watchers (multi-select from project users)
- Priority guidance text on the form: Critical = "Schedule or cost impact if this issue progresses. Immediate notifications." High = "Requires active tracking. Daily updates." Watch = "Background awareness. Weekly summary."

**Agent Implementation Notes:**
- The intake form is critical to product identity. It should feel like filling out a formal tracking request, not typing into a chatbot. Clean fields, clear labels, professional layout.
- The monitoring_scope fields populate the monitoring_scope_json in the database. The monitoring pipeline (CC-5.4) reads this to determine what to match against.
- The Primary Target field gets embedded for semantic similarity matching. Make it clear to the user that this should describe the THING being tracked, not the action they want.
- Auto-populate the Trades multi-select from the selected project's active trades (from the database). This saves the user from typing trade names.
- After creation, the new Radar item should appear immediately in the Radar Panel with its first activity log entry: "Radar item created by [user] at [timestamp]."

**Acceptance Criteria:**
- ✓ Radar Panel displays all active items with correct priority badges
- ✓ Filtering and sorting work correctly
- ✓ Intake form creates a Radar item with all fields populated in the database
- ✓ monitoring_scope_json is correctly structured from form inputs
- ✓ New item appears in the panel immediately after creation
- ✓ Priority guidance text is visible and helpful

---

### CC-5.3: Radar Detail View & Activity Log

**Goal:** Build the detail view for a single Radar item: the activity timeline, linked documents, and manual annotation capability.

**Inputs:**
- Radar API from CC-5.1
- Radar Panel from CC-5.2

**Expected Outputs:**
- Radar item detail page showing: full item metadata (title, project, priority, status, description, primary target, monitoring scope, created by, created at)
- Activity timeline: chronological log of all activity entries (system detections + user annotations). Each entry shows: activity type icon (system vs user), content, timestamp, severity badge if applicable, linked document (clickable to source)
- Linked documents section: list of all documents the system has connected to this Radar item via radar_document_links. Each shows: document type, title/number, relevance score, linked timestamp
- User annotation form: text input at the top of the activity log for adding manual notes. Posts to POST /api/radar/items/:id/activity with activity_type = user_annotation.
- Status controls: buttons to Resolve or Archive the Radar item, with confirmation dialog
- Show linked intelligence items: if the synthesis cycle has produced intelligence items that reference the same entities as this Radar item, display the connection. Cross-reference by entity overlap in signals.

**Agent Implementation Notes:**
- The activity timeline should look like a timeline — chronological entries with timestamps, each tagged as "System" or the user's name.
- System-detected entries should be visually distinct from user annotations (different icon, subtle background color difference).
- The linked intelligence items section is a cross-reference, not a data dependency. It queries intelligence_items for items whose source signals share entities with this Radar item's monitoring scope.
- Resolution should add a final activity log entry: "Radar item resolved by [user] at [timestamp]." and set the status.

**Acceptance Criteria:**
- ✓ Detail view displays all item metadata correctly
- ✓ Activity timeline shows entries in chronological order
- ✓ User annotations are added and appear immediately
- ✓ Linked documents section displays correctly
- ✓ Resolve/Archive actions update status with confirmation
- ✓ Linked intelligence items display if available

---

### CC-5.4: Radar Passive Monitoring Pipeline

**Goal:** Build the three-stage pipeline that evaluates incoming data against active Radar items at ingestion time. This is the Radar's passive monitoring mechanism. Stage 1 is metadata filtering (no LLM). Stage 2 is semantic similarity (embedding comparison). Stage 3 is Opus relevance judgment (LLM).

**Inputs:**
- Signal generation pipeline from Phase 2
- Radar items in database from CC-5.1
- Radar Pipeline Integration Specification v1 (pipeline architecture, model assignment, cost model)
- Existing embedding pipeline (nomic-embed-text-v1.5)
- Anthropic API (Opus) for Stage 3

**Expected Outputs:**
- **Stage 1 (Fast Filter):** when a new document or webhook event is ingested, compare its metadata (project_id, trade, entity names) against active Radar items' monitoring_scope_json. If no Radar item matches the project and has overlapping trade/entity scope, skip. This is a database query, not an LLM call. Goal: filter out 80%+ of items.
- **Stage 2 (Semantic Check):** for items passing Stage 1, generate an embedding of the document content and compare against the Radar item's primary_target embedding (pre-computed at Radar item creation). Cosine similarity threshold: configurable, default 0.6. Items below threshold are skipped. Goal: filter out another 50%+ of remaining items.
- **Stage 3 (Opus Judgment):** for items passing both filters, send the document content + Radar item context to Opus. Structured JSON response: relevant (boolean), relevance_summary (string), severity (low/medium/high). If relevant: create radar_activity entry, link document in radar_document_links, emit a radar_match signal to the signals table.
- Pipeline runs asynchronously — must not block the main ingestion pipeline. Hooks into the same async queue as signal generation.
- Pre-compute and store the embedding for each Radar item's primary_target + description at creation time. Store in a radar_embeddings column or separate table.
- Performance target: Stage 1 + Stage 2 combined < 500ms per document per Radar item.

**Agent Implementation Notes:**
- The three-stage pipeline minimizes Opus API costs. Most documents filter out at Stage 1 (metadata). The semantic check at Stage 2 catches most of the remainder. Only documents that pass both stages reach Opus. For a typical project with 5 Radar items and 50 daily documents, maybe 2–5 reach Stage 3 per day.
- The semantic similarity threshold should be conservative for the prototype (lower = more items reach Opus). Better to have Opus evaluate a few extra items than to miss a relevant match. Start at 0.6 and tune based on pilot data.
- The Stage 3 Opus prompt should be focused: "Given this Radar item [title, description, monitoring scope] and this incoming document [summary, entities, classification], is this document relevant to the Radar item? Respond with JSON: {relevant: boolean, relevance_summary: string, severity: low/medium/high}."
- The radar_match signal emitted to the signals table connects Radar monitoring to the synthesis cycle. The next synthesis cycle will see these signals and can incorporate Radar-related developments into intelligence items.

**Acceptance Criteria:**
- ✓ Stage 1 correctly filters documents not matching any Radar item's scope
- ✓ Stage 2 embedding comparison produces meaningful similarity scores
- ✓ Stage 3 Opus judgment correctly identifies relevant documents (test with a known-relevant document)
- ✓ Relevant matches create radar_activity entries and radar_document_links
- ✓ radar_match signals appear in the signals table
- ✓ Pipeline does not block the main ingestion flow
- ✓ Combined Stage 1 + Stage 2 latency < 500ms per item

---

### CC-5.5: Radar Active Analysis (Synthesis Cycle Embed)

**Goal:** Embed Radar active analysis into the existing periodic synthesis cycle rather than running it as a standalone pipeline. This is the key architectural decision from the Radar Pipeline Integration Specification: Radar evaluation benefits from the full synthesis context window and eliminates redundant Opus API calls.

**Inputs:**
- Synthesis engine from Phase 3
- Radar items in database from CC-5.1
- Radar Pipeline Integration Specification v1, Section 3 (architectural decision: embed in synthesis)

**Expected Outputs:**
- Extend the synthesis prompt templates to include a RADAR MONITORING MANDATE section when active Radar items exist for the project
- The Radar mandate section provides: list of active Radar items with title, description, priority, and monitoring scope; recent Radar activity (last 3 entries per item); instruction to Opus: "For each active Radar item, assess whether any of today's signals or intelligence items are relevant. If relevant, include a radar_update in your output."
- Extend the output schema with a `radar_updates` array: [{radar_item_id, relevance_summary, severity, recommended_status_change (optional), new_activity_entry}]
- Synthesis engine processes radar_updates: creates radar_activity entries, updates Radar item status if recommended, links relevant signals to the Radar item
- If no active Radar items exist for a project, the Radar mandate section is omitted from the prompt (saves tokens)

**Agent Implementation Notes:**
- This is the elegant solution to Radar active analysis. Instead of N additional Opus calls per day (one per Radar item), Radar evaluation is bundled into the 3 existing synthesis calls. Opus already has the full signal set and project context — it just also evaluates Radar items in the same pass.
- The Radar mandate section adds approximately 200–400 tokens per active Radar item to the synthesis prompt. For 5 items, that's ~1,000–2,000 tokens — modest relative to the total prompt size.
- Radar evaluation should NOT displace the core analytical mandate. It is an additional analytical task, not a replacement. The synthesis prompt structure should be: core analytical mandate first, then Radar mandate as a clearly separated section.
- Critical-priority Radar items get additional emphasis in the prompt: "Pay special attention to signals that may relate to Critical-priority Radar items. These represent the highest-priority tracking concerns."

**Acceptance Criteria:**
- ✓ Synthesis prompt includes Radar mandate when active Radar items exist
- ✓ Synthesis prompt excludes Radar mandate when no active items exist (verify token savings)
- ✓ Opus produces radar_updates in the output when relevant signals exist
- ✓ radar_activity entries are created from synthesis output
- ✓ Core intelligence item quality is not degraded by the addition of Radar mandate (compare outputs with and without)

---

### CC-5.6: Radar Signal Emission & Intelligence Link

**Goal:** Connect the Radar to the intelligence cycle by ensuring Radar matches emit signals and Radar-related intelligence items are cross-referenced. This closes the loop between Radar monitoring and the broader intelligence output.

**Inputs:**
- Radar passive monitoring from CC-5.4
- Radar active analysis from CC-5.5
- Signal generation infrastructure from Phase 2

**Expected Outputs:**
- Radar passive monitoring (Stage 3 match) emits a signal with signal_category = radar_match, including: radar_item_id in supporting_context_json, the matched document reference, relevance_summary from Opus judgment
- Radar active analysis (synthesis output) radar_updates are linked to the synthesis cycle's intelligence items via evidence chains
- Intelligence items that share entities with active Radar items display a "Radar-linked" badge in the Intelligence Feed (CC-4.2)
- On the Radar detail view (CC-5.3), show linked intelligence items that reference overlapping entities
- When a Radar item is resolved, any active intelligence items that were primarily driven by Radar-match signals should be evaluated for continued relevance (flagged for next synthesis cycle)

**Agent Implementation Notes:**
- The radar_match signal connects passive monitoring to synthesis. The next synthesis cycle sees these signals and can incorporate them into intelligence items alongside other signals.
- The bi-directional link (Radar → Intelligence Feed and Intelligence Feed → Radar) is important for user experience. The PX should be able to navigate from a Radar item to related intelligence and vice versa.
- Entity matching for the cross-reference uses the same logic as the intelligence overlay in the RFI/Submittal tracker (CC-4.3): compare entity_type and entity_value in signal supporting_context against Radar item monitoring_scope.

**Acceptance Criteria:**
- ✓ Radar passive matches emit radar_match signals to the signals table
- ✓ Synthesis cycle consumes radar_match signals alongside other signals
- ✓ Intelligence Feed items show Radar-linked badge when applicable
- ✓ Radar detail view shows linked intelligence items
- ✓ Signal flow: Radar match → signal → synthesis → intelligence item is end-to-end functional

---

## Phase 6: Polish & Validation

Final integration, quality-of-life features, and end-to-end validation. This phase ensures the prototype is demonstrable, the intelligence output is trustworthy, and the system handles the full client onboarding lifecycle.

---

### CC-6.1: False Positive Management & User Feedback

**Goal:** Build the mechanism for users to provide feedback on intelligence items. This is how the system learns: when a user marks an item as a false positive or confirms it as useful, that signal feeds back into the synthesis cycle's context for future runs.

**Inputs:**
- Intelligence Feed from CC-4.2
- Intelligence Layer System Design v1, Section 15 (false positive management)

**Expected Outputs:**
- On each intelligence item in the Intelligence Feed: thumbs-up and thumbs-down buttons (or Confirm / Dismiss)
- Thumbs-up (Confirm): marks the item as user-validated. Adds a user_validated flag and timestamp. Increases the item's confidence in the next synthesis cycle's context.
- Thumbs-down (Dismiss as False Positive): opens a brief modal: "Why is this not relevant?" with options: Incorrect assessment, Already resolved, Not actionable, Other (free text). Stores feedback in a new intelligence_item_feedback table.
- Dismiss action sets the item's status to dismissed (new status value). Dismissed items are excluded from the active Intelligence Feed but remain queryable.
- Feedback is included in the next synthesis cycle's context as a "user_feedback" block: "The following items were dismissed by the user with the stated reasons. Avoid reproducing similar items unless new, strong evidence emerges."
- Simple feedback metrics visible to the admin: total items, confirmed %, dismissed %, no-action %. This is the system's accuracy tracking.

**Agent Implementation Notes:**
- Keep the feedback interaction fast and frictionless. One click to confirm, two clicks to dismiss (click + select reason). The user should never feel burdened by the feedback loop.
- The feedback-into-synthesis loop is subtle but powerful. Over time, the synthesis cycle learns what the PX cares about and what they dismiss. For the prototype, this is a simple context block. For production, it could become a fine-tuning signal.
- Do not make the feedback modal complex. 4 options + free text. The goal is data collection, not user surveys.
- intelligence_item_feedback table: id, intelligence_item_id, user_id, feedback_type (confirmed, dismissed), dismiss_reason (enum + free text), created_at.

**Acceptance Criteria:**
- ✓ Confirm button marks item as user-validated
- ✓ Dismiss flow captures reason and sets status to dismissed
- ✓ Dismissed items disappear from the default Intelligence Feed view
- ✓ Feedback block appears in next synthesis cycle's prompt context
- ✓ Feedback metrics queryable (even if just via SQL for prototype)

---

### CC-6.2: Baseline Establishment Mode

**Goal:** Implement the three-phase client onboarding lifecycle from the Baseline Establishment Mode Specification. This ensures new clients experience a clean, professional onboarding rather than being flooded with stale intelligence from historical data.

**Inputs:**
- Baseline Establishment Mode Specification v1 (full specification)
- Synthesis engine from Phase 3
- Signal generation service from Phase 2
- Command Center UI from Phase 4
- Radar from Phase 5

**Expected Outputs:**
- `onboarding_phase` field on the clients table (enum: historical_ingest, calibration, live). This is the kill-switch that controls signal generation and synthesis behavior.
- **Phase 1 (Historical Ingest) behavior:** signal generation service checks onboarding_phase before firing — skips entirely during historical_ingest. Synthesis cycle skips execution. Notifications suppressed. Radar intake form disabled with note: "Radar monitoring available after project sync completes." Command Center shows onboarding progress view: project sync status (progress bars per project), entity discovery count, estimated go-live date.
- **Phase 2 (Calibration) behavior:** signal generation fires normally (with calibration_signal = true flag). Synthesis cycle runs with a CALIBRATION CONTEXT block in the prompt that suppresses Category E (Actor Pattern) and Category G (Cross-Project) signals — not enough data yet for reliable pattern detection. Command Center shows live intelligence with a "Calibrating" badge on Project Health Cards and Intelligence Feed. Notifications remain suppressed.
- **Phase 3 (Live Operations) behavior:** all systems normal. Full synthesis, full notifications, full Radar. The transition is triggered by: (1) minimum 5 business days of calibration synthesis, (2) entity norms computed, (3) founder/admin approval (manual endpoint), (4) healthy data pipeline, (5) at least 1 intelligence item per project in working memory.
- Admin endpoint: POST /api/admin/go-live with client_id. Validates exit criteria, transitions onboarding_phase to live. First notification after go-live is the next morning briefing.
- For M4 pilot: the admin endpoint can be a simple database update. The full exit criteria validation is ideal but a manual approval is acceptable for the first client.

**Agent Implementation Notes:**
- The onboarding_phase check must be added to: (1) the signal generation service (skip during Phase 1), (2) the synthesis engine (skip during Phase 1, add calibration context during Phase 2), (3) the notification engine (suppress during Phases 1–2), (4) the Radar intake form (disable during Phase 1).
- The onboarding progress view is the client's first impression. It must communicate competence: "We're learning your projects" not "Nothing to see here." Even a simple progress bar per project with entity counts is better than a blank screen.
- The calibration prompt addition suppresses unreliable signal types, not all intelligence. The client sees real intelligence during calibration — just with a confidence badge noting the system is still learning.
- Decay clocks do not start counting until Phase 3. Items created during calibration enter live operations with decay_days = 0.

**Acceptance Criteria:**
- ✓ Signal generation skips during Phase 1 (historical_ingest)
- ✓ Synthesis cycle skips during Phase 1, runs with calibration context during Phase 2
- ✓ Onboarding progress view renders during Phase 1
- ✓ Calibrating badge displays on health cards and intelligence feed during Phase 2
- ✓ Admin go-live endpoint transitions to Phase 3
- ✓ Notifications activate after go-live transition
- ✓ Radar intake disabled during Phase 1, enabled during Phase 2

---

### CC-6.3: End-to-End Validation Scenario

**Goal:** Execute a full end-to-end test of the intelligence cycle: manually create conditions in the sandbox that should produce a meaningful intelligence item, run the full pipeline, and verify the result appears on the Command Center with source evidence.

**Inputs:**
- All previous tickets completed and functional
- Procore sandbox access
- Implementation Plan v2, Task 10 (E2E validation scenario description)

**Expected Outputs:**
- Scenario setup: create conditions in the Procore sandbox that should trigger a Contradiction intelligence item. Example: make an RFI overdue while creating a correspondence trail showing the architect promised a response by yesterday. This creates two conflicting signals: rfi_became_overdue + the email's implicit promise.
- Run the full pipeline: (1) Procore webhook fires for the overdue RFI → Path A signal generation → rfi_became_overdue signal, (2) Forward the correspondence email to the system → Path B document pipeline → classification → project match → signal generation → expected_turnaround_promised signal, (3) Trigger a synthesis cycle → Opus sees both signals → produces a Contradiction intelligence item, (4) Verify the Contradiction item appears on the Command Center Intelligence Feed with evidence from both the Procore data and the email.
- Secondary validations: (1) create a Radar item tracking the same issue, verify the Radar picks up the relevant activity, (2) dismiss the intelligence item as resolved, verify the feedback is captured, (3) run another synthesis cycle and verify the system doesn't recreate the resolved item
- Document the full E2E flow with screenshots and annotated results for demo purposes

**Agent Implementation Notes:**
- This is the "one demo that matters" scenario. If you can show a pilot client: "Here's an overdue RFI. Here's an email where the architect said it would be done yesterday. SteelSync connected these automatically and flagged the contradiction" — that's the moment they understand the product.
- Set up the scenario carefully. Make sure the data is realistic: use a real trade, a real-sounding entity name, a plausible timeline. The demo should feel like something from an actual project, not a contrived test.
- Capture the E2E flow as a documented walkthrough. This becomes demo material for the pilot pitch.
- If the Contradiction doesn't appear, debug the pipeline step by step: are the signals generated? Are they in the right project? Is the synthesis prompt receiving them? Is Opus identifying the conflict?

**Acceptance Criteria:**
- ✓ Both signals (overdue RFI + email turnaround promise) appear in the signals table
- ✓ Synthesis cycle produces a Contradiction intelligence item referencing both signals
- ✓ Intelligence item appears on the Command Center with expandable evidence chain
- ✓ Radar item picks up related activity
- ✓ Dismissal feedback is captured and reflected in next synthesis cycle
- ✓ E2E walkthrough documented with screenshots

---

### CC-6.4: Visual Polish & Brand Consistency

**Goal:** Final visual polish pass across all Command Center components. Ensure consistent branding, professional typography, appropriate spacing, and a polished feel that communicates "enterprise intelligence platform" to a construction executive audience.

**Inputs:**
- All UI components from Phases 1, 4, and 5
- SteelSync brand direction: professional, dark navy/steel blue, no generic Bootstrap feel
- Command Center & Radar Feature Spec v1, Section 4.3 (frontend technical requirements: branding, theming)

**Expected Outputs:**
- Consistent color palette across all components: navy primary, steel blue accents, severity colors as defined, appropriate contrast ratios
- Typography consistency: font sizes, weights, and spacing consistent across all panels, tables, cards, and forms
- Loading states for all data-dependent components: skeleton loaders or spinner with contextual message
- Error states: graceful error display when API calls fail (not blank screens or raw error messages)
- Empty states for all panels: helpful messages explaining why data is absent and when it will appear
- Responsive verification: all components functional at 1920x1080 and 1440x900. Sidebar collapses cleanly on smaller viewports.
- SteelSync logo/wordmark in the top bar (placeholder image is fine if no final logo exists)
- Keyboard navigation: tabs, enter, escape work as expected in forms and modals
- Print-friendly view for the Intelligence Feed (a PX may want to print a summary for a meeting)

**Agent Implementation Notes:**
- This is the "first impression" pass. A boomer construction executive will judge the product by how it looks in the first 10 seconds. It needs to feel like enterprise software, not a developer prototype.
- Key visual priorities: (1) the project health cards must look authoritative, (2) the Intelligence Feed must feel like a briefing document, (3) the Radar Panel must feel like a command-and-control tool.
- Remove any developer-facing UI: debug panels, raw JSON displays, console.log remnants. The prototype should be demo-ready.
- Consider subtle animations: cards fading in on load, smooth transitions between views, toast notifications when new intelligence items appear. These create a "live" feel.
- If time is limited, prioritize the dashboard landing page (health cards) and the Intelligence Feed. These are the two surfaces that will be shown in a demo.

**Acceptance Criteria:**
- ✓ Color palette consistent across all components
- ✓ No broken layouts at 1920x1080 and 1440x900
- ✓ All loading, error, and empty states are handled gracefully
- ✓ No developer-facing debug UI visible
- ✓ The dashboard is demo-ready: a construction executive can look at it and understand what they're seeing

---

## Key Notes for the Agent

**Consult the specifications.** This document incorporates the key requirements from each spec, but the full specifications contain additional context, edge cases, and design rationale. When a ticket references a spec section, read it.

**Test against real data.** The Procore sandbox has real project data. Use it. Don't mock data if real data is available. The synthesis cycle's value is only visible when it processes real-world signals.

**The synthesis prompt templates are production code.** They are carefully designed. Implement them as specified in CC-3.2 before making modifications. If the output quality isn't right, iterate on the prompts through test cycles (CC-3.5), don't redesign the architecture.

**Signal generation is infrastructure; synthesis is the product.** Phase 2 is plumbing. Phase 3 is where the product's value lives. Invest the time in Phase 3 quality.

**The Radar is a flagship feature.** Build it accordingly. It should feel like a command-and-control tool, not a secondary widget.
