# MEMORY.md - Moby's Long-Term Memory
> Last curated: 2026-02-19

## Nick Stula — The Boss
- 32yo, married, 2 babies, lives in Miami *(since 2026-02-16)*
- PM at Miller Construction (1+ hr commute), project waiting on permits
- 6 years GC side (multi-family), several years real estate dev before that
- Primary goal: buy a house for his family
- Communicates via Telegram (phone + web.telegram.org at work)
- Limited time — needs Moby working autonomously behind the scenes

## The Evangelion Project (EVA)
- Selling locally-deployed AI agents specialized for construction *(since 2026-02-16)*
- Each client gets dedicated NERV server (data never leaves their building)
- SEELE = our company codename (handles pre-deployment, DB setup, history ingestion)
- Target: executive-level boomers at South Florida GCs
- Pricing: $2-3k setup + $3-5k/month per agent
- No existing OpenClaw construction plugins = first mover advantage
- **EVA-00** (FIRST PRODUCT): Master Clerk & Project Historian — structured local DB of all client history, instant cross-referencing *(2026-02-19)*
- **EVA-01**: Submittal Agent — compliance review, Procore drafting, workflow tracking, material tracker
- **EVA-02**: RFI Agent — proactive drawing analysis, gap detection, Procore drafting, reminder management
- Full product theory: business/PROJECT-EVA-PRODUCTS.docx + memory/eva/product-lineup.md

## Infrastructure (Moby-1 Laptop)
- Manjaro KDE, i7-1370P, 62GB RAM, 932GB NVMe *(since 2026-02-16)*
- Always-on (lid close = ignore, sleep targets masked)
- Full sudo access, UFW firewall active
- Docker, PostgreSQL, Redis, Cron running
- 70+ dev/business packages installed

## Accounts & Keys
- GitHub: mechamoby (gh CLI auth'd) *(since 2026-02-16)*
- Gmail: mecha.moby@gmail.com (SMTP/IMAP configured)
- Brave Search API: configured
- Procore Dev: sandbox app, creds in .credentials/procore.env
- DocuSign Dev: sandbox app "Moby", creds in .credentials/docusign.env
- Telegram bot: connected and working
- X/Twitter: @MechaMoby, API pay-per-use, creds in .credentials/x_twitter.env *(2026-02-19)*

## Security
- Master protocol: protocols/SECURITY-MASTER.md *(since 2026-02-17)*
- PIN stored in .security-pin (chmod 600)
- Three tiers: Green (free), Yellow (notify), Red (PIN required)
- Only Nick authorized, all others auto-ignored
- Never send external comms without approval

## EVA Drawing Index (`eva-drawing-index/`)
- Construction drawing indexing pipeline — Procore API is primary data source *(since 2026-02-17)*
- Database: `eva_drawings` in PostgreSQL
- Procore gives us pre-rendered PNGs, pre-classified by discipline — eliminates 80% of Tier 1
- BTV5 fully synced from Procore sandbox: 230 drawings, 486MB PNGs on local disk
- Tier 1 also tested on 6 local PDF sets: 2,008 pages in ~5 min, $0 cost
- Tier 2 (vision extraction of schedule pages) still needs building
- Submittal parsing is higher priority than drawing vision — easier docs, richer data
- Three data sources for equipment info: Submittals (best) → Drawing schedules → Drawing plans
- Key files: src/procore/client.py, src/sync.py, src/indexer.py, src/classifier.py, src/database.py

## BTV5 Submittals (`eva-agent/btv5-submittals/`)
- 206 PDFs downloaded, 143 unique submittals, 44 with revisions up to R4 *(2026-02-19)*
- All 143 uploaded to Procore sandbox — 0 failures
- Attachments skipped (sandbox silently drops them)
- Upload script: `eva-agent/btv5-submittals/upload_submittals.py`

## Procore API Access
- Sandbox working: Company ID 4281379, Project ID 316469 *(since 2026-02-17)*
- OAuth token with auto-refresh in `.credentials/procore_token.json`
- App Version Key: 853ac70d-7838-4d88-9c69-4968e731ff18
- Key endpoint: `drawing_revisions` (NOT `drawings` — that 404s)
- Also working: submittals, rfis, documents, drawing_areas, drawing_sets
- Nick's old company Procore: DO NOT ACCESS (audit trail risk)
- Redirect URI: http://localhost:9876/callback
- **Auth URLs must use sandbox**: `login-sandbox.procore.com` NOT `login.procore.com` *(2026-02-19)*
- **API base for sandbox**: `sandbox.procore.com` NOT `api.procore.com`
- Rate limit: 100 requests per ~60s window
- Vendor creation: use `{"vendor": {...}}` NOT `{"company": {...}}`
- API-created users can't be submittal managers/reviewers — only built-in sandbox users
- No spec section list/create endpoint — UI only, link by ID via submittal update
- No submittal workflow/approver management via API
- Cover sheet PDFs contain signed download links for all attachments (long-lived)

## EVA Deployment Template (`eva-agent/deployment-template/`)
- Standard clone-and-configure package for shipping agents to clients *(since 2026-02-18)*
- Docker Compose (OpenClaw + PostgreSQL 16 + Redis 7 + nightly backups)
- Interactive setup wizard + one-command deploy script
- Base construction prompt with FL Building Code, Miami-Dade NOA, OSHA, CSI MasterFormat
- Specialized workflow prompts: daily reports, submittals
- 4-role RBAC: admin, project_manager, superintendent, executive
- 5-phase client onboarding checklist (pre-sales → go-live support)
- Target: deploy a new client in under 30 minutes
- Customization is config + prompts only, no code changes per client

## NERV Interface (`nerv-interface/`)
- Web command interface for OpenClaw — Evangelion aesthetic *(2026-02-18)*
- v1.0: Full agent chat via Gateway WS, terminal, file browser, session manager, cron manager
- Live activity feed, inline tool calls, system metrics, syntax highlighting
- Access: http://192.168.8.124:8080
- Port 8080, FastAPI + single-file HTML frontend

## MAGI — Procore API Specialist Agent *(2026-02-19)*
- Dedicated OpenClaw agent, Sonnet model, own workspace at `/home/moby/.openclaw/workspace-magi/`
- Internal only — never ships to clients
- Purpose: deep dive Procore API, build knowledge that gets baked into EVA souls and code
- Registered in gateway config as agent ID `magi`
- First sprint launched 2026-02-19 ~6:50 PM — deep diving Daily Logs, RFIs, Change Events, Submittals, etc.
- Sprint 1 COMPLETE — 10 endpoint docs written, full API knowledge base at `memory/eva/procore-api/`
- Workspace files: SOUL.md, AGENTS.md, IDENTITY.md, memory/KNOWLEDGE.md, memory/QUEUE.md

## Procore API — Sprint 1 Findings *(2026-02-19)*
- **Daily Logs**: 18 sub-types (weather, manpower, notes, deliveries, accidents, delays, equipment, visitors, etc.)
  - Require date range params (`filters[start_date]`, `filters[end_date]`)
  - Max 13 weeks (91 days) per query — must chunk for full history
  - Each sub-type also has individual CRUD endpoint
- **RFIs**: 134 total (confirmed correct), all status "open", use v1.1 API
  - Filter syntax: `filters[status][]=open` (needs `[]` brackets)
  - Search: `?search=query` for full-text
  - Full detail (responses, distribution) only on single-RFI endpoint
- **Submittals**: 146 total, use v1.0 API, status filter appears broken
- **Documents**: 25 records (23 folders, 2 files), flat list with `parent_id` for tree
- **Meetings**: Use v1.1 API, response is GROUPED by title (must flatten)
- **Cost Codes**: 304 codes, **Vendors**: 118, **Users**: 554
- **Webhooks**: Working — can monitor any resource type for real-time updates
- **Change Events / Punch Lists**: Module not enabled in sandbox — skip for now
- **Observations**: Read-only (can't create), 22 types available
- Cross-reference map: RFIs → specs → submittals → vendors → users → cost codes
- Full docs: `memory/eva/procore-api/SPRINT-1-SUMMARY.md`

## Katsuragi — Virtual PM Agent (Planned) *(2026-02-19)*
- Planned dedicated agent to think like a GC project manager
- Named after Misato Katsuragi (tactical operations director)
- Purpose: pressure-test EVA souls, generate realistic scenarios, validate PM workflows
- Internal only — never ships to clients
- Needs Nick's brain dump on how he thinks through a day as a PM
- Reminder set for tonight (9:30 PM) to start soul file

## Protocols
- **Rei Clone Reset** *(2026-02-19)*: If Nick sends the Rei Ayanami clones image (End of Evangelion Dummy Plug System), it means: save all critical project state to memory files, update daily log, then start a fresh context session. Image saved at `protocols/rei-clone-reset.jpg`

## Standing Protocols
- Monitor context usage — warn Nick at 75%, recommend fresh session at 85%
- Always provide best option to proceed without interruption
- Separate agents > combined agents (modular pricing, easier to sell/build)
- shared-knowledge/ folder = cross-agent reference data accessible by all agents
- **Auto-abort wasteful loops** — stop after 2-3 attempts max and ask Nick before continuing
- **7 PM evening task list** — Recurring cron (weekdays). Compile pending home tasks and send.

## Infrastructure — Web Terminal
- ttyd on Moby-1, systemd user service, port 7681 *(since 2026-02-18)*
- Access from Nick's PC: http://192.168.8.124:7681 (login: moby / eva2026)
- UFW rule allows port 7681 from LAN only (192.168.8.0/24)

## Security Notes
- **ClawHub marketplace is untrusted** — 1,184 malicious skills found, prompt injection via SKILL.md files. Do NOT install any ClawHub skills. Build our own. *(2026-02-19)*
- All our skills are openclaw-bundled, all plugins are stock. Verified clean 2026-02-19.

## Lessons Learned
- `systemctl restart systemd-logind` kills display session — warn user first *(2026-02-17)*
- Manjaro KDE 6 uses kwriteconfig6/qdbus6 not old 5 versions *(2026-02-17)*
- KDE power management overrides systemd — must disable both *(2026-02-17)*
- Keep conversations shorter to avoid hitting API context limits *(2026-02-17)*
- Sudoers files need chmod 440 or they get silently ignored *(2026-02-17)*
- Paper Moby (Sonnet subagent) is too slow for batch drawing extraction — use direct API pipeline *(2026-02-18)*
- OpenClaw OAuth token can't be used for direct Anthropic API calls *(2026-02-18)*
- Procore `drawings` endpoint 404s — use `drawing_revisions` instead *(2026-02-17)*
- X Articles (native long-form posts) can't be fetched via API or scraping *(2026-02-19)*
