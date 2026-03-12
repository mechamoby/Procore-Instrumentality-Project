# EVA Naming Convention Audit — Rename Map

## Summary

- Total Evangelion-themed references found: **~1,290** (across all search terms)
- Files affected: **125**
- Services/directories affected: **16** top-level directories/groupings
- False positives excluded: **~50** (angel, entry, soul in non-Evangelion contexts)
- Terms searched: eva-00, eva-01, eva-02, eva-sentry, evangelion, nerv, magi, instrumentality, seele, gehirn, terminal dogma, dummy plug, entry plug, AT field, lance of longinus, soul, angel

## Reference Counts by Term

| Term | Count | Notes |
|---|---|---|
| `nerv` | 812 | Most pervasive — repo name, service names, container names, env vars, network, comments |
| `eva-sentry` / `eva_sentry` | 87 | Service name + all references to it |
| `eva-01` / `eva_01` | 77 | Agent directory, workspace files, setup scripts |
| `eva-00` / `eva_00` | 67 | Agent directory, workspace files, setup scripts, db var prefix |
| `eva-02` / `eva_02` | 67 | Agent directory, workspace files, setup scripts |
| `soul` | 39 | SOUL.md agent persona files (4 files) + references |
| `instrumentality` | 37 | Repo name "Procore-Instrumentality-Project" + references |
| `evangelion` | 28 | GitHub URL, comments, audit reports |
| `angel` | 28 | Mostly false positives (e.g., "Los Angeles") — ~5 genuine |
| `seele` | 23 | setup.sh branding line, agent identity files |
| `magi` | 15 | Agent config, drawing-intel model references |
| `dummy plug` | 2 | Agent workspace files |
| `entry plug` | 2 | Agent workspace files |
| `AT field` | 2 | Agent workspace files |
| `lance of longinus` | 1 | Agent workspace file |
| `terminal dogma` | 2 | Agent workspace files |
| `gehirn` | 1 | Agent workspace file |

---

## Rename Map by Service/Directory

### 1. Repository Name

| Current Name | Proposed Replacement | Notes |
|---|---|---|
| `Procore-Instrumentality-Project` | `steelsync-intelligence` | The intelligence brain repo. "Instrumentality" is Evangelion. |

### 2. nerv-deploy-repo (Deploy Repository)

| Current Name | Location | Proposed Replacement | Notes |
|---|---|---|---|
| `nerv-deploy` | Repo name / directory | `steelsync-deploy` | Primary deployment repo |
| `nerv-network` | docker-compose.yml (network) | `steelsync-network` | Docker bridge network |
| `nerv-interface` | docker-compose.yml (service) | `steelsync-portal` | Web dashboard service |
| `nerv-openclaw` | docker-compose.yml (container) | Remove or replace with gateway service | OpenClaw dependency |
| `nerv-postgres` | docker-compose.yml (container) | `steelsync-postgres` | Container name only |
| `nerv-redis` | docker-compose.yml (container) | `steelsync-redis` | Container name only |
| `nerv-watchdog` | docker-compose.yml (container) | `steelsync-watchdog` | Container name only |
| `nerv-portal-auth` | docker-compose.yml (container) | `steelsync-portal-auth` | Container name only |
| `nerv-smartsheet-adapter` | docker-compose.yml (container) | `steelsync-smartsheet-adapter` | Container name only |
| `nerv-eva-sentry` | docker-compose.yml (container) | `steelsync-document-gateway` | See eva-sentry below |
| `nerv-token-guardian` | docker-compose.yml (container) | `steelsync-token-guardian` | Container name only |
| `nerv-webhook-receiver` | docker-compose.yml (container) | `steelsync-webhook-receiver` | Container name only |
| `nerv-inbox-watcher` | docker-compose.yml (container) | `steelsync-inbox-watcher` | Container name only |
| `nerv-embedding-pipeline` | docker-compose.yml (container) | `steelsync-embedding-pipeline` | Container name only |
| `nerv-notification-engine` | docker-compose.yml (container) | `steelsync-notification-engine` | Container name only |
| `nerv-drawing-intel` | docker-compose.yml (container) | `steelsync-drawing-intel` | Container name only |
| `nerv-backup` | docker-compose.yml (container) | `steelsync-backup` | Container name only |
| `nerv-healthcheck` | docker-compose.yml (container) | `steelsync-healthcheck` | Container name only |

### 3. nerv-deploy-repo/services/eva-sentry/ (Document Security Gateway)

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `eva-sentry` | Directory name | `document-gateway` | Scans, classifies, routes, and gates documents |
| `eva-sentry` | docker-compose.yml:296 | `document-gateway` | Service name |
| `eva-sentry.service` | services/eva-sentry/ | `document-gateway.service` | Systemd unit file |
| `SENTRY_URL` | docker-compose.yml:272 | `DOCUMENT_GATEWAY_URL` | Env var reference |
| `SENTRY_STATE_DIR` | docker-compose.yml:305 | `GATEWAY_STATE_DIR` | Env var |
| `SENTRY_INGEST_DIR` | docker-compose.yml:306 | `GATEWAY_INGEST_DIR` | Env var |
| `SENTRY_PORT` | docker-compose.yml:303 | `DOCUMENT_GATEWAY_PORT` | Env var |
| `sentry-data` | docker-compose.yml (volume) | `gateway-data` | Docker volume |
| `sentry_results` | database/migrations/010 | `document_scan_results` | DB table |

**Affected files (7):** `main.py`, `db.py`, `scanner.py`, `route_engine.py`, `outbound_gate.py`, `notification_client.py`, `Dockerfile`

### 4. nerv-deploy-repo/agents/ (Agent Workspaces)

| Current Name | Location | Proposed Replacement | Notes |
|---|---|---|---|
| `agents/eva-00/` | Directory | `agents/clerk-00/` or `agents/historian/` | EVA-00 = Master Clerk & Project Historian |
| `agents/eva-01/` | Directory | `agents/submittal-agent/` | EVA-01 = Submittal Agent |
| `agents/eva-02/` | Directory | `agents/rfi-agent/` | EVA-02 = RFI Agent |
| `SOUL.md` | Agent workspace files (4) | `PERSONA.md` or `IDENTITY.md` | Already have IDENTITY.md; SOUL.md is the primary persona definition |
| `SEELE Systems` | setup.sh:564 | `SteelSync Platform` | Branding string |

**Affected files (15):** All files under `agents/eva-*/workspace/` (SOUL.md, IDENTITY.md, AGENTS.md, USER.md, MEMORY.md × 3 agents)

### 5. nerv-deploy-repo/nerv-interface/ (Web Dashboard)

| Current Name | Location | Proposed Replacement | Notes |
|---|---|---|---|
| `nerv-interface/` | Directory | `steelsync-portal/` | Web dashboard directory |
| `NERV` (display) | static/index.html, portal.html, login.html, onboarding.html | `SteelSync` | UI branding in HTML |
| `nerv_*` CSS classes | static/*.html | `steelsync_*` | CSS class prefixes |

**Affected files (5):** `server.py`, `static/index.html`, `static/portal.html`, `static/login.html`, `static/onboarding.html`

### 6. NERV-Prefixed Environment Variables

| Current Name | Files | Proposed Replacement | Notes |
|---|---|---|---|
| `NERV_DATABASE_URL` | webhook-receiver, inbox-watcher, embedding-pipeline | `DATABASE_URL` | Align with other services that already use `DATABASE_URL` |
| `NERV_STORAGE_ROOT` | webhook-receiver, drawing-intel, inbox-watcher, embedding-pipeline | `STORAGE_ROOT` | Remove NERV prefix |
| `NERV_PROCORE_CLIENT_ID` | webhook-receiver | `PROCORE_CLIENT_ID` | Already exists without prefix in other services |
| `NERV_PROCORE_CLIENT_SECRET` | webhook-receiver | `PROCORE_CLIENT_SECRET` | Already exists without prefix |
| `NERV_PROCORE_COMPANY_ID` | webhook-receiver | `PROCORE_COMPANY_ID` | Already exists without prefix |
| `NERV_PROCORE_WEBHOOK_SECRET` | webhook-receiver | `PROCORE_WEBHOOK_SECRET` | Remove NERV prefix |
| `NERV_PROCORE_BASE_URL` | webhook-receiver | `PROCORE_BASE_URL` | Already exists without prefix |
| `NERV_EMBEDDING_MODEL` | embedding-pipeline | `EMBEDDING_MODEL` | Remove NERV prefix |
| `NERV_SESSION_KEY` | nerv-interface server.py | `SESSION_KEY` | Remove NERV prefix |
| `NERV_PORT` | docker-compose.yml | `PORTAL_PORT` | Rename to match function |

### 7. EVA-Prefixed Environment Variables

| Current Name | Files | Proposed Replacement | Notes |
|---|---|---|---|
| `EVA00_DB` | steelsync_db.py, database.py, sync_agent.py, scripts | `STEELSYNC_DB` | Database name |
| `EVA00_DB_USER` | steelsync_db.py, database.py, sync_agent.py, scripts | `STEELSYNC_DB_USER` | Database user |
| `EVA00_DB_HOST` | steelsync_db.py, database.py, sync_agent.py, scripts | `STEELSYNC_DB_HOST` | Database host |
| `EVA00_DB_PORT` | steelsync_db.py, database.py, sync_agent.py, scripts | `STEELSYNC_DB_PORT` | Database port |
| `EVA00_DB_PASSWORD` | referenced in code | `STEELSYNC_DB_PASSWORD` | Database password |
| `EVA_AGENT_PASSWORD` | docker-compose.yml, security-roles.sql | `STEELSYNC_AGENT_PASSWORD` | DB role password |
| `EVA_ADMIN_PASSWORD` | docker-compose.yml, security-roles.sql | `STEELSYNC_ADMIN_PASSWORD` | DB role password |
| `EVA_SENTRY_URL` | various service configs | `DOCUMENT_GATEWAY_URL` | References to eva-sentry service |

### 8. nerv-deploy-repo/database/ (Schema & Migrations)

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `nerv` (database name) | docker-compose.yml:129, schema.sql | `steelsync` | Default DB name via POSTGRES_DB |
| `eva` (DB user) | docker-compose.yml:127 | `steelsync` | Default DB user via POSTGRES_USER |
| `nerv_agent` | security-roles.sql | `steelsync_agent` | DB role |
| `nerv_admin` | security-roles.sql | `steelsync_admin` | DB role |
| `nerv_agent_changeme` | security-roles.sql | Templated from env var | Default password (should already be templated) |
| `nerv_admin_changeme` | security-roles.sql | Templated from env var | Default password (should already be templated) |

### 9. nerv-deploy-repo/scripts/

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `nerv-setup.sh` | scripts/ | `steelsync-setup.sh` | Setup script filename |
| `NERV` references | All scripts (~93 references) | `SteelSync` | Display names, comments, log messages |

**Affected files (10):** `deploy.sh`, `rollback.sh`, `healthcheck.sh`, `init-db.sh`, `backup.sh`, `backup-script.sh`, `create-project-folders.sh`, `auto-update.sh`, `update.sh`, `auth-watchdog.py`

### 10. nerv-deploy-repo/config/

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `magi` model references | generate-config.py | Rename to functional names | "MAGI" is Evangelion's computer system |
| `eva-00/01/02` agent references | generate-config.py | Match new agent directory names | Config generation references old names |

### 11. nerv-deploy-repo/shared-knowledge/

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `NERV` references | procore-workflows.md, csi-masterformat.md | `SteelSync` | Shared knowledge base references |

### 12. nerv-deploy-repo/tools/

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `NERV` references | cost-calculator.py, ingest_email_archive.py, etc. | `SteelSync` | Tool scripts |

### 13. nerv-deploy-repo/docs/

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `NERV`, `EVA` references | TROUBLESHOOTING.md, SECURITY-ARCHITECTURE.md, SECRETS-MANAGEMENT.md, E2E test report | `SteelSync` | Documentation references |

### 14. Workspace Root Files

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `SOUL.md` | workspace root | `PERSONA.md` | Agent persona file at root level |
| `nerv-deploy/` | workspace directory | `steelsync-deploy/` | Legacy directory reference |
| `nerv-uploads/` | workspace directory | `steelsync-uploads/` | Upload staging directory |
| `eva-sentry-v1/` | workspace directory | `document-gateway-v1/` or remove | Legacy backup directory |
| Various `NERV`/`EVA` references | CONTEXT.md, KNOWLEDGE.md, PRODUCT_BRIEF.md, SETUP.md | `SteelSync` | Working documents |

### 15. Workspace Root Operation Reports (Documentation Only)

| Current Name | File | Proposed Replacement | Notes |
|---|---|---|---|
| `nerv_deploy_audit_report_*` | workspace root | `steelsync_deploy_audit_report_*` | Historical reports — rename if desired, not critical |
| Various EVA references | PHASE_*_OPERATION_STEEL_PIPE_*.md | N/A | Historical operation reports — rename references in future versions only |

### 16. GitHub/Remote References

| Current Name | Location | Proposed Replacement | Notes |
|---|---|---|---|
| `ghcr.io/evangelion-project/openclaw:latest` | docker-compose.yml:8 | Update when image is rebuilt | Container registry reference |
| `github.com/evangelion-project/nerv-deploy` | docker-compose.yml:3 | `github.com/[org]/steelsync-deploy` | Comment URL |

---

## Recommended Rename Execution Order

1. **Database defaults** (nerv→steelsync, eva→steelsync) — Requires coordinated update of docker-compose.yml, .env, security-roles.sql, and all services referencing DB credentials
2. **Environment variables** (NERV_*, EVA_* prefixes) — Requires update of docker-compose.yml and all service code simultaneously
3. **Container names** (nerv-* → steelsync-*) — Docker Compose only, but affects monitoring scripts and docs
4. **Service directory** (eva-sentry/ → document-gateway/) — Requires Dockerfile, docker-compose.yml, and all inter-service URL references
5. **Agent directories** (eva-00/01/02 → functional names) — Requires setup.sh, add-agent.sh, remove-agent.sh, generate-config.py updates
6. **Interface directory** (nerv-interface/ → steelsync-portal/) — Directory rename + docker-compose.yml
7. **Documentation and comments** — Lowest risk, can be done incrementally

**Warning:** Steps 1-4 must be coordinated carefully — they affect running services. A phased approach with one Docker Compose rebuild per step is recommended. Each step should include verification that all services start and pass health checks before proceeding to the next.
