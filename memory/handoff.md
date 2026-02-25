# Session Handoff
> Last updated: 2026-02-25 13:15 EST from Telegram

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

## Pending
- Smartsheet adapter (Phase 1 integration)
- Procore OAuth token management
- End-to-end integration test with real Procore sandbox
- NERV interface updates (webhook stats, doc search)
- Client-facing portal design (responsive mobile UI)
- NERV web portal login/auth system (per-user accounts, role-based)

## Market Intel — SAVE THIS
- Lunch with Shell concrete VP + Miller precon VP + estimators
- Miller has CRM, doesn't use it. Relies on "excel on steroids" (Smartsheet now)
- Shell VP had Outlook plugin sales pitch — rules-based, no AI, heard AI coming
- Shell VP said "the future is agentic AI" + "would work with the excel on steroids"
- **These are our exact target customers describing exactly what we're building**
- Miller Smartsheet = potential internal pilot opportunity
