# Session Handoff
> Last updated: 2026-02-24 22:50 EST from NERV

## Just Completed
- **MAJOR REBRAND**: Company is NERV. All agents are EVAs. Dropped SEELE, EVA-00/01/02, Katsuragi naming.
- **STRATEGIC PIVOT**: 100% focus on NERV database project. Procore-specific agents (submittals/RFIs) backburnered.
- Session handoff protocol created and active (`protocols/SESSION-HANDOFF.md`)
- NERV data architecture designed: file structure + DB schema + naming conventions
- Procore webhooks confirmed: 113 resources from live sandbox API — full coverage
- Scale analysis: one PC handles 5-15 projects, 97% margin
- Hardware locked: Ryzen 9, 64GB DDR5, 2TB NVMe + 8TB HDD, RTX 4060 Ti 16GB (~$1,720)
- Storage strategy: 15TB → ~7TB after optimization, index-based AI (8GB index, not 15TB parsing)
- MEMORY.md, daily log, all docs updated

## In Progress
- Nick may want to continue refining NERV database architecture
- Tonight's NAP (if one exists) — check NERV-DOCS/ after this session

## Pending / Blocked
- Actual DB implementation (SQL migrations, Docker setup)
- Webhook receiver service build
- _Inbox file watcher service build
- Embedding pipeline setup
- mini-moby context update (Nick was sharing business info with mini-moby)

## Decisions Made
- Company = NERV, agents = EVAs (no numbering)
- Focus = database architecture + service (NOT Procore feature agents)
- **Core positioning: "This isn't Procore AI. This is ABC Contractors AI."**
- Database captures institutional knowledge — that's the moat, not integrations
- Smartsheet integration locked in as key data source (matches how GCs actually work)
- "Night Crew" dropped — "24/7 AI employee" instead
- Hardware config locked (Ryzen 9 / 64GB / RTX 4060 Ti / 2TB+8TB)
- $15K setup + $3,500/mo pricing confirmed
- mini-moby given full email access (mecha.moby@gmail.com, SMTP+IMAP)

## Agent Status
- main (Moby): anthropic/claude-opus-4-6
- mini-moby: openai-codex/gpt-5.3-codex, Telegram active
- katsuragi: may need renaming/repurposing under new NERV branding
- magi: research role still valid
- eva-01: backburnered (Procore submittal agent)
