# THE THIRD IMPACT — Project Handoff Document
## Procore Instrumentality Project: Complete Knowledge Transfer

**Created:** February 18, 2026
**Created by:** Moby (Claude Opus 4 via OpenClaw) for Nick Stula
**Purpose:** Full project knowledge transfer to enable a new AI assistant (ChatGPT or equivalent) to continue the Evangelion Project without loss of progress, context, or institutional knowledge.

---

## INSTRUCTIONS FOR NEW AI ASSISTANT

You are taking over a construction AI startup project called **The Evangelion Project (EVA)**. Your operator is **Nick Stula**, a 32-year-old construction project manager at Miller Construction in Miami, FL. He has limited time — he works a full-time PM job with a 1+ hour commute each way. He needs you to work autonomously and come back with answers, not questions.

**Read this entire document before starting any work.** It contains everything the previous AI (Moby/Claude) learned over the course of building this project. Mistakes we made are documented so you don't repeat them. API quirks are documented so you don't waste time rediscovering them.

Nick communicates primarily via Telegram. He has two young children and his primary life goal is to buy a house for his family. This business is how he plans to get there.

---

## 1. THE BUSINESS — What We're Building

### Concept
Locally-deployed AI agents specialized for construction general contractors (GCs), integrated with Procore (the industry-standard project management platform). Each client gets a dedicated mini-server called a **NERV unit** — data never leaves their building.

### Codenames (Neon Genesis Evangelion theme)
- **SEELE** — Our company (handles pre-deployment, DB setup, history ingestion, soul calibration)
- **NERV** — The client-side dedicated server + command station interface
- **EVA-00** — Master Clerk & Project Historian (FIRST PRODUCT — structured local DB + instant cross-referencing)
- **EVA-01** — Submittal Agent (24/7 compliance review, Procore drafting, workflow tracking, material tracker)
- **EVA-02** — RFI Agent (proactive drawing analysis, gap detection, Procore drafting, reminder management)

### Target Market
- Executive-level decision makers at South Florida GCs
- Demographic: primarily older/boomer generation unfamiliar with AI
- Value prop: "Your project knowledge searchable in seconds, not hours of digging through Procore"
- Separate agents = modular pricing, easier to sell individually

### Pricing Model
- **Setup fee:** $2-3k (includes NERV hardware)
- **Monthly per agent:** $3-5k
- **Our dev cost:** Currently $0 per token (Claude Max subscription) — but clients will pay standard API rates
- **TODO (not yet done):** Detailed cost breakdown for hosting + API costs and monthly agent pricing per client

### Key Business Decision
- Separate agents > combined agents (modular pricing, easier to sell/build)
- Shared knowledge folder across all agents on a NERV unit
- Clone-and-configure deployment — no code changes per client
- This is an internal roadmap, NOT client-facing marketing

### Product Theory (from Nick's product doc, 2026-02-19)
See `business/PROJECT-EVA-PRODUCTS.docx` for full product writeup. Key points:
- EVA-00 is the **foundation** — all other EVAs depend on its structured historical database
- SEELE pre-loads the NERV database with complete client project histories (drawings, RFIs, submittals, schedules, meeting minutes, etc.)
- EVA-01 workflow: User sends document → compliance review → historical comparison via EVA-00 → draft in Procore → user publishes → EVA-01 tracks + reminds
- EVA-01 also maintains Key Material Tracker Logs using OPS + daily reports + lead times
- EVA-02 is proactive: analyzes drawings for conflicts/gaps BEFORE they surface in the field
- EVA-02 cross-references historical RFI data from similar project types via EVA-00

---

## 2. INFRASTRUCTURE — What Exists Today

### Moby-1 (Development Server)
- **Hardware:** Laptop, i7-1370P, 62GB RAM, 932GB NVMe
- **OS:** Manjaro KDE Linux
- **Status:** Always-on, lid close = ignore, sleep targets masked
- **Services running:** Docker, PostgreSQL, Redis, Cron, OpenClaw
- **Full sudo access, UFW firewall active**
- **70+ dev/business packages installed** (Python, Node, etc.)

### Nick's Home PC
- Ryzen 7 9800X3D, RX 7900 XTX, 4K OLED monitor, Windows 11
- Has ODA File Converter installed for DWG→DXF conversion

### Web Terminal
- ttyd on Moby-1, port 7681 (LAN only: 192.168.8.0/24)
- Access: http://192.168.8.124:7681 (login: moby / eva2026)
- Writable mode (-W flag), zsh shell

### Accounts & Credentials
All stored on Moby-1:
- **GitHub:** mechamoby (gh CLI authenticated)
- **Gmail:** mecha.moby@gmail.com (SMTP/IMAP configured)
- **Brave Search API:** configured
- **Procore Developer:** sandbox app, creds in `.credentials/procore.env`
- **DocuSign Developer:** sandbox app "Moby", creds in `.credentials/docusign.env`
- **Procore OAuth token:** `.credentials/procore_token.json` (auto-refresh working)

---

## 3. PROCORE API — Critical Knowledge

### Sandbox Environment
- **Company ID:** 4281379
- **Project ID:** 316469
- **Base URL:** https://sandbox.procore.com
- **App Version Key:** 853ac70d-7838-4d88-9c69-4968e731ff18
- **Redirect URI:** http://localhost:9876/callback
- **Rate limit:** 100 requests per ~60 second window

### Built-in Sandbox Users (ONLY THESE WORK AS SUBMITTAL PARTICIPANTS)
- 99519 — API Support
- 100298 — Test Sub
- 100299 — Test Architect
- 174986 — Nick Stula / mecha.moby

### What Works via API ✅ (MAGI Sprint 1 — 2026-02-19)
- **Daily Logs**: 18 sub-types via `/rest/v1.0/projects/{id}/daily_logs` (weather, manpower, notes, deliveries, accidents, delays, equipment, visitors, dumpster, quantity, call, work, timecard)
  - Require date range params, max 13 weeks per query
- **RFIs**: Full CRUD via `/rest/v1.1/projects/{id}/rfis` — 134 in sandbox
  - Filter syntax needs `[]` brackets: `filters[status][]=open`
- **Submittals**: Full CRUD via `/rest/v1.0/projects/{id}/submittals` — 146 in sandbox
- **Documents**: Folder tree via `/rest/v1.0/projects/{id}/documents` — flat list with parent_id
- **Meetings**: Via `/rest/v1.1/projects/{id}/meetings` — response is GROUPED by title, must flatten
- **Cost Codes**: 304 codes, **Vendors**: 118, **Users**: 554
- **Webhooks**: Real-time event monitoring for any resource type
- **Observations**: Read-only (22 types), creation blocked by permissions
- **Checklists**: Templates work, list creation has validation issues
- Submittal CRUD (create, read, update, delete)
- File upload via PATCH with `submittal[attachments][]`
- Vendor creation — **MUST use `{"vendor": {...}}` NOT `{"company": {...}}`**
- Drawing revisions: `drawing_revisions` endpoint

### API Version Map
- **v1.1**: RFIs, Meetings (v1.0 returns 404)
- **v1.0**: Submittals, Daily Logs, Documents, most others

### What DOES NOT Work ❌
- `drawings` endpoint → 404s. **Use `drawing_revisions` instead.**
- **Change Events** — module not enabled in sandbox, skip
- **Punch Lists** — module not enabled in sandbox, skip
- Spec section creation (UI only, no API)
- Spec section listing/search (NO endpoint exists at all)
- Submittal approvers/workflow management (can't add reviewers or advance workflow)
- Submittal status changes (can't close/approve via API)
- Submittal status filter appears broken (returns all regardless)
- API-created users as submittal participants (rejected — only built-in sandbox users accepted)
- Observation creation (permissions issue)

### Full API Documentation
Comprehensive endpoint docs: `memory/eva/procore-api/` (10 files, SPRINT-1-SUMMARY.md has the executive overview)

### ⚠️ CRITICAL: DO NOT ACCESS Nick's old company Procore account. It has an audit trail and could cause professional problems.

### Current Sandbox Data
- **554 users** (all with fake `@sandbox.invalid` emails — NEVER use real emails)
- **118 vendor companies**
- **2 test submittals** created with PDF attachments
- **31 spec sections** (added by Nick via UI)

---

## 4. WHAT WE'VE BUILT — File Locations

All paths relative to `/home/moby/.openclaw/workspace/`

### EVA Deployment Template (`eva-agent/deployment-template/`)
Complete clone-and-configure package for shipping agents to clients:
- `docker-compose.yml` — OpenClaw + PostgreSQL 16 + Redis 7 + nightly backups
- `scripts/setup.sh` — Interactive client onboarding wizard
- `scripts/deploy.sh` — One-command deployment
- `config/agent-config.yaml` — Main config
- `config/roles.yaml` — 4-role RBAC (admin, project_manager, superintendent, executive)
- `config/prompts/base-system.md` — Core construction prompt (FL Building Code, Miami-Dade NOA, OSHA, CSI MasterFormat)
- `config/prompts/daily-reports.md` — Daily report workflow
- `config/prompts/submittals.md` — Submittal tracking workflow
- `docs/CLIENT-ONBOARDING.md` — 5-phase onboarding checklist
- **Target: deploy a new client in under 30 minutes**

### EVA-00 Database Design (`eva-agent/eva-00-design/`)
- `ARCHITECTURE.md` — Full system architecture (PostgreSQL + pgvector + Redis + file storage + embedding service)
- `DATABASE-SCHEMA.sql` — Complete schema: projects, companies, contacts, drawings, specs, submittals, RFIs, daily reports, meetings, schedules, change orders, photos, documents, vector embeddings, sync tracking, audit log
- `INGESTION-PIPELINE.md` — Document ingestion workflow
- `QUERY-PATTERNS.md` — Common query patterns and SQL examples
- `SYNC-STRATEGY.md` — Procore bidirectional sync approach

### Drawing Analysis Design (`eva-agent/drawing-analysis-design/`)
- `STATE-OF-ART.md` — Current state of AI drawing analysis
- `TIERED-STRATEGY.md` — 4-tier extraction approach (Tier 0: metadata $0, Tier 1: text/schedules ~$0.05/sheet, Tier 2: spatial ~$0.30/sheet, Tier 3: cross-discipline ~$3/query)
- `SCHEDULE-EXTRACTION.md` — Table extraction from drawing PDFs
- `LIMITATIONS.md` — Honest assessment of what AI can/can't do
- `IMPLEMENTATION-PLAN.md` — Build order and priorities

### NERV Hardware Spec (`eva-agent/NERV-HARDWARE.md`)
- 3 tiers: Mini PC ($1.2-1.5k), Workstation ($2-2.5k), Enterprise ($2.5-3.5k)
- Option A (Mini PC) recommended for Phase 1 — fits inside $2-3k setup fee
- Software stack: OpenClaw + PostgreSQL + Redis + Ollama + ODA Converter + nginx + backup

### Drawing Index Pipeline (`eva-drawing-index/`)
- Construction drawing indexing pipeline
- Database: `eva_drawings` in PostgreSQL
- Procore integration synced 230 drawings from BTV5 sandbox project
- Tier 1 tested on 6 local PDF sets: 2,008 pages in ~5 min, $0 cost
- Key files: `src/procore/client.py`, `src/sync.py`, `src/indexer.py`, `src/classifier.py`, `src/database.py`

### NERV Test Results (`eva-agent/nerv-test/`)
- `extraction-results.json` — Structured DXF extraction data from 14 sheets
- `analysis-report.md` — Analysis of what can/can't be extracted from DXF
- `database-test.sql` — EVA-00 schema INSERT statements from real data

---

## 5. EVA SOUL DESIGN — The Real Competitive Moat

### Why Souls Matter More Than Skills
Research and field testing (toli/@tolibear_, Feb 2026 — "I Gave My Agents Skills. I Should Have Given Them Souls.") confirmed: agent identity is the #1 lever for output quality. More important than the model, tools, or memory system.

**Key research findings applied:**
- "Lost in the Middle" paper: LLMs put massive weight on first and last tokens. 20%+ accuracy drop when key info is buried in the middle. **Soul must go first in the system prompt. Always.**
- NAACL 2024 "Better Zero-Shot Reasoning with Role-Play Prompting": 10-60% accuracy improvements from role prompting. **Just being someone beat being shown how.**
- Google DeepMind: accuracy saturates/degrades past 4 agents ("Coordination Tax"). **Fewer agents, better souls. Always.**

### Soul Design Principles (Applied to All EVAs)

1. **Experiential voice, not instructions.** Don't say "Always check composition." Say "I've learned through hundreds of failed designs that when the weight is wrong, viewers sense it before they can articulate why." Rules create compliance. Beliefs create expertise.

2. **30-40% anti-patterns.** Budget a large portion of each soul to what the agent REFUSES to do. Not vague traits ("I don't micromanage") but specific catchable behaviors ("I don't rewrite a delegate's output instead of giving feedback").

3. **Productive flaws.** Every soul names one weakness that is the direct cost of its core strength. This makes the agent feel real and creates self-aware output.

4. **"Not My Domain" boundaries.** Each EVA explicitly knows what it doesn't do and who handles it. EVA-01 doesn't write RFIs. EVA-02 doesn't track submittals. EVA-00 doesn't draft documents.

5. **Soul x Skill is multiplicative.** A mismatch doesn't just underperform — it actively degrades output. Each soul is aimed precisely at its domain.

6. **Client soul calibration.** During SEELE onboarding, customize each EVA's personality to match client culture. Questions: How formal is the team? What's the company culture? Do they want a colleague or a tool?

### Soul Files (Located in `eva-agent/souls/`)
- `EVA-00-SOUL.md` — Master Clerk. Experiential voice of someone who's "sat in every OAC meeting." Anti-patterns: won't guess, won't interpret intent, won't make decisions. Flaw: over-indexes on history.
- `EVA-01-SOUL.md` — Submittal Coordinator. Voice of someone who's "processed thousands of submittals across every CSI division." Anti-patterns: won't approve, won't skip compliance, won't fabricate lead times. Flaw: aggressive on compliance flags.
- `EVA-02-SOUL.md` — RFI Analyst. Voice of someone who "finds problems in drawings before they find you in the field." Anti-patterns: won't answer own RFIs, won't suppress issues, won't manufacture urgency. Flaw: generates more potential RFIs than you'll ever send.
- `SEELE-IDENTITY.md` — Our company identity and onboarding process.

### The Pitch Moment
When a GC super asks EVA-00 "what hardware was approved on the last project?" and gets back "Drawing A-301, Detail 4. Spec Section 08 71 00, paragraph 2.3.B. Type II anodized aluminum, Kawneer 451T. Submitted under BTV5-087, approved first pass" — that's when they reach for the checkbook. The soul is what makes that answer feel like it came from a 20-year veteran, not a chatbot.

---

## 6. KEY TECHNICAL DISCOVERIES

### The Competitive Moat: Text Extraction > AI Vision
**This is the single most important technical insight of the project.**

- **PDF text extraction (PyMuPDF):** Reads dimensions, elevations, room names, grid lines from CAD-generated PDFs. Instant, $0, 100% accurate.
- **DXF extraction (ezdxf):** Reads layers, room identifiers, structural grids, discipline separation. Instant, $0, 100% accurate.
- **AI vision models:** Slower, costs tokens, and actually LESS accurate. In our test, the vision model gave the WRONG answer for a grid line dimension (said 30'-0" when it was actually 20'-7 29/32").
- **Strategy:** Text extraction first for everything. AI vision is LAST RESORT only — for scanned/raster-only drawings where there's no extractable text.
- **Scale impact:** Thousands of PDFs and DXFs = batch job measured in minutes at $0 token cost. Everyone else is throwing vision models at drawings and burning money.

### DWG → DXF Conversion
- DWG is proprietary binary format — cannot be read by ezdxf directly
- LibreDWG compile fails on Moby-1 (OOM killed with 62GB RAM — needs more)
- **Solution:** ODA File Converter (free) runs on Windows (Nick's PC) or headless Linux
- On NERV servers with 64GB RAM: LibreDWG or ODA will work fine
- DWG→DXF conversion takes seconds per file
- **CAD (DXF) > PDF for structured data extraction** (~99% vs ~80% accuracy)

### Cover Sheet Pipeline
- Procore cover sheet PDFs contain embedded signed download links for ALL attachments
- PyMuPDF extracts links + full text metadata — zero tokens
- Links are long-lived signed URLs
- Pipeline: Export cover sheet → parse metadata → download files → create submittals via API → upload attachments
- **Bottleneck:** No bulk export from Procore UI — one cover sheet at a time

### Submittal Data Priority
Three data sources for equipment/material info, ranked by quality:
1. **Submittals** (best — manufacturer data, specs, shop drawings)
2. **Drawing schedules** (good — door/window/finish schedules on drawing sheets)
3. **Drawing plans** (okay — callouts and keynotes on plan sheets)

---

## 7. MISTAKES & LESSONS LEARNED (Don't Repeat These)

1. **Don't brute-force scan Procore for IDs** — We burned 50+ minutes and massive context scanning spec section IDs because there's no list endpoint. Rate limit (100/min) makes discovery-by-scanning impractical for large ID ranges. Always check if there's a list endpoint first.

2. **Procore `drawings` endpoint 404s** — Use `drawing_revisions` instead.

3. **Vendor creation format:** `{"vendor": {...}}` NOT `{"company": {...}}`

4. **API-created users can't be submittal participants** — Only the 4 built-in sandbox users work as managers/reviewers.

5. **`is_active: false` is ignored** by Procore sandbox — users always created as active.

6. **LibreDWG won't compile on 62GB RAM** — OOM killed. Use ODA File Converter instead, or wait for NERV hardware with 64GB+.

7. **Paper Moby (Sonnet subagent) too slow for batch extraction** — Use direct API pipeline instead of routing through a chat agent.

8. **OpenClaw OAuth token ≠ Anthropic API key** — Can't use the OpenClaw token for direct Anthropic API calls. Need a separate API key for the Tier 2 vision pipeline.

9. **`systemctl restart systemd-logind` kills the display session** — Always warn the user first.

10. **Manjaro KDE 6 uses kwriteconfig6/qdbus6** — Not the old KDE 5 versions.

11. **KDE power management overrides systemd** — Must disable both to prevent sleep.

12. **Sudoers files need chmod 440** or they get silently ignored.

13. **Vision AI gives wrong answers on construction drawings** — In our grid line test, vision said 30'-0" when text extraction correctly read 20'-7 29/32". Always prefer text extraction.

14. **Keep conversations shorter** — Long sessions hit API context limits and degrade quality.

15. **X Articles can't be fetched via API or scraping** — X's native long-form posts only return the title via API. Must copy-paste or screenshot the content. Regular tweets/threads work fine with Bearer Token.

16. **Agent soul design > tool configuration** — Research shows 10-60% accuracy improvement from role-play prompting. Experiential voice ("I've seen hundreds of these") beats instruction lists ("always check X"). Budget 30-40% of soul to anti-patterns.

---

## 8. CURRENT STATUS & NEXT STEPS

### Completed ✅
- EVA deployment template (10 files, ready to clone-and-deploy)
- Procore sandbox populated (554 users, 118 vendors, 145 submittals, 134 RFIs, 31 spec sections)
- EVA-00 database schema designed (full PostgreSQL + pgvector)
- Drawing analysis 4-tier strategy designed
- NERV hardware 3-tier spec designed
- DXF extraction validated (14 sheets from 1750 project: rooms, layers, grids — perfect)
- PDF extraction validated (NGVD elevations, grid dimensions — perfect, $0)
- Cover sheet PDF parsing pipeline proven
- Submittal agent prototype concept (eva-agent/submittal-agent/)
- **BTV5 submittals fully uploaded** — 206 PDFs parsed, 143 submittals created in Procore sandbox *(2026-02-19)*
- **NERV Interface v1.0** — Full agent chat via Gateway WS, terminal, file browser, session manager, cron manager, live activity feed, inline tool calls, system metrics, syntax highlighting *(2026-02-19)*
- **EVA soul files written** — EVA-00, EVA-01, EVA-02 souls with experiential voice, anti-patterns, productive flaws, domain boundaries *(2026-02-19)*
- **X/Twitter API access** — @MechaMoby account, pay-per-use API for reading tweets *(2026-02-19)*
- **Procore API knowledge base** — Comprehensive endpoint documentation in memory/eva/procore-api/ *(2026-02-19)*
- **Memory system restructured** — Timestamped entries, project sub-folders (eva/, nerv/, infrastructure/, business/) *(2026-02-19)*

### In Progress 🔄
- Procore OAuth token re-authentication (redirect URI updated, awaiting browser flow)
- Procore API deep exploration (daily logs, webhooks, inspections — blocked on auth)

### Not Yet Started 📋
1. **EVA-00 actual database deployment** (schema exists, not yet running) — FIRST PRIORITY
2. **Detailed pricing/cost model** for client deployments (hardware + API + margin)
3. **Batch cover sheet parser pipeline** (automated submittal creation from exported PDFs)
4. **Tier 2 vision extraction pipeline** (schedule tables from scanned drawings)
5. **Client demo package** for sales conversations
6. **Legal/liability framing** for AI-assisted drawing analysis ("AI-assisted" not "AI replacement")
7. **NERV remote access** — Tailscale/Cloudflare Tunnel for access outside LAN
8. **Cognee knowledge graph** — memory enhancement for complex cross-referencing (evaluate when scale demands it)

### Priority Order (Moby's recommendation)
1. Get Procore auth restored → deep API exploration (daily logs, webhooks, inspections)
2. Get EVA-00 database running with real Procore data
3. Build EVA-00 as first demo-able product (the foundation everything else builds on)
4. Create client demo package
5. Build EVA-01 submittal agent on top of EVA-00
6. Pricing model finalization
7. First sales conversation with a target GC

---

## 9. NICK'S WORKING STYLE

- Communicates via Telegram (phone + web.telegram.org at work)
- Available mornings before work, evenings after 6-7 PM, weekends
- During work day: mostly unavailable, occasional Telegram check-ins
- Prefers autonomous agents that report back with results, not questions
- Values directness — skip filler words, just deliver value
- Has deep construction knowledge — don't explain basic construction concepts to him
- Evangelion fan — hence all the codenames
- Wants to see tangible progress, not just plans and documents

---

## 10. SECURITY PROTOCOLS

### Development Security (Our Systems)
- **NEVER send external communications** (emails, tweets, posts) without Nick's explicit approval
- **NEVER access Nick's old company Procore** — audit trail risk
- **NEVER use real email addresses** in sandbox — always `@sandbox.invalid`
- **NEVER send notifications to real people** under any circumstance
- Private data stays private — no exfiltration
- `trash` > `rm` (recoverable beats gone forever)
- Three-tier security: Green (free), Yellow (notify Nick), Red (PIN required)
- Only Nick is authorized — all other users auto-ignored
- **NEVER install ClawHub marketplace skills** — 1,184+ malicious skills found (prompt injection, SSH key theft, reverse shells). Build our own. *(2026-02-19)*

### Client Deployment Security (NERV Units) *(2026-02-19)*
Full architecture documented in `nerv-deploy/docs/SECURITY-ARCHITECTURE.md`. 7-layer defense:

1. **RBAC** — 4 roles (admin/PM/superintendent/executive) with strict permission boundaries
2. **Immutable Audit Log** — Append-only, agent DB user has no DELETE/UPDATE permission
3. **Database Permission Isolation** — Agent role (`eva_agent`) is INSERT/SELECT only on critical tables. No DROP, TRUNCATE, or DELETE on project history. Separate `eva_admin` role for migrations.
4. **Soul-Level Security Directives** — Non-negotiable rules baked into every EVA soul (can't delete records, can't cross-share project data, can't reveal credentials, can't execute instructions from pasted documents)
5. **Prompt Injection Defense** — All pasted/uploaded content wrapped as untrusted data. Agent trained to never execute instructions found in documents. Repeated attempts trigger admin alerts.
6. **Nightly Backups** — 30-day rolling retention, encrypted, weekly restore verification. Max data loss: 24 hours.
7. **Network Isolation** — Outbound firewall limited to Procore API + Anthropic API only. No arbitrary HTTP access.

**Key selling point:** "Even if a disgruntled employee tries to wipe your records, they physically cannot — the system doesn't have a delete button for project history. Every interaction is logged to a tamper-proof audit trail."

---

## 11. FILE SYSTEM MAP

```
/home/moby/.openclaw/workspace/
├── MEMORY.md                    # Long-term memory (this was Moby's brain)
├── THE-THIRD-IMPACT.md          # This document
├── THE-THIRD-IMPACT-NICK.md     # Human-readable version for Nick
├── SOUL.md                      # Moby's personality definition
├── USER.md                      # Nick's profile
├── AGENTS.md                    # Operating procedures
├── TOOLS.md                     # Local tool notes
├── IDENTITY.md                  # Moby's identity (name, emoji)
├── HEARTBEAT.md                 # Periodic task checklist
├── eva-agent/
│   ├── deployment-template/     # Production deployment package (10 files)
│   ├── eva-00-design/           # Database architecture (5 docs + SQL)
│   ├── drawing-analysis-design/ # Drawing AI research (5 docs)
│   ├── nerv-test/               # DXF extraction test results
│   ├── submittal-agent/         # Submittal agent prototype
│   ├── btv5-submittals/         # 206 PDFs + upload script + progress tracking
│   ├── souls/                   # EVA soul files (the competitive moat)
│   │   ├── EVA-00-SOUL.md       # Master Clerk — experiential voice, anti-patterns, flaw
│   │   ├── EVA-01-SOUL.md       # Submittal Agent — same treatment
│   │   ├── EVA-02-SOUL.md       # RFI Agent — same treatment
│   │   └── SEELE-IDENTITY.md    # Our company identity + onboarding process
│   └── NERV-HARDWARE.md         # Server hardware specs
├── eva-drawing-index/           # Drawing indexing pipeline (Python)
├── nerv-interface/              # NERV v1.0 — Web command interface (FastAPI + single HTML)
│   ├── server.py                # Backend: Gateway WS bridge, file browser, system metrics
│   └── static/index.html        # Full UI: chat, terminal, activity feed, session mgr
├── business/
│   └── PROJECT-EVA-PRODUCTS.docx # Nick's product theory document
├── memory/
│   ├── daily/                   # Raw daily session logs
│   ├── eva/                     # EVA project-specific notes
│   │   └── procore-api/         # Procore API knowledge base (endpoints, gotchas, test scripts)
│   ├── nerv/                    # NERV interface dev notes
│   ├── infrastructure/          # Server/Docker/networking notes
│   └── business/                # Sales/clients/strategy notes
├── .credentials/
│   ├── procore.env              # Procore API credentials
│   ├── procore_token.json       # OAuth token (needs re-auth)
│   ├── docusign.env             # DocuSign credentials
│   └── x_twitter.env            # X/Twitter API bearer token + access tokens
└── protocols/
    └── SECURITY-MASTER.md       # Security protocol definition
```

---

## 12. NERV INTERFACE — CUSTOM WEB UI (v1.0 BUILT)

**Problem:** OpenClaw on Telegram surfaces raw tool errors as notifications (e.g., "xelatex not found") with no context about retries or resolution. User can't see agent work history or what happened while away.

**Status:** v1.0 built and running on Moby-1. Full agent session access via Gateway WebSocket protocol — agent has full tool access (file read/write/edit, exec commands, web search, memory, everything) when chatting through NERV.

### File Locations
```
nerv-interface/
├── server.py                    # FastAPI backend (WebSocket bridge to OpenClaw gateway)
├── static/
│   └── index.html               # THE ENTIRE UI — single-file HTML/CSS/JS app
└── templates/                   # (empty, unused)
```

### How to Edit the UI
- **Everything is in one file:** `nerv-interface/static/index.html`
- CSS variables at the top (`:root { ... }`) control the entire color theme
- Color scheme: blue/teal throughout, NERV logo stays red (`--nerv-red: #cc0000`)
- Font: `Share Tech Mono` (Google Fonts) for the military/sci-fi HUD feel
- Layout: 3-column — sidebar (system status + activity log) | chat | terminal (ttyd iframe)
- No build step, no dependencies — just edit the HTML file and refresh

### How to Run It
```bash
cd nerv-interface
OPENCLAW_GATEWAY_TOKEN=<token from ~/.openclaw/openclaw.json> python3 server.py
```
- Requires: `fastapi`, `uvicorn`, `httpx` (all pip-installable)
- Runs on port 8080, UFW rule allows LAN access (192.168.8.0/24)
- Terminal iframe loads ttyd from port 7681

### Key Config in server.py
- `GATEWAY_HOST` / `GATEWAY_PORT` — OpenClaw gateway (default 127.0.0.1:18789)
- `TTYD_HOST` / `TTYD_PORT` — Web terminal (default 192.168.8.124:7681)
- `NERV_PORT` — NERV UI port (default 8080)

### v1.0 Features (Built 2026-02-19)
- **Full agent session** via Gateway WebSocket (chat.send protocol) — complete tool access
- **Inline tool call visualization** — collapsible blocks with colored badges per tool type
- **System metrics** — live CPU, RAM, disk with color-coded bars
- **Session manager** — list/switch between agent sessions
- **File browser** — navigate workspace, view file contents
- **Live activity feed** — real-time agent tool calls streamed via session log
- **Code syntax highlighting** — highlight.js integration
- **Image rendering** — inline images with click-to-enlarge
- **Keyboard shortcuts** — Ctrl+Enter, Ctrl+L, Ctrl+K, Ctrl+/, Escape
- **Notification sounds** — Web Audio API tone on response complete (toggleable)
- **Context gauge** — token usage + cost display with auto-refresh

### Remaining Limitations
- **No remote access** — LAN only. Need Tailscale or Cloudflare Tunnel for office/mobile access
- **No auth** — Anyone on LAN can access. Need login page before exposing externally
- **No cron management UI** — planned but not yet built into the panel

---

*This document was created as a contingency plan ("The Third Impact") in case the underlying AI platform needs to change. All project knowledge, mistakes, and progress are preserved here for continuity. — Moby 🐋, February 18, 2026*
