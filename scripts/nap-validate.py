#!/usr/bin/env python3
"""Validate Nightly Action Plan ledger before morning report.

Checks:
1) Canonical task list exists
2) Every task has terminal checkbox state ([x] for complete OR [ ] plus BLOCKED/DEFERRED note)
3) If a task is [x], there must be proof-of-work in Execution Log
4) No "In Progress" leftovers at report time
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TASK_RE = re.compile(r"^- \[(?P<done>[ xX])\] (?P<num>\d+\)) (?P<title>.+)$")
DONE_RE = re.compile(r"^- \[x\]", re.IGNORECASE)


def parse_sections(text: str):
    sections = {}
    current = "__root__"
    sections[current] = []
    for line in text.splitlines():
        m = re.match(r"^(#{2,3})\s+(.+)$", line.strip())
        if m:
            current = m.group(2).strip().lower()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Path to memory/nap/YYYY-MM-DD-NAP.md")
    args = ap.parse_args()

    p = Path(args.file)
    if not p.exists():
        print(f"FAIL: NAP file not found: {p}")
        return 2

    text = p.read_text(encoding="utf-8")
    sections = parse_sections(text)

    tasks_block = sections.get("tasks (priority order)", [])
    completed_block = sections.get("completed", [])
    in_progress_block = sections.get("in progress", [])

    tasks = []
    for line in tasks_block:
        m = TASK_RE.match(line.strip())
        if m:
            tasks.append({
                "num": m.group("num"),
                "title": m.group("title"),
                "done": m.group("done").lower() == "x",
            })

    if not tasks:
        print("FAIL: No checkbox tasks found under '## Tasks (priority order)'")
        return 3

    errors = []

    # Check in-progress leftovers
    in_progress_items = [ln for ln in in_progress_block if DONE_RE.match(ln.strip()) or ln.strip().startswith("- [")]
    for ln in in_progress_items:
        if "none" not in ln.lower():
            errors.append("In Progress section still has active checkbox items")
            break

    completed_text = "\n".join(completed_block)

    for t in tasks:
        if t["done"]:
            if t["num"] not in completed_text and t["title"][:20] not in completed_text:
                errors.append(f"Task {t['num']} marked done but missing proof in '### Completed': {t['title']}")
        else:
            # Must be explicitly blocked/deferred in execution log
            if t["num"] not in text or not re.search(rf"{re.escape(t['num'])}.*(BLOCKED|DEFERRED)", text, re.IGNORECASE):
                errors.append(f"Task {t['num']} is unchecked but not marked BLOCKED/DEFERRED with reason")

    if errors:
        print("FAIL: NAP validation failed")
        for e in errors:
            print(f" - {e}")
        return 4

    print("PASS: NAP validation passed (report gate cleared)")
    print(f"Tasks checked: {len(tasks)}")
    done_count = sum(1 for t in tasks if t['done'])
    print(f"Done: {done_count} | Open: {len(tasks)-done_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
