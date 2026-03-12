# Environment Variable Completeness Audit

## Date: 2026-03-11

## Scope

This audit covers the **Procore-Instrumentality-Project** repository (the intelligence brain). Environment variables were extracted by searching all Python files for `os.environ` / `os.getenv`, all shell scripts for `${VAR}` interpolation, and the deployment template `docker-compose.yml` for `${VAR}` references.

**Config template status:** No `.env.example`, `.env.template`, or `.env.sample` file exists in this repository. The closest equivalent is the setup wizard at `eva-agent/deployment-template/scripts/setup.sh`, which generates a `.env` file at runtime. The deployment template `docker-compose.yml` references env vars that are expected to come from that generated `.env`. For cross-referencing purposes, the variables written by setup.sh are treated as the "documented" set.

---

## Summary

| Metric | Count |
|--------|-------|
| Total unique env vars referenced in code | **30** |
| Documented (in setup.sh-generated .env) | **14** |
| MISSING from .env template (setup blocker risk) | **16** |
| UNDOCUMENTED (in template but not referenced in code) | **1** |

---

## Full Variable Inventory

| # | Variable | In Setup Template? | Sensitivity | Referenced By | Notes |
|---|----------|-------------------|-------------|---------------|-------|
| 1 | `EVA00_DB` | NO | CONFIG | steelsync_db.py, database.py, sync_agent.py, ingest_btv5.py, init-intelligence-layer.py, seed-test-signals.py | Default: `nerv_eva00` |
| 2 | `EVA00_DB_USER` | NO | CONFIG | steelsync_db.py, database.py, sync_agent.py, init-intelligence-layer.py, seed-test-signals.py | Default: `moby` |
| 3 | `EVA00_DB_HOST` | NO | CONFIG | steelsync_db.py, database.py, sync_agent.py, init-intelligence-layer.py, seed-test-signals.py | Default: `localhost` |
| 4 | `EVA00_DB_PORT` | NO | CONFIG | steelsync_db.py, database.py, sync_agent.py, init-intelligence-layer.py, seed-test-signals.py | Default: `5432` |
| 5 | `ANTHROPIC_API_KEY` | YES | SECRET | synthesis_engine.py, docker-compose.yml | No default; empty string fallback in code |
| 6 | `SYNTHESIS_MODEL` | NO | CONFIG | synthesis_engine.py | Default: `claude-sonnet-4-20250514` |
| 7 | `OLLAMA_HOST` | NO | CONFIG | signal_generation.py | Default: `http://localhost:11434` |
| 8 | `SIGNAL_LLM_MODEL` | NO | CONFIG | signal_generation.py | Default: `deepseek-r1:8b` |
| 9 | `OPENCLAW_GATEWAY_TOKEN` | NO | SECRET | server.py, katsuragi-email.py, katsuragi-email-poll.sh | Empty default; shell script reads from file fallback |
| 10 | `OPENCLAW_GATEWAY_PORT` | NO | CONFIG | katsuragi-email.py, katsuragi-email-poll.sh | Default: `18789` |
| 11 | `PORT` | NO | CONFIG | server.py | Default: `8080`; controls nerv-interface listen port |
| 12 | `SMTP_HOST` | YES | CONFIG | server.py, docker-compose.yml | Default in code: `smtp.gmail.com` |
| 13 | `SMTP_PORT` | YES | CONFIG | server.py, docker-compose.yml | Default: `587` |
| 14 | `SMTP_USER` | YES | CONFIG | server.py, docker-compose.yml | No default |
| 15 | `SMTP_PASSWORD` | YES | SECRET | docker-compose.yml, setup.sh | Named `SMTP_PASS` in server.py (mismatch!) |
| 16 | `SMTP_PASS` | NO | SECRET | server.py | server.py uses `SMTP_PASS`, template uses `SMTP_PASSWORD` |
| 17 | `SMTP_FROM` | YES | CONFIG | docker-compose.yml | Not referenced in Instrumentality Python code |
| 18 | `IMAP_HOST` | NO | CONFIG | ingest_email.py | Default: `imap.gmail.com` |
| 19 | `IMAP_PORT` | NO | CONFIG | ingest_email.py | Default: `993` |
| 20 | `IMAP_USER` | NO | CONFIG | ingest_email.py | No default |
| 21 | `IMAP_PASS` | NO | SECRET | ingest_email.py | No default |
| 22 | `PROCORE_COMPANY_ID` | YES | CONFIG | sync_agent.py, docker-compose.yml | Default: `4281379` (sandbox) |
| 23 | `PROCORE_PROJECT_IDS` | NO | CONFIG | sync_agent.py | Default: `316469`; comma-separated list |
| 24 | `PROCORE_CLIENT_ID` | YES | SECRET | docker-compose.yml | Not directly referenced in Instrumentality Python code |
| 25 | `PROCORE_CLIENT_SECRET` | YES | SECRET | docker-compose.yml | Not directly referenced in Instrumentality Python code |
| 26 | `SYNC_API_DELAY` | NO | CONFIG | sync_agent.py | Default: `0.6` seconds |
| 27 | `SYNC_INTERVAL_PROJECTS` | NO | CONFIG | sync_agent.py | Default: `3600` |
| 28 | `SYNC_INTERVAL_SUBMITTALS` | NO | CONFIG | sync_agent.py | Default: `300` |
| 29 | `SYNC_INTERVAL_RFIS` | NO | CONFIG | sync_agent.py | Default: `300` |
| 30 | `SYNC_INTERVAL_DRAWINGS` | NO | CONFIG | sync_agent.py | Default: `900` |
| 31 | `SYNC_INTERVAL_COMPANIES` | NO | CONFIG | sync_agent.py | Default: `3600` |
| 32 | `SYNC_INTERVAL_CONTACTS` | NO | CONFIG | sync_agent.py | Default: `3600` |
| 33 | `SYNC_INTERVAL_DOCUMENTS` | NO | CONFIG | sync_agent.py | Default: `1800` |

### Docker-Compose-Only Variables (deployment template)

These are referenced in `eva-agent/deployment-template/docker-compose.yml` but not in the Instrumentality Python code directly:

| # | Variable | In Setup Template? | Sensitivity | Notes |
|---|----------|-------------------|-------------|-------|
| 34 | `AGENT_PORT` | YES | CONFIG | Default: `3000`; OpenClaw container port |
| 35 | `POSTGRES_USER` | YES (generated) | CONFIG | Default: `eva` |
| 36 | `POSTGRES_PASSWORD` | YES (generated) | SECRET | Generated randomly by setup wizard |
| 37 | `POSTGRES_DB` | YES (generated) | CONFIG | Default: `eva_agent` |
| 38 | `DATABASE_URL` | Composed in docker-compose | SECRET | Assembled from POSTGRES_USER/PASSWORD/DB |
| 39 | `REDIS_URL` | Hardcoded | CONFIG | Hardcoded as `redis://redis:6379` in compose |
| 40 | `DOCUSIGN_INTEGRATION_KEY` | YES | SECRET | Optional integration |
| 41 | `DOCUSIGN_SECRET_KEY` | YES | SECRET | Optional integration |
| 42 | `DOCUSIGN_ACCOUNT_ID` | YES | CONFIG | Optional integration |

---

## Missing Variables (Action Required)

These variables are referenced in application code but have **no entry** in the setup wizard / deployment template. A new deployer would not know to set them without reading source code.

| Variable | Risk Level | Impact | Recommendation |
|----------|-----------|--------|----------------|
| `EVA00_DB` | **HIGH** | DB connection fails if not set and default `nerv_eva00` doesn't match Docker DB | Add to setup wizard; align with `POSTGRES_DB` |
| `EVA00_DB_USER` | **HIGH** | DB connection fails if default `moby` doesn't match Docker user | Add to setup wizard; align with `POSTGRES_USER` |
| `EVA00_DB_HOST` | **MEDIUM** | Defaults to `localhost`; needs to be `postgres` in Docker | Add to setup wizard with Docker-aware default |
| `EVA00_DB_PORT` | **LOW** | Default `5432` is standard | Document but low risk |
| `SYNTHESIS_MODEL` | **LOW** | Default works; override for cost/capability tuning | Document in setup wizard as optional |
| `OLLAMA_HOST` | **MEDIUM** | Default `localhost:11434`; Docker needs service name | Add to setup wizard |
| `SIGNAL_LLM_MODEL` | **LOW** | Default works for local Ollama | Document as optional |
| `OPENCLAW_GATEWAY_TOKEN` | **HIGH** | Auth to OpenClaw gateway; empty = no auth | Add to setup wizard |
| `OPENCLAW_GATEWAY_PORT` | **LOW** | Default `18789` works | Document as optional |
| `PORT` | **LOW** | Server listen port; default `8080` works | Document as optional |
| `SMTP_PASS` | **HIGH** | **Naming mismatch**: server.py reads `SMTP_PASS` but docker-compose sets `SMTP_PASSWORD` — email will silently fail | **Fix variable name** to be consistent |
| `IMAP_HOST` | **MEDIUM** | Email ingestion won't work without explicit config | Add to setup wizard |
| `IMAP_PORT` | **LOW** | Default `993` is standard | Document |
| `IMAP_USER` | **HIGH** | Email ingestion non-functional without this | Add to setup wizard |
| `IMAP_PASS` | **HIGH** | Email ingestion non-functional without this | Add to setup wizard |
| `PROCORE_PROJECT_IDS` | **MEDIUM** | Sync agent needs project IDs to know what to sync | Add to setup wizard |
| `SYNC_API_DELAY` | **LOW** | Tuning parameter; safe default | Document as optional |
| `SYNC_INTERVAL_*` (6 vars) | **LOW** | All have reasonable defaults | Document as optional |

---

## Undocumented Variables (Cleanup Candidates)

These appear in the setup wizard / docker-compose template but are **not referenced** in the Instrumentality repo's Python code:

| Variable | In Template | Notes |
|----------|-------------|-------|
| `SMTP_FROM` | setup.sh, docker-compose.yml | Used by Docker OpenClaw service; not by Instrumentality Python code. May be used by Deploy repo services. Keep. |
| `NODE_ENV` | docker-compose.yml (hardcoded `production`) | Standard Node.js var for OpenClaw container. Not relevant to Python code. Keep. |
| `AGENT_CONFIG_PATH` | docker-compose.yml (hardcoded path) | OpenClaw internal config. Keep. |
| `ROLES_CONFIG_PATH` | docker-compose.yml (hardcoded path) | OpenClaw internal config. Keep. |

These are not stale — they serve the OpenClaw container which is a separate codebase. No cleanup needed.

---

## Critical Findings

### 1. SMTP Variable Name Mismatch (BUG)

`nerv-interface/server.py` line 1025 reads `SMTP_PASS`:
```
smtp_pass = os.environ.get("SMTP_PASS", "")
```

But `eva-agent/deployment-template/docker-compose.yml` line 36 and `setup.sh` line 216 set `SMTP_PASSWORD`:
```
SMTP_PASSWORD=${SMTP_PASSWORD}
```

**Impact:** Email sending will silently fail in Docker deployments because the password is set under the wrong name.

**Fix:** Rename either the code reference or the template variable to match.

### 2. Database Variable Namespace Split

The Instrumentality repo uses `EVA00_DB`, `EVA00_DB_USER`, `EVA00_DB_HOST`, `EVA00_DB_PORT` for database configuration. The deployment template uses `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` and assembles a `DATABASE_URL`. These two naming schemes are not bridged — deploying the intelligence layer alongside the Docker stack requires manually setting both sets of variables or modifying `steelsync_db.py` to accept `DATABASE_URL`.

**Note from MEMORY.md:** `steelsync_db.py` was updated in the Deploy repo to support `DATABASE_URL` env var for Docker, but this change may not be reflected in the Instrumentality repo's copy.

### 3. No `.env.example` File

The repository has no `.env.example` or equivalent checked-in template. The setup wizard generates `.env` interactively, but only covers deployment template variables — not the intelligence layer variables (`EVA00_DB*`, `OLLAMA_HOST`, `SIGNAL_LLM_MODEL`, `SYNTHESIS_MODEL`, etc.).

**Recommendation:** Create a `.env.example` at the repo root listing all 42 variables with placeholder values and comments, grouped by service.

---

## Variable Classification by Sensitivity

### SECRET (must never be committed or logged)

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API authentication |
| `PROCORE_CLIENT_ID` | Procore OAuth client ID |
| `PROCORE_CLIENT_SECRET` | Procore OAuth client secret |
| `SMTP_PASS` / `SMTP_PASSWORD` | SMTP authentication |
| `IMAP_PASS` | IMAP email authentication |
| `OPENCLAW_GATEWAY_TOKEN` | OpenClaw gateway auth token |
| `POSTGRES_PASSWORD` | PostgreSQL authentication |
| `DATABASE_URL` | Contains embedded password |
| `DOCUSIGN_INTEGRATION_KEY` | DocuSign API key |
| `DOCUSIGN_SECRET_KEY` | DocuSign API secret |

### CONFIG (safe to document with example values)

All remaining variables (database names, hosts, ports, model names, sync intervals, etc.)

---

## Recommendations (Priority Order)

1. **Fix SMTP_PASS/SMTP_PASSWORD mismatch** — immediate bug fix
2. **Create `.env.example`** at repo root with all 42 variables, grouped and commented
3. **Bridge database variable namespaces** — ensure `steelsync_db.py` supports `DATABASE_URL` in this repo
4. **Add IMAP variables to setup wizard** — email ingestion is broken without them
5. **Add OPENCLAW_GATEWAY_TOKEN to setup wizard** — auth to gateway will fail silently
6. **Document optional tuning variables** (`SYNC_INTERVAL_*`, `SIGNAL_LLM_MODEL`, `SYNTHESIS_MODEL`) in README or setup wizard help text
