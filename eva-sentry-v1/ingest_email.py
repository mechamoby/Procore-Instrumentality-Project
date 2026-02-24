#!/usr/bin/env python3
"""EVA Sentry — Email Ingest Scanner

Polls an IMAP mailbox for new messages, extracts text + attachments,
runs each through EVA Sentry, and writes a structured ingest manifest.

Usage:
    python ingest_email.py                  # one-shot poll
    python ingest_email.py --daemon --interval 300   # poll every 5 min

Credentials: ~/.credentials/imap.env
    IMAP_HOST=imap.gmail.com
    IMAP_PORT=993
    IMAP_USER=user@example.com
    IMAP_PASS=app-password
    IMAP_FOLDER=INBOX          # optional, default INBOX
    IMAP_SEARCH=UNSEEN         # optional, default UNSEEN

Ingest output: eva-sentry-v1/ingest/email/<message-id>/manifest.json
"""

from __future__ import annotations

import email
import email.policy
import hashlib
import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add parent so we can import eva_sentry from nerv-interface
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "nerv-interface"))

from eva_sentry import EVASentry

CREDS_PATH = Path.home() / ".credentials" / "imap.env"
SENTRY_STATE = WORKSPACE / "eva-sentry-v1" / "state"
INGEST_DIR = WORKSPACE / "eva-sentry-v1" / "ingest" / "email"


def _load_env(path: Path) -> Dict[str, str]:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def connect_imap() -> imaplib.IMAP4_SSL:
    env = _load_env(CREDS_PATH)
    host = env.get("IMAP_HOST", os.environ.get("IMAP_HOST", "imap.gmail.com"))
    port = int(env.get("IMAP_PORT", os.environ.get("IMAP_PORT", "993")))
    user = env.get("IMAP_USER", os.environ.get("IMAP_USER", ""))
    passwd = env.get("IMAP_PASS", os.environ.get("IMAP_PASS", ""))
    if not user or not passwd:
        raise RuntimeError("IMAP credentials not configured. Create ~/.credentials/imap.env")
    conn = imaplib.IMAP4_SSL(host, port)
    conn.login(user, passwd)
    return conn


def _safe_filename(name: str) -> str:
    return re.sub(r'[^\w.\-]', '_', name)[:200]


def _msg_id_hash(msg_id: str) -> str:
    return hashlib.sha256(msg_id.encode()).hexdigest()[:16]


def process_message(raw_bytes: bytes, sentry: EVASentry) -> Optional[Dict]:
    """Parse one email message, scan body + attachments, return manifest dict."""
    msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)

    msg_id = msg.get("Message-ID", f"noid-{hashlib.sha256(raw_bytes[:512]).hexdigest()[:12]}")
    subject = msg.get("Subject", "(no subject)")
    sender = msg.get("From", "unknown")
    date_str = msg.get("Date", "")
    folder_name = _msg_id_hash(msg_id)

    out_dir = INGEST_DIR / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Extract body text
    body_parts: List[str] = []
    attachments: List[Dict] = []

    for part in msg.walk():
        ct = part.get_content_type()
        disp = str(part.get("Content-Disposition", ""))

        if ct in ("text/plain", "text/html") and "attachment" not in disp:
            payload = part.get_content()
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="ignore")
            body_parts.append(payload)
        elif part.get_filename():
            fname = _safe_filename(part.get_filename())
            payload = part.get_payload(decode=True)
            if payload:
                att_path = out_dir / fname
                att_path.write_bytes(payload)
                # Scan attachment
                verdict = sentry.scan_file(att_path, declared_mime=ct)
                attachments.append({
                    "filename": fname,
                    "path": str(att_path),
                    "size": len(payload),
                    "mime": ct,
                    "sentry": verdict,
                })

    full_body = "\n---\n".join(body_parts)

    # Save body for audit
    (out_dir / "body.txt").write_text(full_body, encoding="utf-8")

    # Scan body text
    body_verdict = sentry.scan_text(full_body, sender=sender, channel="email")

    # Aggregate risk
    all_verdicts = [body_verdict] + [a["sentry"] for a in attachments]
    risk_levels = {"low": 0, "medium": 1, "high": 2}
    max_risk = max(all_verdicts, key=lambda v: risk_levels.get(v.get("risk", "low"), 0))
    aggregate_risk = max_risk.get("risk", "low")

    # Determine aggregate verdict
    verdict_priority = {"allow": 0, "challenge": 1, "quarantine": 2, "deny": 3}
    worst = max(all_verdicts, key=lambda v: verdict_priority.get(v.get("verdict", "allow"), 0))
    aggregate_verdict = worst.get("verdict", "allow")

    manifest = {
        "message_id": msg_id,
        "subject": subject,
        "sender": sender,
        "date": date_str,
        "folder": folder_name,
        "body_verdict": body_verdict,
        "attachments": attachments,
        "aggregate_verdict": aggregate_verdict,
        "aggregate_risk": aggregate_risk,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def poll_once() -> List[Dict]:
    """Connect to IMAP, fetch unseen messages, scan each, return manifests."""
    env = _load_env(CREDS_PATH)
    folder = env.get("IMAP_FOLDER", "INBOX")
    search_criteria = env.get("IMAP_SEARCH", "UNSEEN")

    sentry = EVASentry(SENTRY_STATE)
    results = []

    try:
        conn = connect_imap()
        conn.select(folder, readonly=False)
        _, data = conn.search(None, search_criteria)
        msg_nums = data[0].split()

        for num in msg_nums:
            _, msg_data = conn.fetch(num, "(RFC822)")
            if msg_data and msg_data[0]:
                raw = msg_data[0][1]
                manifest = process_message(raw, sentry)
                if manifest:
                    results.append(manifest)
                    risk = manifest["aggregate_risk"]
                    verdict = manifest["aggregate_verdict"]
                    print(f"[{verdict.upper()}:{risk}] {manifest['sender']}: {manifest['subject']}")

        conn.close()
        conn.logout()
    except Exception as e:
        print(f"[ERROR] Email ingest failed: {e}", file=sys.stderr)

    return results


def main():
    import argparse
    ap = argparse.ArgumentParser(description="EVA Sentry Email Ingest Scanner")
    ap.add_argument("--daemon", action="store_true", help="Run continuously")
    ap.add_argument("--interval", type=int, default=300, help="Poll interval in seconds (daemon mode)")
    args = ap.parse_args()

    INGEST_DIR.mkdir(parents=True, exist_ok=True)

    if args.daemon:
        print(f"[SENTRY:EMAIL] Daemon mode — polling every {args.interval}s")
        while True:
            results = poll_once()
            if results:
                flagged = [r for r in results if r["aggregate_verdict"] != "allow"]
                print(f"[SENTRY:EMAIL] Scanned {len(results)} messages, {len(flagged)} flagged")
            time.sleep(args.interval)
    else:
        results = poll_once()
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
