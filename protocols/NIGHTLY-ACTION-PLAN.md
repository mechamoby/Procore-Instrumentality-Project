# NIGHTLY ACTION PLAN (NAP) PROTOCOL

## Mission
Execute Nick's nightly plan fully and deliver a clear morning report. No night wasted.

## Canonical Source of Truth
- Every received NAP must be saved immediately to:
  - `memory/nap/YYYY-MM-DD-NAP.md`
- Parse into checkbox tasks with priority order.
- This file is the only authoritative overnight task list.

## Overnight Execution Window
- Active window: 22:00-07:00 America/New_York.
- If NAP exists: execute only NAP items unless blocked.
- If no NAP by 00:00: self-direct productive work per HEARTBEAT.md priorities.

## Task Status Rules
Each item must end as one of:
- `DONE`
- `BLOCKED` (with blocker + what is needed)
- `DEFERRED` (with explicit reason)

No vague status labels.

## Proof-of-Work Requirement
An item cannot be marked `DONE` without evidence:
- changed file paths and short summary
- command/test evidence when applicable
- verification note

## Mandatory Checkpoints
Update the NAP file at:
- 00:30
- 02:30
- 04:30
- 06:30

## Morning Report Gate (Mandatory)
Before sending any morning report, run:

```bash
scripts/nap-validate.py --file memory/nap/YYYY-MM-DD-NAP.md
```

- If result is `PASS`: report may be sent.
- If result is `FAIL`: fix ledger/task states first; do not send final morning report yet.

## Morning Report Format
1. Completed
2. Not completed
3. Blockers
4. Immediate next actions

Keep concise and factual.

## Reliability Safeguards
- Never rely on transient chat state for NAP presence.
- Always re-check `memory/nap/YYYY-MM-DD-NAP.md` before heartbeat responses.
- If conflicting signals occur, trust canonical NAP file over memory/context assumptions.
