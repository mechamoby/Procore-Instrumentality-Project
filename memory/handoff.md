# Session Handoff
> Last updated: 2026-02-26 00:10 EST from Midnight Cron (autonomous)

## Latest Session: 2026-02-25 Morning/Afternoon (Telegram)

### API Cost Ceiling Analysis — LOCKED
- Built `nerv-deploy/tools/cost-calculator.py` (standalone, no deps)
- Full analysis doc: `NERV-DOCS/API-COST-ANALYSIS.md`
- Modeled 1x through 100x usage across all provider tiers + smart routing
- mini-Moby fact-checked, raised 6 caveats — all analyzed and addressed
- **Drawing analysis** identified as #1 cost driver (Nick's input from field experience)
- Modeled up to 1,000 drawings/day: $706/proj/mo on Sonnet 4 = 80% margin
- **Conclusion: pricing model is bulletproof at $3,500/mo**

### Client Communication Architecture — LOCKED
- Three lanes: **Email** (stateless/formal), **Telegram** (real-time/field), **NERV Web Portal** (dashboard)
- All three hit the same NERV database — channel is just delivery mechanism
- Security ranking: Portal > Telegram > Email

### Cloudflare Tunnel — LIVE ✅
- Domain purchased: **nerv-command.com** (~$10/year)
- cloudflared installed, authed, tunnel created
- **https://nerv-command.com is live** — confirmed working from Nick's phone
- Running as systemd service: `cloudflared-nerv.service` (auto-start, auto-restart)
- 4 QUIC connections through Miami Cloudflare nodes

### Client Deployment Walkthrough (DRAFT — not locked)
- Discussed full contract-to-operational pipeline
- Realistic timeline: ~2 weeks (not 4)
- Nick flagged: will need employee/contractor for physical installs + training
- Recommendation: Nick does first 3 clients himself, then hires
- Install labor cost: ~$500-750 per deployment, barely dents margin

### Branding Discussion (OPEN)
- mini-Moby raised legit IP concerns about using "NERV" officially (Evangelion)
- Moby proposed alternatives (AXON, CORTEX, FORGE, CITADEL, NEXUS) — Nick rejected all
- **NERV stays as internal codename** until the right name hits
- Name swap is just find-and-replace when ready — no technical impact

## Previous Session Context (2026-02-24 night)
- Company = NERV (internal codename), agents = EVAs
- Core positioning: "This isn't Procore AI. This is ABC Contractors AI."
- 100% focus on NERV database + managed service
- Pricing: $15K setup + $3,500/mo per project
- Hardware: Ryzen 9 7950X, 64GB DDR5, 2TB NVMe + 8TB HDD, RTX 4060 Ti 16GB (~$1,720)

## What Was Done 2026-02-25 Morning Session (Telegram)

### API Cost Ceiling Analysis — LOCKED
- Built cost calculator (`nerv-deploy/tools/cost-calculator.py`)
- Modeled 1x through 100x usage, all provider tiers, smart routing scenarios
- mini-Moby fact-checked, 6 caveats analyzed and addressed
- Drawing analysis modeled as #1 cost driver (Nick's input) — up to 1,000/day
- Even worst case (1,000 drawings/day, Sonnet 4): 80% margin at $3,500/mo
- Full doc: `NERV-DOCS/API-COST-ANALYSIS.md`

### Client Communication Architecture — LOCKED
- Three lanes: Email (stateless), Telegram (real-time), NERV Web Portal (dashboard)
- All hit same NERV database

### Cloudflare Tunnel — LIVE
- Installed cloudflared, authed with Nick's Cloudflare account
- Domain purchased: **nerv-command.com** ($10/year)
- Tunnel created + DNS routed + systemd service enabled
- **https://nerv-command.com is live and working from mobile**
- Service: `cloudflared-nerv.service` (auto-start, auto-restart)

### Token Guardian — BUILT & PUSHED ✅ (webchat evening session)
- `services/token-guardian/` — FastAPI on port 8091
- AES-256-GCM encrypted token storage, proactive refresh at 75% lifetime
- 5-min cron sweep, atomic refresh locks, Telegram alerting
- Webhook receiver updated to fetch tokens from Token Guardian
- DB migration 003: `oauth_tokens` + `oauth_refresh_log`
- Commit: `ef6a13a`

### EVA Sentry v1 — BUILT & PUSHED ✅ (webchat evening session)
- `services/eva-sentry/` — FastAPI on port 8092
- Core scanner: text (prompt injection, malware), files (ext, MIME, hash, content), commands (risk classification)
- Email ingest (IMAP polling) + Procore ingest (via Token Guardian)
- Hot-reloadable policy, verdict caching, scan stats
- Webhook receiver now screens ALL inbound data through Sentry before DB write
- Fail-open: Sentry down = data flows but logged. Deny/quarantine = blocked.
- Commit: `02a584a`

### Smartsheet Adapter — BUILT & PUSHED ✅ (webchat evening session)
- `services/smartsheet-adapter/` — FastAPI on port 8093
- Async Smartsheet REST client (no SDK dep), bidirectional sync engine
- Flexible column mapping (JSON config per client), 5 sheet types supported
- Background polling sync + Smartsheet webhook support for real-time
- Row-level version tracking, conflict detection, sync audit log
- DB migration 004: smartsheet_mappings, smartsheet_row_map, smartsheet_sync_log
- Commit: `4db1b1b`

### Portal Auth — BUILT & PUSHED ✅ (webchat evening session)
- `services/portal-auth/` — FastAPI on port 8094
- bcrypt passwords, SHA-256 session tokens, 72h sessions
- 5 roles: admin, owner, pm, field, viewer + per-project access control
- Rate limiting (5 attempts / 15 min lockout), audit trail
- Admin bootstrap from env vars, inter-service token validation endpoint
- DB migration 005: portal_users, portal_sessions, portal_auth_log
- Commit: `d8e467d`

### Portal UI Updates — BUILT & PUSHED ✅ (webchat evening session)
- Login page (login.html) — NERV-themed, auth proxy routes in server.py
- Mobile responsive: enhanced breakpoints, touch-friendly, iOS zoom prevention
- New APIs: /api/webhook-stats, /api/search, /api/services (health dashboard)
- Auth-aware main UI: user info in header, logout, configurable AUTH_ENABLED
- Commit: `6224613`

### Smartsheet Live API Test — VERIFIED ✅ (webchat evening)
- Connected to real Smartsheet Business account (Poinciana Crossing project)
- Read 13 sheets, 1,330 rows, all column types
- Write test: created sheet, added rows, verified, cleaned up
- Sentry: 31 rows scanned, 0 false positives on real construction data  
- Webhook: verification challenge via nerv-command.com confirmed
- Token saved to `.credentials/smartsheet.env`
- Added `shop_drawing` to document_type enum

### mini-Moby Audit Fixes — ALL RESOLVED ✅
- Auth ON by default
- Watchdog service (health monitor + Telegram alerts)
- Self-service password reset + change-own-password endpoints
- Secrets management docs
- Commit: 959a354

## Midnight 2026-02-26 — Docker Stack Validated ✅
- All 8 custom services build + start + pass health checks
- Fixed 3 bugs: missing python-multipart, missing /health endpoint, seed.sql ordering
- Fixed stale migration 002 (document_chunks schema mismatch)
- Commit: `fbef676` pushed to GitHub
- Only blocker: `openclaw` container image doesn't exist yet (placeholder)

## NAP 02.25 — ALL 5 TASKS COMPLETE ✅
1. OpenClaw updated to 2026.2.25
2. mini-Moby delegated for audit + security fixes
3. Docker full-stack test — report PDF emailed to Nick
4. Client portal (1,125 lines) + onboarding wizard live at nerv-command.com
5. 8 audit findings fixed (all Critical + High) — grade C+ → ~B+

## Live URLs
- https://nerv-command.com/portal — Client Portal prototype
- https://nerv-command.com/onboarding — Client Onboarding Wizard

## Pending
- ~~Docker compose full stack test~~ ✅
- ~~Client onboarding wizard~~ ✅
- ~~Client portal design~~ ✅
- ~~Security audit remediation (Critical/High)~~ ✅
- Smartsheet adapter functional testing
- End-to-end integration test with real Procore sandbox
- Client portal: replace mock data with real API calls
- Mobile UI polish (field-guy testing)
- Remaining audit items (18 MEDIUM/LOW findings)
- Branding decision (NERV = internal codename, final name TBD)
- Client deployment playbook formalization
- Demo package for sales meetings

## Market Intel — SAVE THIS
- Lunch with Shell concrete VP + Miller precon VP + estimators
- Miller has CRM, doesn't use it. Relies on "excel on steroids" (Smartsheet now)
- Shell VP had Outlook plugin sales pitch — rules-based, no AI, heard AI coming
- Shell VP said "the future is agentic AI" + "would work with the excel on steroids"
- **These are our exact target customers describing exactly what we're building**
- Miller Smartsheet = potential internal pilot opportunity
