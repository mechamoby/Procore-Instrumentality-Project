# EVA-SENTRY v1 (Lightweight Security Agent)

Purpose: pre-filter inbound requests and classify risk before passing to operational agents.

## v1 Scope
- Input: message text + channel metadata + uploaded documents
- Output: one decision
  - `allow`
  - `challenge`
  - `deny`
  - `quarantine`

## Live Integration (NERV)
- `nerv-interface/server.py` now runs Sentry preflight on inbound chat text.
- `POST /api/upload` scans every uploaded file and stores a verdict.
- Attachment gate blocks `deny/quarantine` files before `chat.send`.
- `POST /api/sentry/scan` allows external pipelines (email/Procore) to trigger scans for newly ingested files.
- Full ops notes: `eva-sentry-v1/OPS.md`.

## Policy Model
- Green: harmless internal actions (read/search/status)
- Yellow: actions that leave machine or alter important state (notify user)
- Red: destructive/sensitive/external comms without approval (PIN required)

## v1.1 — Ingest Scanning (2026-02-24)
- **Email ingest**: IMAP polling → extract body + attachments → Sentry scan → manifest
- **Procore ingest**: Poll RFIs, submittals, documents → download attachments → Sentry scan → manifest
- **NERV API integration**: `/api/sentry/ingest/email`, `/api/sentry/ingest/procore`, `/api/sentry/ingest/report`
- Watermark-based incremental scanning (only new items per poll)
- Daemon mode for continuous background polling

## Files
- `policy.json` — rule config
- `sentry.py` — deterministic evaluator (original command classifier)
- `ingest_email.py` — Email IMAP ingest scanner
- `ingest_procore.py` — Procore item ingest scanner
- `ingest_api.py` — FastAPI routes for NERV integration

## Usage
```bash
# Original command classification
python sentry.py --text "restart gateway now" --channel telegram --sender 8515314184

# Email ingest (one-shot)
python ingest_email.py

# Email ingest (daemon, poll every 5 min)
python ingest_email.py --daemon --interval 300

# Procore ingest (one-shot, all projects)
python ingest_procore.py

# Procore ingest (specific project)
python ingest_procore.py --project-id 12345

# Procore ingest (daemon, poll every 10 min)
python ingest_procore.py --daemon --interval 600
```

Returns JSON decision payload for routing layer.
