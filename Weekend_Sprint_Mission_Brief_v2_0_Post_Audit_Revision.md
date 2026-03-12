# STEELSYNC

*AI-Powered Construction Intelligence Platform*

---

# WEEKEND SPRINT MISSION BRIEF

## Version 2.0 — Post-Audit Revision

### Command Center & Intelligence Layer
### End-to-End Proof of Concept

**Version 2.0 | March 2026**  
**CONFIDENTIAL — FOR INTERNAL USE ONLY**

---

## 1. Situation Report

This brief supersedes Weekend Sprint Mission Brief v1.0, which was written before the repo audit. The audit (REPO-AUDIT-001, March 11, 2026) revealed that the backend intelligence pipeline is substantially built. The sprint scope has been revised accordingly.

### 1.1 What Exists (Confirmed by Audit)

| Ticket | Description | Status | Location |
|---|---|---|---|
| CC-1.1 | Intelligence Layer Schema (6 tables, 19 indexes) | PARTIAL | Migration 018 exists; not applied to live DB |
| CC-1.2 | Data API — command-center-api service, 8 endpoints | COMPLETE | `services/command-center-api/main.py` (938 lines) |
| CC-1.3 | Intelligence Data API — signals, items, synthesis, trigger | PARTIAL | Two implementations; intelligence-engine has real trigger |
| CC-2.1 | Deterministic Signal Detectors (6 detector functions) | COMPLETE | `services/intelligence-engine/signal_generation.py` |
| CC-2.2 | Signal Generation Service Core (805 lines) | COMPLETE | `signal_generation.py`, configurable model param |
| CC-2.3 | Path A: Webhook → Signal Hook | NOT FOUND | No hook from webhook-receiver to signal generation |
| CC-2.5 | Reinforcement Candidate Pipeline | COMPLETE | Schema + writer + API + synthesis consumer |
| CC-3.1 | Synthesis Engine Core (1,548 lines) | COMPLETE | `services/intelligence-engine/synthesis_engine.py` |
| CC-3.2 | Prompt Template Implementation (4 templates) | COMPLETE | `synthesis_engine.py`; defaults to Sonnet, needs Opus |
| CC-3.3 | Intelligence Item CRUD & Evidence Chain | COMPLETE | `ItemManager` in `synthesis_engine.py` |
| CC-3.4 | Working Memory Lifecycle Manager | COMPLETE | Decay profiles + archival in `synthesis_engine.py` |
| CC-5.1 | Radar Schema & API Endpoints | COMPLETE | Migration 019 + `command_center_api.py` |
| CC-5.4 | Radar Passive Monitoring Pipeline | COMPLETE | `services/intelligence-engine/radar_monitor.py` |
| CC-5.5 | Radar Active Analysis (Synthesis Embed) | COMPLETE | `radar_monitor.py` + `synthesis_engine.py` |
| CC-5.6 | Radar Signal Emission & Intelligence Link | COMPLETE | `radar_monitor.py` |
| CC-6.1 | False Positive Management & User Feedback | COMPLETE | Migration 019 + feedback endpoints |
| CC-6.2 | Baseline Establishment Mode | COMPLETE | Onboarding phase checks in signal gen + synthesis |

### 1.2 What Does Not Exist (Confirmed by Audit)

| Ticket | Description | Status |
|---|---|---|
| CC-1.4 | Frontend Scaffold & Project List | STUB — Stock Vite scaffold, no real UI |
| CC-1.5 | Command Center Layout & Navigation | NOT FOUND |
| CC-4.1 | Project Health Cards | NOT FOUND |
| CC-4.2 | Intelligence Feed Panel | NOT FOUND |
| CC-4.3 | RFI/Submittal Tracker with Intelligence Overlay | NOT FOUND |
| CC-4.4 | Synthesis Cycle Status & Manual Trigger | NOT FOUND (backend exists) |
| CC-5.2 | Radar UI: Panel & Intake Form | NOT FOUND (backend exists) |
| CC-5.3 | Radar Detail View & Activity Log | NOT FOUND (backend exists) |
| CC-6.3 | End-to-End Validation Scenario | NOT FOUND |
| CC-6.4 | Visual Polish & Brand Consistency | NOT FOUND |

### 1.3 Blockers Identified by Audit

1. **Migrations 018–019 not applied.** Intelligence tables do not exist in the live database. Zero signals, zero intelligence items, zero synthesis cycles.
2. **New services cannot start.** `command-center-api` and `intelligence-engine` fail on Postgres hostname resolution. They cannot find the database container.
3. **Frontend not built.** The `command-center/` directory is a stock Vite scaffold with a counter button. No real UI.
4. **Webhook-to-signal hook missing.** CC-2.3 (Path A: webhook event triggers signal generation) was not found. The signal detectors exist but nothing calls them when a webhook arrives.
5. **Synthesis model defaults to Sonnet.** CC-3.2 prompt templates default to `claude-sonnet-4-20250514`. Must be changed to Opus for production synthesis quality.
6. **Duplicate API surfaces.** `command-center-api` (standalone) and `intelligence-engine` (integrated) both expose similar endpoints. Need to resolve which is canonical.
7. **OpenClaw image pull blocked.** `docker compose up` fails because the `openclaw` image cannot be pulled. OpenClaw should be removed from the production compose file — it is a development tool, not a production service.

---

## 2. Mission Objective

The backend intelligence pipeline is built. The weekend sprint has three objectives:

- **Objective 1 — Infrastructure:** Get the full stack running in a clean environment with all migrations applied, all services healthy, and signals generating from real Procore data.
- **Objective 2 — Frontend:** Build the Command Center UI that displays the intelligence output. This is the primary build work of the sprint.
- **Objective 3 — Validation:** Run an end-to-end test where Procore data flows through signal generation, synthesis produces intelligence items, and the Command Center displays them.

### 2.1 Success Criteria

The sprint is complete when:

- All Docker services start healthy (no restart loops, no DNS failures)
- Migrations 018–019 are applied and intelligence tables exist with indexes
- Signal generation fires against real Procore data and writes signals to the database
- At least one synthesis cycle completes (Opus) and produces intelligence items with evidence chains
- The Command Center loads in a browser with project health cards showing intelligence-driven status
- The Intelligence Feed displays real intelligence items with severity, confidence, and expandable evidence
- Radar panel is accessible with intake form and displays any tracked items
- A human observer can walk through the system and understand what they are seeing

---

## 3. Sprint Work Streams

The sprint has three work streams. Stream 1 must complete first. Streams 2 and 3 can overlap once Stream 1 is stable.

### 3.1 Stream 1: Infrastructure Stabilization

**Goal:** A healthy Docker stack with data in the database and services talking to each other.

This stream unblocks everything else. Nothing works until the infrastructure is solid.

| # | Task | Details |
|---|---|---|
| 1 | Remove OpenClaw from `docker-compose.yml` | OpenClaw is a development tool, not a production service. Its image pull failure blocks the entire compose stack. Comment out or remove the `openclaw` service definition. Verify: `docker compose config` shows no `openclaw` service. |
| 2 | Resolve service DNS / networking | `command-center-api` and `intelligence-engine` fail because they cannot resolve hostname `postgres`. Ensure both services are on the same Docker network as the postgres container. Verify `depends_on` and network configuration in `docker-compose.yml`. Verify: both services start without `socket.gaierror`. |
| 3 | Apply migrations 016–019 | Run all four migrations in order against the running Postgres instance. 016: `retrieval_status` column + backfill. 017: `document_relationships` table + backfill. 018: intelligence layer schema (6 tables, 19 indexes). 019: radar + feedback + onboarding phase. Verify: `psql \dt` shows `signals`, `intelligence_items`, `synthesis_cycles`, `radar_items`, etc. |
| 4 | Resolve duplicate API surfaces | Two services expose similar intelligence endpoints: standalone `command-center-api` and the integrated `intelligence-engine`. Recommended: `intelligence-engine` is the canonical runtime (it has the real synthesis trigger). The standalone `command-center-api` should be retired or converted to a proxy. Alternative: keep both if they serve different roles (read-only data API vs. intelligence execution). Document the decision. Verify: one clear API path for each endpoint. |
| 5 | Configure model parameters | Set `SYNTHESIS_MODEL` env var to `claude-opus-4-20250514` (currently defaults to Sonnet). Set `SIGNAL_LLM_MODEL` env var to `claude-haiku-4-5-20251001` for signal triage. Set `ANTHROPIC_API_KEY` in `.env`. Verify: env vars are read by `intelligence-engine` on startup. |
| 6 | Wire webhook-to-signal hook (CC-2.3) | The signal detectors exist but nothing triggers them when a webhook arrives. Add a call from the webhook receiver (after DB write) to the signal generation service. This can be an async HTTP call to the `intelligence-engine`, a shared function import, or a database trigger — whatever fits the existing architecture. Verify: simulate a Procore webhook event and confirm a signal row appears in the `signals` table. |
| 7 | Seed initial signals from existing data | Run the deterministic signal detectors as a sweep against all existing Procore data in the database. This populates the `signals` table with baseline signals from historical data so synthesis has something to work with. Verify: `SELECT COUNT(*) FROM signals` returns `> 0`. |
| 8 | Run first synthesis cycle | Trigger a synthesis cycle via the API endpoint or direct function call. Verify: `synthesis_cycles` table has a completed row with `signals_processed > 0` and `items_created > 0`. Verify: `intelligence_items` table has rows with real summaries, severity scores, and linked evidence. If synthesis fails, capture the full error log before proceeding. |

**Stream 1 acceptance:** `docker compose ps` shows all services healthy, signals exist in the database, at least one synthesis cycle has completed successfully.

### 3.2 Stream 2: Frontend Build

**Goal:** A working Command Center UI that displays the intelligence output from the backend.

This is the primary build work of the sprint. The backend is done; now it needs a face. All frontend tickets from the original Ticketized Build Breakdown apply. The V2 prototype (`command-center-v2.jsx`) in the repository is the approved design direction.

| Ticket | Description | Priority | Notes |
|---|---|---|---|
| CC-1.4 | Frontend Scaffold & Project List | CRITICAL | Replace stock Vite scaffold with real app. Dark theme, API integration. |
| CC-1.5 | Command Center Layout & Navigation | CRITICAL | React Router, sidebar, placeholder panels, Radar tab. |
| CC-4.1 | Project Health Cards | CRITICAL | Intelligence-driven status from real synthesis data. |
| CC-4.2 | Intelligence Feed Panel | CRITICAL | Severity badges, summaries, expandable evidence chains. |
| CC-4.3 | RFI/Submittal Tracker with Intelligence Overlay | HIGH | Real data with intelligence signals overlaid. |
| CC-4.4 | Synthesis Cycle Status & Manual Trigger | HIGH | Backend endpoint exists. Build the UI button + status display. |
| CC-5.2 | Radar UI: Panel & Intake Form | HIGH | Backend exists. Build the command-and-control UI. |
| CC-5.3 | Radar Detail View & Activity Log | MEDIUM | Backend detail endpoint exists. Build the detail view. |
| CC-6.4 | Visual Polish & Brand Consistency | HIGH | Enterprise feel. Demo-ready. No developer debug UI. |

The four **CRITICAL** tickets are the minimum viable frontend. If time runs short, cut CC-5.2, CC-5.3, and CC-6.4 — the Intelligence Feed and health cards are the demo.

*Design direction: dark navy (`#1B2A4A`) background, steel blue (`#3B6B8A`) accents, DM Sans typography. Match the V2 prototype aesthetic. The target audience is a boomer construction executive who will judge the product in the first 10 seconds.*

### 3.3 Stream 3: End-to-End Validation

**Goal:** Walk through the complete system and confirm it works as a product.

This stream runs after Streams 1 and 2 are complete. It is the definition of “done” for the sprint.

1. **Infrastructure:** `docker compose ps` shows all services healthy. No restart loops.
2. **Data layer:** Procore data in the database. `signals` table populated. `intelligence_items` exist from at least one completed synthesis cycle.
3. **Command Center load:** Open browser. Dashboard loads. Project health cards show real projects with intelligence-driven status.
4. **Intelligence Feed:** Click a project. Intelligence items appear with severity badges, confidence scores, summaries, and expandable evidence. The items reference real signals from real Procore data.
5. **Manual trigger:** Click the synthesis trigger button. A new cycle runs. New or updated intelligence items appear in the feed.
6. **Radar:** Navigate to Radar. Create a new Radar item. Verify it appears and the backend accepts it. (If Radar UI was cut for time, verify via `curl` against the API.)
7. **The gut check:** A construction PM looking at this output would find it useful, specific, and grounded in real project data. If the output feels generic or fabricated, the synthesis prompts need iteration before the sprint is done.

---

## 4. Model Strategy for Sprint

| Function | Production Model | Sprint Model | Reason |
|---|---|---|---|
| Signal triage | DeepSeek (local) | Claude Haiku | No local LLM in test env. |
| Synthesis cycle | Claude Opus | Claude Opus | No change. Opus is the product. |
| Deterministic signals | No LLM (code) | No LLM (code) | No change. |
| Radar judgment | Claude Opus | Claude Opus | No change. |

**Critical fix:** the `SYNTHESIS_MODEL` environment variable currently defaults to `claude-sonnet-4-20250514`. This must be changed to `claude-opus-4-20250514`. The synthesis cycle is the product's core analytical output. Opus-grade reasoning is non-negotiable.

---

## 5. Operating Rules

### 5.1 Pace

No artificial pacing. The dependency chain and acceptance criteria define what must happen. The Operations Team decides how fast. If Stream 1 clears in two hours, move to Stream 2 immediately.

### 5.2 Stream 1 Before Stream 2

Do not start the frontend build until the infrastructure is healthy and at least one synthesis cycle has completed. The frontend needs real data to build against — building against mock data when real data is available is wasted effort.

### 5.3 Blocker Escalation

Three-strike rule from the Production Protocol applies. If a task fails three times, declare BLOCKED and move on. The CEO will be available for real-time escalation during the sprint.

### 5.4 Real Data Only

The Procore sandbox has real project data. Use it. Do not create mock data unless a specific table is empty and you need it for testing. Mark seeded test data clearly.

### 5.5 Frontend Quality Bar

Enterprise software, not a developer prototype. Dark navy theme, professional typography, appropriate spacing. A construction executive judges the product in the first 10 seconds. Match the V2 prototype aesthetic (`command-center-v2.jsx`). Remove all developer debug UI.

### 5.6 Commit Discipline

Per the Version Control Protocol: commit after each task completion, at time checkpoints, and at every session end. Tag phase completions. Push to remote after every merge.

---

## 6. Reference Documents

- `AUDIT-REPORT.md` (REPO-AUDIT-001) — ground truth on current codebase state
- Command Center Ticketized Build Breakdown v1 — full ticket details for all frontend work
- Intelligence Layer System Design v1 — signal schema, intelligence items, synthesis cycle design
- Synthesis Prompt Templates v1 — production prompt templates for all four cycle types
- Signal Type Scoping Specification v1 + Addendum v1.1 — signal categories, review chain progress signals
- Review Chain Weight Reference v1 — industry-standard reviewer authority by CSI division (shared knowledge)
- Command Center Design Specification v1 — V2 prototype design direction
- Command Center & Radar Feature Specification v1 — dashboard modules, Radar structure
- Operations Code Production Protocol v1 — task execution rules
- Version Control Protocol v1 — commit discipline, merge rules

---

## 7. Document Control

| Field | Value |
|---|---|
| Document | Weekend Sprint Mission Brief |
| Version | 2.0 — Post-Audit Revision |
| Date | March 12, 2026 |
| Author | HQ (Claude Opus) — VP / CTO |
| Approved By | Moby — CEO |
| Classification | Internal — Founders Only |
| Status | Pending CEO Approval |
| Supersedes | Weekend Sprint Mission Brief v1.0 |
| Basis | REPO-AUDIT-001 findings (March 11, 2026) |
