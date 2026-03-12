# Weekend Sprint Handoff — Session 1 Complete

**Date:** March 12, 2026
**Session:** Stream 1 (Infrastructure) + Stream 2 (Frontend) + Stream 3 (Validation)
**Commits:**
- App repo `master`: `de33918`
- Deploy repo `ops/phase3`: `434ef4f`

---

## What Got Done

### Stream 1: Infrastructure (8/8 tasks COMPLETE)

| Task | What Changed |
|------|-------------|
| Remove OpenClaw | Removed from `docker-compose.yml` (was blocking `docker compose up` with image pull failure) |
| Fix DNS/networking | All Docker services now use `host.docker.internal` to reach host PostgreSQL. `pg_hba.conf` updated with `172.16.0.0/12 trust`. `listen_addresses = '*'` in `postgresql.conf`. Postgres restarted. |
| Apply migrations | Already applied — 44 tables exist in `nerv_eva00` |
| Retire command-center-api | Removed from compose. Intelligence-engine (port 8098) is the canonical API. Watchdog dependency updated. |
| Configure model params | `SYNTHESIS_MODEL` default → `claude-opus-4-20250514`. `SIGNAL_LLM_MODEL` default → `claude-haiku-4-5-20251001`. |
| Wire webhook-to-signal hook (CC-2.3) | `services/webhook-receiver/processor.py` now calls `POST /api/synthesis/sweep` on intelligence-engine after every successful webhook DB write. Best-effort, non-blocking. |
| Seed signals | 326 signals already existed from prior sweeps |
| Run Opus synthesis | Completed successfully. Cycle `bcf61778-...`, model `claude-opus-4-20250514`, health: green |

### Stream 2: Frontend (ALL tickets covered)

The vanilla JS SPA at `nerv-interface/static/command-center.html` already implements every frontend ticket from the build breakdown. No React port was needed — the existing UI covers:

- CC-1.4: Project list (sidebar)
- CC-1.5: Layout & navigation (topbar, sidebar, main content area)
- CC-4.1: Health cards (intelligence-driven, with synthesis health indicators)
- CC-4.2: Intelligence feed (severity bars, confidence, evidence counts, attention badges)
- CC-4.3: RFI/Submittal tables with status badges
- CC-4.4: Synthesis trigger with async polling
- CC-5.2: Radar panel with create form
- CC-5.3: Radar detail view with activity log

**Enhancements made this session:**
- Sidebar health dots now driven by actual synthesis data (was hardcoded 'neutral')
- Synthesis trigger sweeps all projects when run from dashboard
- Init sequence refreshes sidebar after dashboard data loads
- Added `/health` endpoint to `server.py` (was returning 404)
- Added CORS middleware to both `server.py` and intelligence-engine `main.py`

### Stream 3: Validation (PASSED)

All 7 validation checks passed. See validation output in conversation history.

### Bug Fix

`synthesis_engine.py` line 1380: `ORDER BY created_at` → `ORDER BY snapshot_at` (column doesn't exist in `working_memory_state` table — the correct column is `snapshot_at`). Fixed in both app repo and deploy repo copies.

---

## Current System State

### Database (`nerv_eva00` on localhost:5432)

| Table | Count |
|-------|-------|
| Projects (active) | 2 |
| Signals | 326 |
| Intelligence Items | 13 |
| Synthesis Cycles | 3 (1 Opus, 2 local) |
| Radar Items | 2 |
| RFIs | 146 |
| Submittals | 151 |

### How to Run

```bash
cd nerv-interface
ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY /home/moby/.openclaw/workspace/nerv-deploy-repo/.env | cut -d= -f2) \
SYNTHESIS_MODEL=claude-opus-4-20250514 \
PORT=8888 \
python3 server.py
```

Then open: `http://localhost:8888/command-center`

### Docker Status

Docker stack is NOT running. The compose file is updated and validated (`docker compose config` passes), but no services have been started yet. The sprint validation was done against the local server directly.

To start Docker (not tested yet this session):
```bash
cd /home/moby/.openclaw/workspace/nerv-deploy-repo
docker compose up -d
```

Note: Data directories exist at `/home/moby/nerv-data/`. Redis password needed in `.env`.

---

## What's Left for Next Session

### Must Do

1. **Run a fresh Opus synthesis with more signal coverage.** The Opus cycle only processed 1 signal (the others were already consumed by prior local_algorithmic cycles). Either:
   - Run a new signal sweep first (`POST /api/synthesis/sweep`), then trigger synthesis
   - Or reset signal `synthesis_cycle_id` to NULL to make them available again

2. **Test Docker stack.** The compose file is updated but hasn't been `docker compose up`'d. Could hit issues with service builds, missing Dockerfiles, or Redis config.

3. **Demo walkthrough.** Open the Command Center in a browser and verify the visual presentation meets the "boomer executive 10-second test." Check:
   - Health cards show real project health (red/yellow/green)
   - Intelligence items have meaningful, specific summaries (not generic)
   - Synthesis summary reads like a PM briefing
   - Radar items display correctly

### Nice to Have

4. **Run synthesis on the Sandbox Test Project** (the one with 146 RFIs and 151 submittals — it has actual data). This project currently shows health: red from the local_algorithmic cycle. An Opus cycle should produce a richer briefing.

5. **CC-6.4 Visual Polish.** The frontend works but could use:
   - DM Sans font (currently uses system fonts)
   - Loading states could be smoother
   - Mobile responsiveness isn't tested

6. **Deploy repo: merge `ops/phase3` to main.** Currently on a feature branch.

### Known Issues

- **Collation warning:** `database "nerv_eva00" has a collation version mismatch` — cosmetic, doesn't affect functionality. Fix with `ALTER DATABASE nerv_eva00 REFRESH COLLATION VERSION;`
- **OPENCLAW_GATEWAY_TOKEN warning:** Printed on startup, harmless — OpenClaw is removed from the stack
- **Vite scaffold:** `command-center/` directory in deploy repo is still a stock Vite scaffold. Not used — the real frontend is `nerv-interface/static/command-center.html`

---

## File Change Summary

### App Repo (Procore-Instrumentality-Project)

| File | Change |
|------|--------|
| `nerv-interface/server.py` | Added `/health` endpoint, CORS middleware |
| `nerv-interface/static/command-center.html` | Sidebar health dots, synthesis sweep-all, init refresh |
| `nerv-interface/synthesis_engine.py` | Bug fix: `created_at` → `snapshot_at` |
| `Weekend_Sprint_Mission_Brief_v2_0_Post_Audit_Revision.md` | Added (mission brief) |

### Deploy Repo (nerv-deploy)

| File | Change |
|------|--------|
| `docker-compose.yml` | Removed openclaw + postgres + command-center-api. All services → host postgres. Model defaults updated. Volumes cleaned. |
| `services/intelligence-engine/main.py` | Added CORS middleware |
| `services/intelligence-engine/synthesis_engine.py` | Bug fix: `created_at` → `snapshot_at` |
| `services/webhook-receiver/processor.py` | Added CC-2.3 webhook-to-signal hook |

### Infrastructure

| Change | Details |
|--------|---------|
| `/var/lib/postgres/data/pg_hba.conf` | Added `host all all 172.16.0.0/12 trust` |
| `/var/lib/postgres/data/postgresql.conf` | Changed `listen_addresses` from `localhost` to `*` |
