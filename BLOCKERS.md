# SteelSync Build Blockers

## Active

### B-1: Intelligence Layer Schema Not Yet Applied to Database
- **Status:** Pending manual action
- **Impact:** All intelligence features (signals, synthesis, Radar) require these tables
- **Fix:** Run `python3 scripts/init-intelligence-layer.py` against the live database
- **Notes:** Schema file is ready. Need database access to apply.

### B-2: ANTHROPIC_API_KEY Required for Synthesis
- **Status:** Environment variable needed
- **Impact:** Synthesis engine cannot call Claude API without this
- **Fix:** Set `ANTHROPIC_API_KEY` environment variable before running synthesis
- **Notes:** Deterministic signal detectors and the full frontend work without it

### B-3: Ollama/DeepSeek Required for LLM-Based Signal Generation
- **Status:** Optional for prototype
- **Impact:** LLM-based signal generation (CC-2.2) needs Ollama running with DeepSeek model
- **Fix:** Ensure Ollama is running on localhost:11434 with `deepseek-r1:8b` model loaded
- **Notes:** Deterministic detectors work without Ollama. Synthesis engine uses Anthropic API directly.

### B-4: psycopg2 Dependency
- **Status:** Needs verification
- **Impact:** All database operations require psycopg2
- **Fix:** `pip install psycopg2-binary` in the nerv-interface service environment

## Resolved
(none yet)
