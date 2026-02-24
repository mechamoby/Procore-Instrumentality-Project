# Demo Findings → Product Improvement Backlog (2026-02-23)

## P0 (Must Fix)
1. **Attachment truth-check guardrail** ✅ implemented
   - EVA-01 helper now fails loud on missing/invalid attachment path (`require_attachment_path`).
   - Added in: `eva-agent/submittal-agent/eva00/eva01_flow.py`
2. **Deterministic NAP execution ledger** ✅ implemented
   - Canonical nightly file + explicit DONE/BLOCKED/DEFERRED state.
3. **Telegram ingest observability** ✅ v1 implemented
   - Added health/observability scripts:
     - `scripts/check-telegram-sync.sh`
     - `scripts/telegram-ingest-observability.sh`
   - Added runbook:
     - `memory/infrastructure/NERV-TELEGRAM-SYNC-RUNBOOK.md`

## P1 (High Value)
1. **NERV Documents Export UX**
   - one-click export to DOCX/HTML (implemented)
2. **Sub-agent dashboard reliability**
   - consume subagents tool API directly (implemented)
3. **System metrics reliability**
   - verify endpoint contract and frontend parsing for CPU/RAM/Disk/Uptime.

## P2 (Polish)
1. **NGE easter events**
   - occasional themed visual/line in UI (implemented v1)
2. **YouTube mini player improvements**
   - persistence of last URL and basic play-state indicator.

## Acceptance Criteria
- Demo path must survive clean-room test: Telegram PDF -> Katsuragi -> EVA-01 -> Procore draft with attachment.
- Any missing file path must produce immediate visible failure reason to user.
- Nightly report must list all NAP items with proof-of-work.
