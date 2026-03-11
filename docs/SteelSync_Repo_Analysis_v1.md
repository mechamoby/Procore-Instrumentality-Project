# STEELSYNC — Instrumentality Repository Analysis

**Comprehensive Code Review Against Product Specifications**

March 11, 2026 | CONFIDENTIAL — FOR INTERNAL USE ONLY

---

## Executive Summary

This analysis reviews the Procore-Instrumentality-Project repository against the full SteelSync specification library: the Business & Architecture Spec, Intelligence Layer System Design, Command Center Implementation Plan v2, Signal Type Scoping Spec, Document Pipeline Integration Point Spec, Model Strategy & Cost Analysis, Synthesis Prompt Templates, Agent Framework Orchestration Spec, and the Radar Pipeline Integration Spec.

The core finding is that the implementation is substantially further along than a typical early prototype. The intelligence pipeline — from Procore data sync through signal generation, synthesis, working memory lifecycle, and Radar monitoring — is architecturally complete and closely tracks the specifications. The Command Center API layer is comprehensive with 30+ endpoints. The database schema is applied and validated. Real Procore sandbox data is flowing.

The primary gaps are operational, not architectural: the Anthropic API key is not yet set (blocking Claude-powered synthesis), the Docker container is running stale code, visual polish is deferred, and the document pipeline integration exists in spec but not yet in the codebase for the full 8-stage pipeline. These are all tractable blockers that don't require rearchitecting anything.

---

## 1. Repository Structure & Organization

The repo spans approximately 2.9MB across several major directories. The core application code lives in `nerv-interface/` (the FastAPI server, Command Center API, synthesis engine, signal generation, Radar monitor, and static frontend). The EVA-00 sync agent and its design documents are in `eva-agent/`. Supporting infrastructure includes scripts, memory/session logs, protocol docs, business docs, and research.

### Key File Inventory

| Module | File | Lines | Role |
|--------|------|-------|------|
| Server | `nerv-interface/server.py` | 1,207 | FastAPI app, WebSocket bridge to OpenClaw gateway, activity feed |
| Command Center API | `nerv-interface/command_center_api.py` | 1,462 | 30+ REST endpoints for projects, RFIs, submittals, signals, intelligence, Radar, onboarding |
| Synthesis Engine | `nerv-interface/synthesis_engine.py` | 1,473 | Cycle orchestration, 4 prompt templates, ItemManager, decay lifecycle, working memory snapshots |
| Signal Generation | `nerv-interface/signal_generation.py` | 805 | SignalWriter, 6 deterministic detectors, LLM-based detection via Ollama, reinforcement candidates |
| Radar Monitor | `nerv-interface/radar_monitor.py` | 493 | 3-stage pipeline (metadata, keyword, judgment), synthesis mandate builder, radar_updates processing |
| EVA Sentry | `nerv-interface/eva_sentry.py` | 217 | Prompt injection + malware preflight scanner for document intake |
| DB Layer | `nerv-interface/steelsync_db.py` | 84 | psycopg2 connection pooling, serialization helpers |
| Command Center SPA | `nerv-interface/static/command-center.html` | 1,532 | Dark-theme SPA with dashboard, project detail, Radar views |
| Portal | `nerv-interface/static/portal.html` | 1,125 | Original NERV portal interface |
| Main Portal | `nerv-interface/static/index.html` | 4,126 | Full web interface with chat, terminal, file manager, document tabs |
| Sync Agent | `eva-agent/eva-00/src/sync_agent.py` | 800 | Continuous Procore polling: projects, RFIs, submittals, drawings, companies, contacts, docs |
| Procore Client | `eva-agent/eva-00/src/procore_client.py` | ~300 | OAuth token management, API wrappers, rate limit handling |
| Intelligence Schema | `eva-agent/eva-00-design/INTELLIGENCE-LAYER-SCHEMA.sql` | 337 | 9 tables, 15 enum types, 35 indexes for the intelligence layer |
| Base Schema | `eva-agent/eva-00-design/DATABASE-SCHEMA.sql` | 909 | Core 22-table schema for Procore data mirror |

Total production-relevant Python: approximately 6,500 lines across the nerv-interface modules. Including the sync agent, schemas, scripts, and frontend HTML, the working codebase is roughly 15,000–18,000 lines of implementation code.

---

## 2. Specification Alignment Audit

### 2.1 Intelligence Layer System Design v1

The Intelligence Layer spec defines the three-stage pipeline: ingestion-time micro-analysis (signals), periodic synthesis, and deep analysis on demand. It specifies signals as first-class objects with confidence, strength, effective_weight, decay profiles, and entity tracking. It defines intelligence items as the primary PM-facing output with status lifecycle (new → active → watch → downgraded → resolved → archived), evidence chains, and working memory state snapshots.

**Implementation status: Substantially complete.** The signals table, intelligence_items table, synthesis_cycles table, evidence_chain, working_memory_state, and reinforcement_candidates tables all exist in the schema and match the spec. The SignalWriter implements validation, dedup (same source_document_id + signal_type within 1 hour), category enforcement (synthesis-only categories blocked at ingestion), and source_multiplier application. Six deterministic detectors cover RFI overdue, submittal overdue, submittal rejected, high-value change orders, stalled RFIs, and daily log gaps. The synthesis engine implements all four cycle types (morning briefing, midday checkpoint, end-of-day, escalation review) with proper prompt templates. The decay lifecycle (`run_decay_cycle`) correctly implements exponential decay with half-lives per profile, archive threshold at 0.1, and the 7-day active→watch and 15-day watch→archive rules. Calibration-awareness is implemented (decay skips during historical_ingest and calibration phases).

### 2.2 Signal Type Scoping Specification v1

This spec assigns each signal category to a processing tier: Categories A (Status Change) and D partial (Document Significance, Timeline mechanical) to the local LLM; Categories B (Contradiction), C partial (Reinforcement evaluation), E (Actor Pattern), and F (Cross-Project) deferred to Opus synthesis.

**Implementation status: Correctly enforced.** The `SYNTHESIS_ONLY_CATEGORIES` set in `signal_generation.py` blocks contradiction, actor_pattern, and cross_project from ingestion-time writing. `ALLOWED_INGESTION_CATEGORIES` permits only status_change, reinforcement, timeline, document_significance, and radar_match. The reinforcement_candidates table is properly separate from signals. The LLM output contract from the spec (signals array, reinforcement_candidates array, no_signal_reason) is reflected in the Ollama integration's prompt template and response parser.

### 2.3 Command Center Implementation Plan v2

The 10-task, 4-phase plan defines the full build sequence from database audit through E2E validation.

| Task | Description | Status |
|------|-------------|--------|
| CC-1.1 | Intelligence Layer Schema (9 tables, 15 enums, 35 indexes) | ✅ DONE |
| CC-1.2 | Procore Data API Endpoints (projects, RFIs, submittals, logs, schedule, COs) | ✅ DONE |
| CC-1.3 | Intelligence Data API Endpoints (signals, items, synthesis, dashboard) | ✅ DONE |
| CC-1.4/1.5 | Command Center SPA Frontend Scaffold + Styling | ✅ DONE |
| CC-2.1 | Deterministic Signal Detectors (6 detectors) | ✅ DONE |
| CC-2.2 | LLM-Based Signal Generation (Ollama/DeepSeek integration) | ✅ DONE |
| CC-2.4 | Source Multiplier + PM Review Re-fire (refire_signals_for_document) | ✅ DONE |
| CC-3.1/3.2/3.3 | Synthesis Engine + Prompt Templates + ItemManager | ✅ DONE |
| CC-3.4 | Working Memory Lifecycle (decay, archive, health_trend) | ✅ DONE |
| CC-4.4 | Synthesis Trigger + Signal Sweep UI Controls | ✅ DONE |
| CC-5.1/5.2/5.3 | Radar Schema + CRUD API + UI (create/list/detail) | ✅ DONE |
| CC-5.4 | Radar Passive Monitoring Pipeline (3-stage) | ✅ DONE |
| CC-5.5 | Radar Synthesis Mandate Builder | ✅ DONE |
| CC-5.6 | Radar ↔ Intelligence Bidirectional Linking | ✅ DONE |
| CC-6.2 | Onboarding Phase Management + Go-Live Endpoint | ✅ DONE |
| CC-6.3 | E2E Validation Scenario | 🟡 PARTIAL |
| CC-6.4 | Visual Polish | 🟡 PARTIAL |

Of the 32 discrete tickets in the build breakdown, all backend systems are complete. The two remaining partial items are validation documentation (the backend works, but a documented test walkthrough doesn't exist yet) and visual polish (intentionally deferred).

### 2.4 Synthesis Prompt Templates v1

**Implementation status: Complete.** All four templates (Morning Briefing, Midday Checkpoint, End-of-Day Consolidation, Escalation Review) are implemented in `synthesis_engine.py` with the correct structural elements: system base prompt with analytical mandate, anti-noise rules, assumption-stating requirements, and structured JSON output schema. The morning template caps at 5 new items, midday at 3, EOD at 7 with merge support. The escalation template includes the escalation assessment sub-schema. Template variables (morning_summary, midday_summary, escalation_item, related_items, etc.) are properly parameterized.

### 2.5 Document Pipeline Integration Point Spec v1

**Implementation status: Hooks ready, pipeline not yet built.** The specification defines two ingestion paths: Path A (Procore webhooks → signal generation directly) and Path B (documents through the 8-stage pipeline). Path A is implemented — the sync agent writes to the database, and signal generation fires against the synced data. The `evaluate_document()` and `refire_signals_for_document()` methods in `signal_generation.py` implement the document pipeline hook points per sections 3.2 and 3.3 of the spec, including the source_multiplier for low-confidence project matches. However, the full 8-stage document pipeline itself (intake → security → normalize → extract → classify → match → route → store) is not yet built in this repo — it exists in the Document Pipeline MVP System Design as a future build. The signal generation hooks are ready and waiting for it.

### 2.6 Agent Framework Orchestration Spec v1

**Implementation status: Architecturally aligned.** The spec defines the OpenClaw agent framework as the operational backbone with Opus as the primary orchestrator. The `server.py` implementation reflects this: it connects to the OpenClaw gateway via WebSocket, maintains authenticated sessions, and bridges the NERV web interface to the agent's full toolset. The SOUL.md and AGENTS.md files define the agent's identity, memory protocol, and operational boundaries. The heartbeat system, session handoff protocol, and memory hierarchy (daily notes → MEMORY.md → project-specific memory) are all implemented as file-based state. The spec's description of Opus delegating to local LLM via tool calls matches the architecture where signal generation calls Ollama independently for high-volume structured tasks.

### 2.7 Radar Pipeline Integration Spec v1

**Implementation status: Complete with one placeholder.** The 3-stage passive monitoring pipeline (metadata filter → keyword/entity match → relevance judgment) is fully implemented in `radar_monitor.py`. Stage 1 checks project match, entity type overlap, trade match, and signal category against the Radar item's monitoring_scope_json. Stage 2 builds a keyword corpus from the Radar item's primary_target, title, description, and scope keywords, then scores against the signal's text corpus with partial stem matching. Stage 3 uses an algorithmic heuristic (keyword score × priority multiplier) as a placeholder for the Opus LLM judgment call. The `build_radar_mandate()` function correctly constructs the synthesis prompt injection per CC-5.5, including recent activity per Radar item. The `process_radar_updates()` function handles synthesis output's radar_updates array, creating activity entries and applying status changes (resolved, escalated). Flood protection is implemented: max 3 matches per Radar item per run, and signal_type dedup per item.

---

## 3. Architecture Assessment

### 3.1 What's Working Well

**Clean separation of concerns.** The codebase maintains a clear boundary between the sync layer (EVA-00), signal generation, synthesis, Radar monitoring, API endpoints, and the frontend. Each module has a single responsibility. The database is the integration point, not interprocess communication. This is the correct architecture for a system that needs to run reliably on dedicated hardware with minimal operational overhead.

**Spec fidelity is high.** The implementation doesn't just vaguely follow the specs — it implements them with precision. Enum types match exactly. Decay profiles use the specified half-lives. Signal categories are enforced at the service level as the Signal Type Scoping Spec requires. The synthesis prompt templates include the anti-noise rules, the assumption-stating mandate, and the structured JSON output contract. This level of spec adherence means the architecture documents remain valid references rather than becoming stale aspirational docs.

**The database schema is production-quality.** The intelligence layer schema (337 lines of SQL) defines 9 tables with proper foreign keys, CHECK constraints, enum types, GIN indexes on JSONB columns, partial indexes for common query patterns, and update triggers. The base schema adds another 909 lines covering the full Procore data mirror. This is not prototype-level schema work — it's designed for the query patterns the API actually uses.

**The local fallback synthesis is smart.** Rather than blocking entirely on the missing Anthropic API key, the codebase includes a local algorithmic synthesis engine that detects contradictions, convergences, pattern matches, and emerging risks using rule-based analysis of signal clusters. This means the full pipeline can be validated end-to-end without any external API dependency. Two synthesis cycles have already completed against real data, producing 12+ intelligence items.

**Signal dedup and lifecycle are well-engineered.** The 1-hour window dedup on source_document_id + signal_type prevents signal flooding from repeated webhook events. The context-merge behavior (when a new signal has additional context keys vs an existing duplicate) is a thoughtful touch that preserves information without creating noise. The effective_weight computation (confidence × strength × source_multiplier × decay_factor) gives the synthesis engine a single sortable metric.

### 3.2 Areas for Attention

**SQL injection surface in `find_by_procore_id`.** The `sync_agent.py` function uses an f-string for the table name: `f"SELECT id FROM {table} WHERE procore_id = %s"`. While the table parameter is always hardcoded by the caller (never from user input), this pattern is worth refactoring to use a whitelist check. In a codebase destined for on-premise deployment at construction firms, defense-in-depth matters.

**Single-connection sync agent.** The sync agent uses a single psycopg2 connection (`get_conn()`) rather than a connection pool. For the current prototype this is fine, but it means a transient connection failure during a sync pass will crash the agent. The nerv-interface modules correctly use ThreadedConnectionPool. The sync agent should be brought in line before pilot deployment.

**No retry logic on Procore API calls.** The sync agent has a simple try/except per entity type but no exponential backoff or retry on transient failures (rate limiting, network hiccups). The ProcoreClient handles token refresh, but the sync functions themselves don't distinguish between retryable and permanent failures.

**The Anthropic API call in `synthesis_engine.py` uses httpx directly.** There's no retry, no timeout configuration, and no streaming. For synthesis calls that may take 30–60 seconds with large context windows, this is a reliability gap. A timeout and at least one retry on 5xx errors should be added before the API key goes live.

**Radar Stage 3 is purely algorithmic.** The spec calls for Opus-grade LLM judgment at Stage 3 of the Radar pipeline. The current implementation uses a keyword_score × priority_multiplier heuristic. This is explicitly documented as a placeholder, and it's the right call for the prototype phase, but it will need upgrading for pilot — Radar accuracy is a direct trust metric per the spec.

**No automated test suite.** The handoff doc references "E2E tests passing" from the broader NERV stack, but this repo has no unit tests, no integration tests, and no CI pipeline. The `seed-test-signals.py` script serves as a manual validation tool but isn't a substitute for repeatable automated tests. Before pilot, at minimum the signal generation detectors and synthesis engine's item lifecycle should have test coverage.

---

## 4. Gap Analysis: What's Built vs. What's Specified

| Capability | Spec Source | Implementation | Gap |
|-----------|-------------|----------------|-----|
| Procore data sync (projects, RFIs, submittals, drawings, companies, contacts, docs) | Business & Architecture Spec | Complete — sync_agent.py covers all entity types with cursor-based polling | None |
| Signal generation (deterministic) | Intelligence Layer Design §4, Signal Scoping Spec | Complete — 6 detectors covering overdue, rejected, high-value, stalled, missing | Could add: schedule milestone, manpower deviation |
| Signal generation (LLM-based) | Intelligence Layer Design §4, Signal Scoping Spec | Complete — Ollama/DeepSeek integration with structured JSON contract | Blocked on Ollama availability; falls back to deterministic-only |
| Synthesis cycles (4 types) | Intelligence Layer Design §5, Synthesis Templates v1 | Complete — all 4 templates, ItemManager, evidence chains | Blocked on ANTHROPIC_API_KEY for Claude; local fallback works |
| Working memory lifecycle | Intelligence Layer Design §6 | Complete — decay sweep, archive thresholds, health_trend tracking, calibration-aware | None |
| Radar passive monitoring (3-stage) | Radar Pipeline Spec, CC-5.4/5.5/5.6 | Complete — metadata, keyword, algorithmic judgment; synthesis mandate; bidirectional linking | Stage 3 needs Opus upgrade for pilot |
| Radar structured intake form | CC & Radar Feature Spec | Complete — POST /api/radar/items with monitoring_scope_json | UI form exists in command-center.html |
| Command Center dashboard | CC Design Spec, CC Implementation Plan | Complete — project overview, RFI/submittal drill-down, intelligence items, Radar view | Visual polish deferred (CC-6.4) |
| Document pipeline (8-stage) | Document Pipeline MVP Design, Document Pipeline Integration Spec | Hooks ready (evaluate_document, refire_signals) but full pipeline not built | Major build item — intake/security/normalize/extract/classify/match/route/store |
| Baseline Establishment Mode | Baseline Establishment Mode Spec, CC-6.2 | Complete — onboarding_phase column, calibration-aware decay, go-live endpoint with exit criteria | None |
| Deep Dive on demand | Deep Dive Request Flow Spec | Escalation Review template exists; no dedicated request endpoint | Needs a POST /api/deep-dive trigger + queue |
| Email intake channel | Inbound Channel Design Spec | katsuragi-email.py exists as a standalone email poller; not integrated into intelligence pipeline | Needs routing into signal generation |
| Cross-project correlation | Intelligence Layer Design §4, Signal Scoping Spec | Schema supports it (cross_project signal category); no implementation yet | Deferred to multi-project deployment |
| Notification delivery | Inbound Channel Design Spec | Telegram bot (katsuragi) exists; no intelligence-triggered notifications | Needs synthesis → notification bridge |
| RBAC / user profiles | User Profiles Schema | Schema exists (USER-PROFILES-SCHEMA.sql); portal auth is functional | Not connected to Command Center role-based views |

---

## 5. Code Quality Observations

The codebase is clean, well-commented, and consistent in style. Module-level docstrings reference the specific spec sections they implement (e.g., "CC-3.1 + CC-3.2 + CC-3.3"). Function signatures use type hints. SQL queries use parameterized inputs throughout (with the one f-string exception noted above). Error handling is present at service boundaries. Logging is structured and uses appropriate severity levels.

The CLAUDE.md file is an excellent piece of developer documentation — it gives any new contributor (human or AI) a complete contextual onboarding in a single read. The SOUL.md, AGENTS.md, and memory hierarchy are well-designed for the agent framework's stateless session model.

The naming transition from Evangelion to SteelSync is partially complete. New code (`command_center_api.py`, `steelsync_db.py`, `signal_generation.py`) uses SteelSync naming. Legacy code (`server.py`, `sync_agent.py`, file paths) still uses NERV/EVA naming. This is expected per the CLAUDE.md convention: "New code uses SteelSync, modify existing code where practical."

One structural observation: the entire Command Center SPA is a single 1,532-line HTML file with inline CSS and JavaScript. This is appropriate for the prototype phase (fast iteration, no build tooling required), but will need to be componentized before the visual polish pass. The current file is maintainable but approaching the limit.

---

## 6. Risk Assessment for Pilot

| Risk | Severity | Mitigation Status | Action Needed |
|------|----------|-------------------|---------------|
| Anthropic API key not set — Claude synthesis blocked | **HIGH** | Local fallback validates pipeline | Set the key. This is the single highest-value unblock. |
| Docker container running stale code (March 9) | **MEDIUM** | Local dev server works on port 8888 | Rebuild and redeploy the nerv-interface container |
| No automated tests | **MEDIUM** | Manual validation scripts exist | Add pytest suite for signal detectors + synthesis lifecycle |
| Radar Stage 3 is heuristic-only | **MEDIUM** | Algorithmic judgment is functional | Upgrade to Opus API call; this is a trust metric |
| Document pipeline not built | LOW (for PoC) | Procore webhook path covers primary data flow | Build after PoC validates core intelligence value |
| No retry/timeout on Anthropic API calls | **MEDIUM** | Not yet relevant (key not set) | Add before key goes live: 60s timeout, 1 retry on 5xx |
| Single-threaded sync agent | LOW | Works for sandbox data volumes | Add connection pool + retry logic before pilot |
| Email intake not integrated | LOW (for PoC) | Standalone poller exists | Wire katsuragi output into signal generation |

---

## 7. Recommended Next Steps

Ordered by impact and dependency:

### Immediate (This Week)

**1. Set the Anthropic API key.** This is the single highest-ROI action. It unlocks Claude-powered synthesis against the 324+ real signals already in the database. The synthesis engine, prompt templates, and ItemManager are all built and waiting. One environment variable change transitions the system from "validated prototype" to "producing real intelligence."

**2. Rebuild the Docker container.** The running container is from March 9 and doesn't include the intelligence layer code built March 10–11. A docker build + deploy brings the deployed system current.

**3. Run a full synthesis cycle with Claude.** Once the API key is set, trigger a morning briefing synthesis against the sandbox project. Evaluate the quality of intelligence items produced. This is the moment of truth for the product thesis: does Claude-powered synthesis against real Procore data produce intelligence a PX would act on?

### Near-Term (Next 2 Weeks)

**4. Add httpx retry + timeout to synthesis API calls.** Before running synthesis in any production-like cadence, the Anthropic API call needs a 60-second timeout and at least one retry on 5xx responses.

**5. Write the E2E validation walkthrough (CC-6.3).** Document the end-to-end scenario: seed signals → run synthesis → verify intelligence items appear in Command Center → create Radar item → run Radar monitoring → verify matches. This becomes the repeatable demo script for pilot conversations.

**6. Upgrade Radar Stage 3 to Opus judgment.** Replace the algorithmic heuristic with a Claude API call that evaluates whether a signal-to-Radar match is genuinely relevant. This directly impacts the product's trust metric.

### Pre-Pilot (Before First Client Deployment)

**7. Automated test suite.** At minimum: signal detector unit tests, synthesis cycle integration test, Radar pipeline test, and API endpoint smoke tests.

**8. Sync agent hardening.** Connection pooling, retry with backoff, and distinguishing retryable vs permanent failures.

**9. Command Center visual polish pass (CC-6.4).** The current dark-theme SPA communicates the concept but needs refinement for executive-level pilot demos.

**10. Deep Dive request endpoint.** Build the POST /api/deep-dive trigger that queues an escalation review synthesis for a specific intelligence item.

---

## 8. Conclusion

The Instrumentality repo is in a strong position. The architecture faithfully implements a thoughtful set of specifications. The intelligence pipeline is complete from data sync through signal generation, synthesis, working memory lifecycle, Radar monitoring, and Command Center display. The database schema is production-quality. Real data is flowing.

The path from here to a working pilot demo is short and well-defined: set the API key, rebuild the container, run a synthesis cycle, evaluate the output quality, and polish. There are no architectural redesigns needed. The remaining work is operational — hardening, testing, and the visual layer.

The product thesis — that an AI intelligence layer sitting above Procore can produce insights a PX would act on — is about to be testable for the first time against real data with Claude-grade reasoning. That's the milestone to push toward.
