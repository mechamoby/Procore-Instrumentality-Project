#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/home/moby/.openclaw/workspace}"
cd "$ROOT"

echo "=== Git Daily Checkpoint ==="
echo "Repo: $ROOT"
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "(not-a-repo)")
echo "Branch: $branch"

echo
echo "-- Uncommitted changes --"
if [[ -n "$(git status --porcelain)" ]]; then
  git status --short
else
  echo "clean"
fi

echo
echo "-- Unpushed commits --"
upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true)
if [[ -z "$upstream" ]]; then
  echo "No upstream set for current branch."
  echo "Suggested: git push -u origin $branch"
else
  ahead=$(git rev-list --left-right --count "$upstream"...HEAD 2>/dev/null | awk '{print $2}')
  if [[ "${ahead:-0}" -gt 0 ]]; then
    echo "$ahead commit(s) not pushed"
    git log --oneline "$upstream"..HEAD
  else
    echo "No unpushed commits"
  fi
fi

echo
echo "-- Suggested next commands --"
echo "git add -A"
echo "git commit -m 'feat(scope): summary'"
echo "git push"
