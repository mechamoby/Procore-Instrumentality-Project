# Handoff — Last updated 2026-03-10

## What Happened (2026-03-10) — COMMAND CENTER BUILD

### Full Pipeline Build (Phases 1-6)
- **CC-1.1:** Intelligence layer schema created — 6 tables (signals, synthesis_cycles, intelligence_items, intelligence_item_evidence, working_memory_state, reinforcement_candidates) + 3 Radar tables, 11+ enum types, 26+ indexes
- **CC-1.2 + CC-1.3:** Full REST API for Command Center — Procore data endpoints (projects, RFIs, submittals, daily logs, schedule, change orders) + intelligence data endpoints (signals, items, synthesis cycles, dashboard overview)
- **CC-1.4 + CC-1.5:** Command Center SPA frontend at `/command-center` — dark navy/steel-blue theme, project sidebar, dashboard with health cards, tabbed project detail, responsive layout
- **CC-2.1 + CC-2.2:** Signal generation service — 6 deterministic detectors (RFI overdue, submittal rejected/overdue, daily log missing, milestone approaching, CO status changed) + LLM-based detection via Ollama/DeepSeek with category enforcement and deduplication
- **CC-3.1 + CC-3.2 + CC-3.3:** Synthesis engine — 4 prompt templates (Morning/Midday/EOD/Escalation), Anthropic API with prompt caching, ItemManager with full lifecycle (create/update/reinforce/downgrade/resolve/merge/archive), evidence chain management
- **CC-4.4:** Synthesis trigger button + signal sweep in dashboard UI
- **CC-5.1 + CC-5.2 + CC-5.3:** Radar backend (schema + full CRUD API) + Radar UI (list, create form, detail view with activity log)
- **CC-6.3:** Validation tooling — schema init script, 5-scenario test data seeder

### Commits (3 pushes to master)
- `32051fe` — Phase 1-3: schema, API, signals, synthesis, frontend
- `e007155` — Phase 4-5: Radar backend, synthesis trigger, UI enhancements
- `99b119d` — Phase 6: validation scripts, blockers

### Blockers (see BLOCKERS.md)
1. Schema needs to be applied to live database: `python3 scripts/init-intelligence-layer.py`
2. `ANTHROPIC_API_KEY` env var required for synthesis
3. Ollama + DeepSeek needed for LLM-based signal generation (optional for prototype)
4. `psycopg2-binary` needs to be installed in service environment

### Key New Files
- `eva-agent/eva-00-design/INTELLIGENCE-LAYER-SCHEMA.sql` — full intelligence + radar schema
- `nerv-interface/steelsync_db.py` — database connection pool
- `nerv-interface/command_center_api.py` — all REST API endpoints
- `nerv-interface/signal_generation.py` — signal detectors + LLM service
- `nerv-interface/synthesis_engine.py` — synthesis cycle + item manager
- `nerv-interface/static/command-center.html` — Command Center SPA
- `scripts/init-intelligence-layer.py` — schema initialization
- `scripts/seed-test-signals.py` — test data for 5 scenarios

## Previous Session (2026-02-26) — MASSIVE DAY

### Morning (4 AM - 9 AM)
- Rei Clone Reset at 4:16 AM (light session, no carryover)
- **7 Docker audit fixes committed + pushed** (GitHub: d813387 → 5b747f5)
  - .dockerignore, Python 3.12, watchdog shared HTTP client, backup cron, Smartsheet import, subnet removal, log rotation
  - Remaining audit: ~10 medium/low items
- **Cloudflare Access enabled** on nerv-command.com — Zero Trust "NERV Check" policy
  - Only stula.nick@gmail.com + mecha.moby@gmail.com can access
  - Confirmed working in incognito

### Midday (Commute)
- **Drawing Intelligence breakthrough** — tested 3-prong pipeline on real BTV5 drawings:
  - Prong 1 (PDF text): ✅ Nailed elevation schedule (free)
  - Prong 2 (DXF): ✅ Found data but needs spatial reasoning
  - Prong 3 (Vision AI): ❌ Read 3'-0" when answer was 2'-0" — missed centerline symbol
  - **Core insight (Nick):** Vision AI doesn't understand construction symbology — reads drawings like a photo, not like a PM
  - **Solution:** Build symbol recognition pre-processing layer
  - Confirmed Procore API provides `png_url` + `pdf_url` for every drawing
- Emailed Nick: A-7.00 PDF + DXF inventory (160 files)
- Full research doc: `NERV-DOCS/drawing-intelligence/SYMBOL-RECOGNITION-RESEARCH.md`

### Evening
- **Symbol Dictionary Operation launched:**
  - MAGI: delivered 854-line symbol catalog (`SYMBOL-DICTIONARY-RAW.md`)
  - mini-Moby: delivered tooling research (`TOOLING-RESEARCH.md`) — YOLOv8, datasets, ODA converter
  - Moby: built v1 dictionary (25+ symbols, 5 categories) + drawing_reader.py pipeline
- **Pico agent deployed** — Almudena's business assistant for Nico Pico Kids
  - Bot: @Almudenanicopicobot, model: GPT-5 via her ChatGPT Plus
  - FIRST external agent deployment — non-technical user, fully working
  - Key lesson: bindings[] entry required for telegram account → agent routing
- **drawing_reader.py** built at `nerv-deploy/services/drawing-intel/drawing_reader.py`
  - Symbol-aware query builder, 3-prong analysis, spatial search
  - Fixed false positive matching (CL in CLEARANCE)
  - Tested: symbol-aware prompts improve but don't fully solve vision AI accuracy

## Active Priorities
1. **Drawing Intelligence** — merge MAGI + mini-Moby research into master dictionary, build detection pipeline
2. **Remaining Docker audit items** — ~10 medium/low findings
3. **NERV stack** — Smartsheet functional testing, e2e Procore integration, portal real API calls
4. **Business** — demo package, branding decision, MSA template

## Key Files
- `NERV-DOCS/drawing-intelligence/SYMBOL-DICTIONARY-V1.md` — structured dictionary
- `NERV-DOCS/drawing-intelligence/SYMBOL-DICTIONARY-RAW.md` — MAGI's raw research
- `NERV-DOCS/drawing-intelligence/TOOLING-RESEARCH.md` — mini-Moby's tooling research
- `NERV-DOCS/drawing-intelligence/SYMBOL-RECOGNITION-RESEARCH.md` — master research doc
- `nerv-deploy/services/drawing-intel/drawing_reader.py` — pipeline code

### Evening (9 PM - 11 PM)
- **Pico agent deployed** for Elena (Nick's wife) — @Almudenanicopicobot
  - Multiple debugging rounds: wrong model string, missing binding, wrong token type, cached sessions
  - All resolved — working on GPT-5 via Elena's ChatGPT Plus
  - **Agent Deployment Protocol written:** `protocols/AGENT-DEPLOYMENT.md` — every mistake documented with fix
- Nick mentioned using his PC as first full NERV deployment test (future)
- No NAP tonight — Nick exhausted, called it a night ~11 PM

## Infrastructure State
- Gateway running
- 4 agents: main (Moby), katsuragi, mini-moby, pico
- 4 telegram bindings (all working)
- nerv-command.com: live, Cloudflare Access protected
- Latest nerv-deploy commit: 5aeecbb (pushed)
- Docker stack: 13 services, all healthy (as of NAP 02.25 test)
- Pico OAuth token expires ~10 days (needs refresh mechanism)
