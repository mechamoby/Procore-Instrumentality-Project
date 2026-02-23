# GITHUB WORKFLOW PROTOCOL (Development-First)

## Objective
Keep all meaningful engineering progress versioned, recoverable, and reviewable.

## Branching Rules
- `main` must stay stable.
- New work uses feature branches: `feat/<scope>-<yyyymmdd>` or `fix/<scope>-<yyyymmdd>`.
- Avoid direct commits to `main` except urgent hotfixes.

## Daily Minimum Cadence
If code/docs changed today, minimum required:
1. Commit logical checkpoints (small, coherent slices)
2. Push branch to remote at least once before day end
3. Update daily log with branch name + summary + validation status

## Commit Message Standard
Use Conventional Commits:
- `feat:` new capability
- `fix:` bug fix
- `refactor:` behavior-preserving structural change
- `test:` test additions/updates
- `docs:` documentation
- `chore:` maintenance

Example:
- `feat(eva01): enforce attachment guardrail before submittal upload`

## PR Protocol
- Open PR for every meaningful change.
- If work spans >1 day, open as **draft PR** same day.
- PR must include:
  - what changed
  - why it changed
  - how validated
  - rollback plan

## Merge Requirements
- No merge without validation evidence.
- Squash merge preferred unless commit history itself is important.

## End-of-Day Checkpoint (Mandatory)
Run:
```bash
scripts/git-daily-checkpoint.sh
```

This prints:
- current branch
- uncommitted changes
- unpushed commits
- recommended next commands

## Recovery Principle
If local machine fails, remote branch should still preserve same-day work.
No day ends with critical work only local.
