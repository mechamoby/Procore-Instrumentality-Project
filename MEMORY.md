# MEMORY.md - Moby's Long-Term Memory
> Last curated: 2026-02-23

## Nick Stula — The Boss
- 32, married, 2 babies, Miami *(since 2026-02-16)*
- PM at Miller Construction; long commute; limited daytime bandwidth
- Goal: buy a house for family
- Priority channel: Telegram (phone + web.telegram.org)
- Needs autonomous execution + concise decision-ready updates

## Core Mission — NERV *(rebrand 2026-02-24)*
- Company name: **NERV** (dropped SEELE)
- All AI agents = **EVAs** (generic term, no more EVA-00/01/02 numbering)
- Build/sell locally deployed AI agents (EVAs) for construction firms *(since 2026-02-16)*
- Value prop: data stays on client-owned NERV box; intelligent data architecture + managed service
- Target customer: exec-level GC/dev leaders in South Florida
- Commercial model: $15K setup + $3,500/month per project

## Product Focus — NERV Database *(2026-02-24)*
- **Core product is the NERV database + EVA agents + managed service**
- **"This isn't Procore AI. This is ABC Contractors AI."** ← THE positioning statement
- Without the database, we're just configuring OpenClaw agents — any dev can do that
- The database captures **institutional knowledge**: past projects, old bids, archived RFIs, vendor history, lessons learned, employee handbooks, company newsletters — everything that makes a company THAT company
- EVAs operate on this accumulated intelligence. Day 1 it's smart. Day 365 it's indispensable.
- Procore, Smartsheet, email = **feeding tubes into the brain.** The brain (database) is the product.
- Procore-specific agents (submittal review, RFI drafting) = backburner. Don't compete with Procore on Procore features.
- Smartsheet integration = locked in as key integration (matches how GCs actually work — "excel on steroids")
- Key architecture docs: `NERV-DOCS/NERV-DATA-ARCHITECTURE.md`, `NERV-DOCS/SCALE-ANALYSIS.md`, `NERV-DOCS/HARDWARE-ANALYSIS.md`, `NERV-DOCS/STORAGE-STRATEGY.md`

## Market Intelligence — Lunch with Shell VP + Miller VP *(2026-02-24)*
- VP from large concrete company + Nick's VP of precon at Miller + estimators
- Miller has CRM but doesn't use it. Precon team relies on "excel sheet on steroids" (forever spreadsheet as database)
- Miller moving to Smartsheet for less friction on shared docs
- Shell contractor VP had Outlook plugin sales pitch yesterday — auto-collects data from emails by parameters, NOT AI, but heard AI version coming
- Shell VP explicitly said "the future is agentic AI" and "would work so well with the excel on steroids document"
- **This is live market validation from our exact target customers**
- Entry point strategy: connect to their existing Smartsheet/Excel → prove value → deploy full NERV box
- Miller Smartsheet = potential internal pilot opportunity (proof of concept, not a sale)

## Procore API (Sandbox) — Operational Facts
- Company ID: **4281379**, Project ID: **316469** *(since 2026-02-17)*
- Sandbox auth/base URLs only (`login-sandbox.procore.com`, `sandbox.procore.com`)
- `drawing_revisions` works; `drawings` endpoint 404s
- No API for submittal workflow assignment; spec section list/create also limited
- Private integration path (Path B) is valid for deployments *(2026-02-21)*

## Platform & Infrastructure
- Host: Manjaro laptop, always-on posture, Docker/Postgres/Redis/Cron available
- NERV interface at `http://192.168.8.124:8080`
- NERV uploads land in `nerv-uploads/` and mirrored to `~/.openclaw/media/inbound/`
- Avoid orphan `server.py` process on 8080 (can block managed service)

## Telegram Settings
- Messages set to **auto-delete after 24 hours** *(2026-02-24)*
- Context bloat is only a same-day problem; history self-clears overnight
- For immediate reset: Nick clears chat manually from Telegram app (bot can't bulk-delete)

## Telegram/NERV Reliability Notes
- Explicit bindings can disable Telegram auto-binding; must explicitly include main bot binding *(2026-02-22)*
- Known failure class: file messages with missing inbound path; must fail loud to user, not hallucinate
- Don’t restart gateway from active Telegram session (drops context)

## Security / Policy
- Security protocol: `protocols/SECURITY-MASTER.md`
- External communications require explicit approval
- Nick is authorized controller; avoid exposing personal/internal data in shared contexts

## Business/Execution Protocols
- NAP is mandatory nightly execution mechanism
- Canonical NAP protocol file: `protocols/NIGHTLY-ACTION-PLAN.md` *(2026-02-23)*
- Canonical nightly ledger location: `memory/nap/YYYY-MM-DD-NAP.md`
- Morning report must be factual: DONE / BLOCKED / DEFERRED + proof-of-work

## Ongoing Priorities (as of 2026-02-23 night)
- NAP 02.23: NERV DB Architecture v1, Brownsville Sandbox Plan, Soul Dump + CM Logic Sheet, Cross-Session Sync, GitHub push
- mini-Moby agent created but Telegram response not yet confirmed — debug on next session
- Cross-session sync protocol (nerv-handoff.md) is critical gap — implement immediately
- Browser Relay: internal-only, not client-facing

## mini-Moby Agent *(2026-02-23, updated 2026-02-24)*
- Registered in openclaw.json, model: openai-codex/gpt-5.3-codex
- Workspace: /home/moby/.openclaw/workspace-mini-moby/
- Telegram token wired + binding active
- Role: overflow/research/drafting, no production changes

## Cross-Session Handoff Protocol *(2026-02-24)*
- **Problem**: NERV and Telegram are separate sessions — work done in one is invisible to the other
- **Solution**: `memory/handoff.md` — live shift-change file updated before session transitions
- **Protocol doc**: `protocols/SESSION-HANDOFF.md`
- **AGENTS.md updated**: handoff.md is now step 3 in bootup sequence
- **Rule**: NEVER end a session with significant work without updating handoff.md

## Standing Protocols
- **Rei Clone Reset** *(since 2026-02-19)*: Core protocol — see `protocols/REI-CLONE-RESET.md`. NEVER DELETE.
- Monitor context usage — warn Nick at 75%, recommend fresh session at 85%
- Auto-abort wasteful loops — stop after 2-3 attempts max and ask Nick
- 7 PM evening task list — Recurring cron (weekdays). Compile pending home tasks and send.

## Business Model — NERV *(updated 2026-02-24)*
- **Company**: NERV
- **Product**: Locally deployed AI data platform + managed EVA agents for construction
- **Pricing**: $15K setup (one-time) + $3,500/month all-in per project
- **Core offering**: Intelligent local data architecture + 24/7 AI employee + managed service
- **Signature feature**: "Your projects make progress while you sleep"
- **Target**: South Florida GCs, mid-size ($20-100M annual volume)
- **Dropped**: "Night Crew" branding (cheap vibe), SEELE name, individual agent numbering
- **Key docs**: `NERV-DOCS/NERV-DATA-ARCHITECTURE.md`, `business/SEELE-MODEL-V2.md` (legacy naming)

## Procore Competitive Intelligence *(2026-02-24)*
- Agent Builder v1 launched Sep 2025, already shut down for new activations
- Acquired Datagrid AI (Jan 20, 2026) — rebuilding as "next gen Procore AI"
- Datagrid: 31-person team, CEO Thiago da Costa (sold Lagoa to Autodesk for $60M)
- Integration timeline: 12-18 months before serious competitive threat
- Their agents: cloud-only, create-only (can't modify/delete), Procore-only
- **Our edge: local data ownership, intelligent architecture, cross-platform, white-glove service**
- **Strategic shift: don't compete on Procore features — compete on data intelligence + service**
- Procore Drive: useful for onboarding bulk import
- Procore webhooks: 113 resources confirmed from live sandbox API (full coverage)

## Lessons to Retain
- Diagnose with minimal reproducible tests before speculative fixes
- Prefer deterministic state files over chat-context assumptions
- Avoid hidden file-input hacks in Chrome; use transparent overlay on visible control
- Keep sessions shorter; monitor context utilization proactively
