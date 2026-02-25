# MEMORY.md - Moby's Long-Term Memory
> Last curated: 2026-02-23

## Nick Stula — The Boss
- 32, married, 2 babies, Miami *(since 2026-02-16)*
- PM at Miller Construction; long commute; limited daytime bandwidth
- Goal: buy a house for family
- Priority channel: Telegram (phone + web.telegram.org)
- Needs autonomous execution + concise decision-ready updates

## Core Mission (EVA / SEELE)
- Build/sell locally deployed AI agents for construction firms *(since 2026-02-16)*
- Value prop: data stays on client-owned NERV box; fast PM workflows
- Target customer: exec-level GC/dev leaders in South Florida
- Commercial model: setup + monthly per-agent pricing

## Product Lineup
- **EVA-00**: Master Clerk / Project Historian *(2026-02-19)*
- **EVA-01**: Submittal Agent (review + Procore draft creation)
- **EVA-02**: RFI Agent
- **Katsuragi**: client-facing operations director routing to EVA specialists *(2026-02-20)*
- Modular packaging is preferred (sell agents individually or bundled)

## EVA-01 Critical Truths
- Confirmed flow: PDF → review → PM approval → stamp → Procore draft + attachment *(2026-02-19)*
- Required defaults:
  - submittal `status` = `open`
  - placeholder `number` required by Procore (TBD pattern)
  - naming format: `{Project} - {Title} - {Date}.pdf`
  - PM title override must be respected
- Attachment upload method: `PATCH submittal[attachments][]`
- Guardrail needed: never review random local files when attachment path is missing

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

## mini-Moby Agent *(2026-02-23)*
- Registered in openclaw.json, model: openai/gpt-4o-mini
- Workspace: /home/moby/.openclaw/workspace-mini-moby/
- Telegram token wired + binding added
- Role: overflow/research/drafting, no production changes
- Status: config done, Telegram delivery unconfirmed at session end

## Standing Protocols
- **Rei Clone Reset** *(since 2026-02-19)*: Core protocol — see `protocols/REI-CLONE-RESET.md`. NEVER DELETE.
- Monitor context usage — warn Nick at 75%, recommend fresh session at 85%
- Auto-abort wasteful loops — stop after 2-3 attempts max and ask Nick
- 7 PM evening task list — Recurring cron (weekdays). Compile pending home tasks and send.

## Business Model v2 — The Digital Superintendent *(2026-02-24)*
- **Pivot**: OpenClaw agent (full digital employee) vs Procore agents (feature inside their app)
- **Pricing**: $15K setup (one-time) + $3,500/month all-in per project
- **Core offering**: Digital PM + Night Crew (overnight processing) + 6 AM morning report
- **Signature feature**: "Your projects make progress while you sleep"
- **Target**: South Florida GCs, mid-size ($20-100M annual volume)
- **Year 1 conservative**: ~$294K revenue
- **Full doc**: `business/SEELE-MODEL-V2.md`

## Procore Competitive Intelligence *(2026-02-24)*
- Agent Builder v1 launched Sep 2025, already shut down for new activations
- Acquired Datagrid AI (Jan 20, 2026) — rebuilding as "next gen Procore AI"
- Datagrid: 31-person team, CEO Thiago da Costa (sold Lagoa to Autodesk for $60M)
- Integration timeline: 12-18 months before serious competitive threat
- Their agents: cloud-only, create-only (can't modify/delete), Procore-only
- Our edge: cross-platform, overnight processing, local deployment, white-glove service
- Procore Drive: only useful for onboarding bulk import, locked into deployment protocol

## Lessons to Retain
- Diagnose with minimal reproducible tests before speculative fixes
- Prefer deterministic state files over chat-context assumptions
- Avoid hidden file-input hacks in Chrome; use transparent overlay on visible control
- Keep sessions shorter; monitor context utilization proactively
