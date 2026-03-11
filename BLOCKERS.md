# SteelSync Build Blockers

## Active

### B-2: ANTHROPIC_API_KEY Required for Synthesis
- **Status:** BLOCKING — only remaining blocker
- **Impact:** Synthesis engine cannot call Claude API without this. Everything else works.
- **Location:** `/home/moby/.openclaw/workspace/nerv-deploy-repo/.env` has `ANTHROPIC_API_KEY=` (empty)
- **Fix:** Set `ANTHROPIC_API_KEY=sk-ant-...` in environment or .env file
- **Notes:** Deterministic signal detectors, full frontend, Radar, all API endpoints work without it. Only the Opus synthesis call is blocked.

### B-3: Ollama/DeepSeek Required for LLM-Based Signal Generation
- **Status:** Optional for prototype
- **Impact:** LLM-based signal generation (CC-2.2) needs Ollama running with DeepSeek model
- **Fix:** Ensure Ollama is running on localhost:11434 with `deepseek-r1:8b` model loaded
- **Notes:** Deterministic detectors work without Ollama. Not needed for core demo.

## Resolved

### B-1: Intelligence Layer Schema Not Yet Applied to Database
- **Status:** RESOLVED 2026-03-11
- **Resolution:** `python3 scripts/init-intelligence-layer.py` — all 9 tables, 15 types, 35 indexes verified OK

### B-4: psycopg2 Dependency
- **Status:** RESOLVED 2026-03-11
- **Resolution:** Already installed and working (`psycopg2` available in system Python)
