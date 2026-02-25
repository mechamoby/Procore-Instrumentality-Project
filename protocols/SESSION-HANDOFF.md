# Session Handoff Protocol

## Problem
NERV (webchat) and Telegram are separate sessions. Each session starts fresh — no memory of the other unless it's written to files. This creates dangerous gaps where work done in one session is invisible to the next.

## Solution: `memory/handoff.md`

A live shift-change document that bridges sessions.

## Rules

### Writing (Before Leaving a Session)
Every session MUST update `memory/handoff.md` before ending. Triggers:
1. User says "switching to Telegram" / "heading out" / "logging off" / "goodnight"
2. Significant work is completed (agent created, config changed, NAP executed)
3. Session hits 70%+ context utilization
4. Heartbeat detects no user activity for 30+ minutes after significant work

### What to Write
```markdown
# Session Handoff
> Last updated: YYYY-MM-DD HH:MM EST from [NERV|Telegram]

## Just Completed
- [concrete items with file paths / proof]

## In Progress
- [what's actively being worked on]

## Pending / Blocked
- [what needs attention next]

## Decisions Made
- [any decisions Nick confirmed]

## Agent Status
- [any changes to agent configs, new agents, model changes]

## NAP Status
- [current NAP state if applicable]
```

### Reading (On Session Start)
AGENTS.md bootup sequence now includes:
1. Read SOUL.md
2. Read USER.md
3. **Read memory/handoff.md** ← NEW
4. Read memory/daily/YYYY-MM-DD.md (today + yesterday)
5. If main session: read MEMORY.md

### Maintenance
- handoff.md is ephemeral — overwrite on each update (not append forever)
- Important items graduate to daily log and MEMORY.md during normal memory maintenance
- Keep it SHORT — this is a quick briefing, not a novel

## Anti-Patterns
- ❌ "I'll remember this" — NO YOU WON'T. Write it to handoff.md.
- ❌ Completing work without updating handoff — the next session won't know
- ❌ Making handoff.md too long — it's a shift change brief, not a diary
