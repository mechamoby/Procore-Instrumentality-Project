# Session Handoff
> Last updated: 2026-02-24 23:33 EST from NERV

## ⚠️ READ THIS FIRST — TONIGHT WAS MASSIVE

Nick and I just had a 3+ hour strategy session on NERV Command Interface. If you're reading this on Telegram, you KNOW everything below. Don't ask Nick to re-explain anything.

## Major Decisions Made Tonight

### Rebrand
- Company = **NERV** (dropped SEELE entirely)
- All agents = **EVAs** (generic term — no more EVA-00, EVA-01, EVA-02, Katsuragi)
- This is permanent. Do not use the old naming.

### Strategic Pivot
- **100% focus on NERV database project**
- Procore-specific agents (submittal review, RFI drafting) = **backburner**
- Don't compete with Procore on Procore features — they'll always win that race

### Core Positioning
**"This isn't Procore AI. This is ABC Contractors AI."**
- The database captures institutional knowledge: past projects, old bids, archived RFIs, vendor history, lessons learned, handbooks, newsletters — everything that makes a company THAT company
- Without the database, we're just configuring OpenClaw agents — any dev can do that
- The database is the moat. EVAs operate on accumulated intelligence. Day 1 smart, Day 365 indispensable.
- Procore, Smartsheet, email = feeding tubes into the brain. The brain (database) is the product.

### Smartsheet Integration — LOCKED IN
- Lunch intel: GC VPs use "excel on steroids" as their real database. They're moving to Smartsheet.
- Shell VP literally described our product: "agentic AI that works with the spreadsheet"
- Smartsheet webhooks fully compatible with OpenClaw (confirmed by mini-moby research)
- Entry strategy: connect to their existing Smartsheet → prove value → deploy full NERV box

### Pricing Confirmed
- $15K setup (one-time) + $3,500/month per project

## What Was Built Tonight
- `protocols/SESSION-HANDOFF.md` — this handoff protocol (you're using it right now)
- `NERV-DOCS/NERV-DATA-ARCHITECTURE.md` — full file structure + DB schema + naming conventions
- `NERV-DOCS/SCALE-ANALYSIS.md` — 5-project deployment, 97% margin, one PC handles it
- `NERV-DOCS/HARDWARE-ANALYSIS.md` — CPU/RAM/GPU/storage deep dive
- `NERV-DOCS/STORAGE-STRATEGY.md` — tiered storage, 15TB onboarding, index-based AI
- `memory/eva/procore-api/WEBHOOK-RESOURCES-CONFIRMED.md` — 113 webhook resources from live Procore API

### Hardware Config LOCKED
- Ryzen 9 7950X, 64GB DDR5, 2TB NVMe + 8TB HDD, RTX 4060 Ti 16GB
- ~$1,720 build cost against $15K setup fee = 89% margin

### Key Technical Insights
- AI indexes data (8GB in RAM), doesn't parse all of it (15TB). Queries return in seconds.
- 15TB onboarding = ~1 week unattended (catalog overnight, embed in 30 min)
- Storage optimizations reduce 15TB raw → ~7TB actual
- Procore webhooks: 113 resources confirmed, every feature has full coverage, ~5 second latency
- One high-end PC handles 5-15 active projects comfortably

## Other Updates
- mini-moby given full email access (mecha.moby@gmail.com — SMTP + IMAP)
- mini-moby model confirmed as gpt-5.3-codex (MEMORY.md was outdated)
- Everything committed and pushed to GitHub

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
