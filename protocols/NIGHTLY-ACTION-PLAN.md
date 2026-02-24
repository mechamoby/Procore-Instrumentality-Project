# NIGHTLY ACTION PLAN (NAP) PROTOCOL

## Mission
Execute Nick's nightly plan fully and deliver a clear morning report. No night wasted.

## Source Documents
Nick creates NAP documents in NERV Command. They land on disk as:
- `NERV-DOCS/NIGHTLY ACTION PLAN - MM.DD.YYYY.html` (and .docx)

**These source files are the ultimate authority.** No rewrite, summary, or paraphrase overrides them.

## NAP Ledger
Each night's execution is tracked in:
- `memory/nap/YYYY-MM-DD-NAP.md`

### Creating the Ledger (CRITICAL — READ THIS)
When a NAP document is received:
1. Read the source HTML file directly
2. **Copy each task item VERBATIM from the source** — do NOT paraphrase, summarize, or reinterpret
3. Write them as checkbox items in the ledger with exact wording
4. Include the source file path at the top of the ledger

**NEVER rewrite tasks in your own words. Copy-paste the exact text.**

### Ledger Format
```markdown
# NAP — YYYY-MM-DD
Source: `NERV-DOCS/NIGHTLY ACTION PLAN - MM.DD.YYYY.html`
Source hash: <first 8 chars of md5sum of source file>

## Tasks (verbatim from source, in priority order)
- [ ] 1) <exact text from source>
- [ ] 2) <exact text from source>
...

## Execution Log
### Task 1: <title>
- Status: DONE | BLOCKED | DEFERRED
- Evidence: <file paths, commands, results>

### Task 2: <title>
...
```

## Overnight Execution

### Pre-Execution Validation (MANDATORY)
Before starting ANY work, every session must:
1. Check if `NERV-DOCS/NIGHTLY ACTION PLAN - MM.DD.YYYY.html` exists for today's date
2. If it exists: re-read the SOURCE HTML (not just the ledger)
3. Compare ledger tasks against source tasks — if they don't match, **rebuild the ledger from source**
4. Only then begin execution

### Execution Window
- Active: 22:00–07:00 America/New_York
- If NAP exists: execute ONLY NAP items unless blocked
- If no NAP by 00:00: self-direct per HEARTBEAT.md priorities
- NAP items ALWAYS take priority over HEARTBEAT items

### Task Status Rules
Each item must end as one of:
- `DONE` — with proof-of-work (file paths, test results, commands run)
- `BLOCKED` — with specific blocker and what is needed to unblock
- `DEFERRED` — with explicit reason

No vague statuses. No "in progress" at morning report time.

## Mandatory Checkpoints
Update the NAP ledger file at: 00:30, 02:30, 04:30, 06:30

## Morning Report
Format:
1. ✅ Completed (with proof)
2. ❌ Not completed (with reason)
3. 🚧 Blockers
4. ➡️ Immediate next actions

Keep concise and factual. No fluff.

## Reliability Rules
1. **Trust the source document over everything** — over the ledger, over memory, over chat context
2. Never rely on a previous session's interpretation of NAP items
3. If the ledger and source disagree, the source wins — rebuild the ledger
4. Re-read the source file at every checkpoint, not just at start of night
5. If a task is ambiguous, execute conservatively and flag for morning clarification — do NOT invent a different task
