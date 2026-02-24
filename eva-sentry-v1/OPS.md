# EVA Sentry v1 — Operational Notes

## What is protected now
- **Text commands** are scanned before `chat.send` execution.
- **Uploaded files** are scanned at `/api/upload` and verdict-cached.
- **Document editor saves** are scanned before persist.
- **Attachment execution gate** blocks `deny/quarantine` files from reaching the agent.

## Verdicts
- `allow` → pass
- `challenge` → medium-risk, currently allowed with operator visibility
- `deny` / `quarantine` → blocked

## API hooks
- `POST /api/sentry/scan` with `{ "path": "...", "mime": "..." }`
  - Use this for email/Procore extracted files after ingest.
- `GET /api/sentry/verdict?path=...`
  - Retrieve prior verdict for a path.

## State location
- `eva-sentry-v1/state/policy.json`
- `eva-sentry-v1/state/verdicts/*.json`

## Policy tuning
Edit `eva-sentry-v1/state/policy.json`:
- `maxBytes`: max scan size
- `denyHashPrefixes`: SHA-256 prefixes to hard-quarantine known bad files

## Email Ingest (v1.1 — 2026-02-24)
- **Setup**: Create `~/.credentials/imap.env` with IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASS
- **One-shot**: `python eva-sentry-v1/ingest_email.py`
- **Daemon**: `python eva-sentry-v1/ingest_email.py --daemon --interval 300`
- **NERV API**: `POST /api/sentry/ingest/email` triggers one-shot scan
- **Output**: `eva-sentry-v1/ingest/email/<msg-hash>/manifest.json`
- Scans body text for prompt injection + malware patterns
- Scans all attachments via file scanner (extension, MIME, hash, content patterns)
- Aggregate verdict = worst of body + all attachments

## Procore Ingest (v1.1 — 2026-02-24)
- **Setup**: Requires existing `~/.credentials/procore.env` + `procore_token.json`
- **One-shot**: `python eva-sentry-v1/ingest_procore.py`
- **Daemon**: `python eva-sentry-v1/ingest_procore.py --daemon --interval 600`
- **NERV API**: `POST /api/sentry/ingest/procore` with optional `{"project_ids": [...]}`
- **Report**: `GET /api/sentry/ingest/report?source=all&limit=50`
- **Output**: `eva-sentry-v1/ingest/procore/<project_id>/<type>/<item_id>/manifest.json`
- Watermark tracking: `eva-sentry-v1/state/procore_watermarks.json` (only scans new items)
- Scans: RFIs (question + answers + attachments), Submittals (description + attachments), Documents

## NERV Integration
Mount ingest routes in server.py:
```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path.home() / ".openclaw/workspace/eva-sentry-v1"))
from ingest_api import mount_ingest_routes
mount_ingest_routes(app)
```

## Recommended next hardening (v1.2)
1. Add ClamAV optional deep scan when stage-1 risk != low.
2. Add explicit challenge approval workflow in UI.
3. Add telemetry panel for false positive tuning.
4. Webhook-based Procore ingest (real-time vs polling).
5. Email ingest: auto-forward flagged items to quarantine folder.
