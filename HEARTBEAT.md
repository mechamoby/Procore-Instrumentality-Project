# HEARTBEAT.md

## NAP Protocol
- **Full protocol:** `protocols/NIGHTLY-ACTION-PLAN.md` — read it before executing any NAP
- After 10 PM: check for `NERV-DOCS/NIGHTLY ACTION PLAN - MM.DD.YYYY.html`
- If source file exists: **read the HTML directly, copy tasks VERBATIM into ledger, then execute**
- NEVER paraphrase or reinterpret NAP items — exact text only
- If ledger already exists: **re-read source HTML and validate ledger matches before working**
- NAP items ALWAYS override HEARTBEAT pending items
- If no NAP by midnight: self-direct into productive work (HEARTBEAT pending → NERV bugs → code → docs → research)
- No night wasted — EVER. Idle overnight = failure.

## Pending
- [x] EVA Sentry v1 — make 100% deployable on emails to mecha.moby@gmail.com, follow GitHub protocols, ready for testing ✅
- [x] EVA-01 submittal flow refinements (file naming, open status, placeholder number, PM title override) ✅
- [x] Multi-project user profile DB schema design ✅
- [x] Column-level DB security grants ✅
- [x] Formalize multi-agent deployment config in deployment template (Option B, Section 11 of Third Impact) ✅
- [x] 2026-02-24 AM: EVA Sentry v1.1 — email + Procore ingest modules built (ingest_email.py, ingest_procore.py, ingest_api.py). Needs IMAP creds + NERV route mounting to go live. ✅

## NERV Bugs (from 2026-02-20 night session)
- [x] Doc editor text color dark-on-dark fix ✅
- [x] SMTP creds setup (~/.credentials/smtp.env) ✅
- [x] AGENTS panel `/api/subagents` data fix ✅
- [x] System metrics fix ✅
- [x] YouTube toggle in live feed ✅

## Heartbeat Behavior
- If all checkboxes above are complete and there is no new urgent item, heartbeat reply should be: `HEARTBEAT_OK`.
