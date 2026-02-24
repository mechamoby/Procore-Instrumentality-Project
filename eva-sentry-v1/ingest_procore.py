#!/usr/bin/env python3
"""EVA Sentry — Procore Item Ingest Scanner

Polls Procore projects for new/updated RFIs, submittals, and documents,
downloads attachments, and runs each through EVA Sentry.

Usage:
    python ingest_procore.py                            # one-shot scan
    python ingest_procore.py --daemon --interval 600    # poll every 10 min
    python ingest_procore.py --project-id 12345         # specific project

Credentials: ~/.credentials/procore.env + procore_token.json
Ingest output: eva-sentry-v1/ingest/procore/<project_id>/<item_type>/<item_id>/manifest.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "nerv-interface"))
sys.path.insert(0, str(WORKSPACE / "eva-agent" / "eva-00" / "src"))

from eva_sentry import EVASentry

SENTRY_STATE = WORKSPACE / "eva-sentry-v1" / "state"
INGEST_DIR = WORKSPACE / "eva-sentry-v1" / "ingest" / "procore"
WATERMARK_PATH = WORKSPACE / "eva-sentry-v1" / "state" / "procore_watermarks.json"


def _load_watermarks() -> Dict:
    if WATERMARK_PATH.exists():
        try:
            return json.loads(WATERMARK_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_watermarks(wm: Dict):
    WATERMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATERMARK_PATH.write_text(json.dumps(wm, indent=2))


def _get_procore_client():
    """Import and instantiate ProcoreClient."""
    try:
        from procore_client import ProcoreClient
        return ProcoreClient()
    except Exception as e:
        print(f"[ERROR] Cannot initialize ProcoreClient: {e}", file=sys.stderr)
        return None


def scan_procore_items(
    client,
    project_id: int,
    sentry: EVASentry,
    watermarks: Dict,
) -> List[Dict]:
    """Scan RFIs, submittals, and documents for a project. Returns manifests."""
    results = []
    proj_key = str(project_id)
    proj_wm = watermarks.get(proj_key, {})
    proj_dir = INGEST_DIR / proj_key

    # --- RFIs ---
    try:
        rfis = client.get_all(f"/rest/v1.0/projects/{project_id}/rfis")
        last_rfi = proj_wm.get("rfi_last_id", 0)
        new_rfis = [r for r in rfis if r.get("id", 0) > last_rfi]

        for rfi in new_rfis:
            rfi_id = rfi["id"]
            rfi_dir = proj_dir / "rfis" / str(rfi_id)
            rfi_dir.mkdir(parents=True, exist_ok=True)

            # Scan RFI text content
            text_content = f"RFI #{rfi.get('number', '?')}: {rfi.get('subject', '')}\n"
            text_content += f"Question: {rfi.get('question', {}).get('plain_text_body', '')}\n"
            for ans in rfi.get("answers", []):
                text_content += f"Answer: {ans.get('plain_text_body', '')}\n"

            body_verdict = sentry.scan_text(text_content, sender=str(rfi.get("created_by", {}).get("id", "")), channel="procore")

            # Scan attachments
            att_verdicts = []
            for att in rfi.get("attachments", []):
                att_url = att.get("url", "")
                att_name = att.get("filename", att.get("name", f"attachment_{att.get('id', 'unknown')}"))
                if att_url:
                    try:
                        dest = rfi_dir / att_name
                        client.download(att_url, dest)
                        v = sentry.scan_file(dest)
                        att_verdicts.append({"filename": att_name, "path": str(dest), "sentry": v})
                    except Exception as e:
                        att_verdicts.append({"filename": att_name, "error": str(e)})

            manifest = _build_manifest("rfi", rfi_id, rfi.get("subject", ""), body_verdict, att_verdicts)
            (rfi_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
            results.append(manifest)
            print(f"[{manifest['aggregate_verdict'].upper()}] RFI #{rfi.get('number')}: {rfi.get('subject', '')}")

        if new_rfis:
            proj_wm["rfi_last_id"] = max(r["id"] for r in new_rfis)
    except Exception as e:
        print(f"[WARN] RFI scan failed for project {project_id}: {e}", file=sys.stderr)

    # --- Submittals ---
    try:
        submittals = client.get_all(f"/rest/v1.1/projects/{project_id}/submittals")
        last_sub = proj_wm.get("submittal_last_id", 0)
        new_subs = [s for s in submittals if s.get("id", 0) > last_sub]

        for sub in new_subs:
            sub_id = sub["id"]
            sub_dir = proj_dir / "submittals" / str(sub_id)
            sub_dir.mkdir(parents=True, exist_ok=True)

            text_content = f"Submittal #{sub.get('number', '?')}: {sub.get('title', '')}\n"
            text_content += f"Description: {sub.get('description', {}).get('plain_text_body', '') if isinstance(sub.get('description'), dict) else sub.get('description', '')}\n"

            body_verdict = sentry.scan_text(text_content, channel="procore")

            att_verdicts = []
            for att in sub.get("attachments", []):
                att_url = att.get("url", "")
                att_name = att.get("filename", att.get("name", f"att_{att.get('id', '')}"))
                if att_url:
                    try:
                        dest = sub_dir / att_name
                        client.download(att_url, dest)
                        v = sentry.scan_file(dest)
                        att_verdicts.append({"filename": att_name, "path": str(dest), "sentry": v})
                    except Exception as e:
                        att_verdicts.append({"filename": att_name, "error": str(e)})

            manifest = _build_manifest("submittal", sub_id, sub.get("title", ""), body_verdict, att_verdicts)
            (sub_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
            results.append(manifest)
            print(f"[{manifest['aggregate_verdict'].upper()}] Submittal #{sub.get('number')}: {sub.get('title', '')}")

        if new_subs:
            proj_wm["submittal_last_id"] = max(s["id"] for s in new_subs)
    except Exception as e:
        print(f"[WARN] Submittal scan failed for project {project_id}: {e}", file=sys.stderr)

    # --- Documents (folder listing) ---
    try:
        docs = client.get_json(f"/rest/v1.0/projects/{project_id}/documents")
        last_doc = proj_wm.get("doc_last_id", 0)
        new_docs = [d for d in docs if d.get("id", 0) > last_doc and not d.get("is_folder", False)]

        for doc in new_docs:
            doc_id = doc["id"]
            doc_dir = proj_dir / "documents" / str(doc_id)
            doc_dir.mkdir(parents=True, exist_ok=True)

            doc_name = doc.get("name", f"doc_{doc_id}")
            doc_url = doc.get("url", "")

            att_verdicts = []
            if doc_url:
                try:
                    dest = doc_dir / doc_name
                    client.download(doc_url, dest)
                    v = sentry.scan_file(dest)
                    att_verdicts.append({"filename": doc_name, "path": str(dest), "sentry": v})
                except Exception as e:
                    att_verdicts.append({"filename": doc_name, "error": str(e)})

            body_verdict = sentry.scan_text(doc_name, channel="procore")
            manifest = _build_manifest("document", doc_id, doc_name, body_verdict, att_verdicts)
            (doc_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
            results.append(manifest)
            print(f"[{manifest['aggregate_verdict'].upper()}] Doc: {doc_name}")

        if new_docs:
            proj_wm["doc_last_id"] = max(d["id"] for d in new_docs)
    except Exception as e:
        print(f"[WARN] Document scan failed for project {project_id}: {e}", file=sys.stderr)

    watermarks[proj_key] = proj_wm
    return results


def _build_manifest(item_type: str, item_id: int, title: str, body_verdict: Dict, att_verdicts: List[Dict]) -> Dict:
    risk_levels = {"low": 0, "medium": 1, "high": 2}
    verdict_priority = {"allow": 0, "challenge": 1, "quarantine": 2, "deny": 3}

    all_verdicts = [body_verdict] + [a["sentry"] for a in att_verdicts if "sentry" in a]
    if not all_verdicts:
        all_verdicts = [body_verdict]

    worst_risk = max(all_verdicts, key=lambda v: risk_levels.get(v.get("risk", "low"), 0))
    worst_verdict = max(all_verdicts, key=lambda v: verdict_priority.get(v.get("verdict", "allow"), 0))

    return {
        "item_type": item_type,
        "item_id": item_id,
        "title": title,
        "body_verdict": body_verdict,
        "attachments": att_verdicts,
        "aggregate_verdict": worst_verdict.get("verdict", "allow"),
        "aggregate_risk": worst_risk.get("risk", "low"),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


def poll_once(project_ids: Optional[List[int]] = None) -> List[Dict]:
    client = _get_procore_client()
    if not client:
        return []

    sentry = EVASentry(SENTRY_STATE)
    watermarks = _load_watermarks()

    if not project_ids:
        try:
            projects = client.list_projects()
            project_ids = [p["id"] for p in projects]
        except Exception as e:
            print(f"[ERROR] Cannot list projects: {e}", file=sys.stderr)
            return []

    all_results = []
    for pid in project_ids:
        results = scan_procore_items(client, pid, sentry, watermarks)
        all_results.extend(results)

    _save_watermarks(watermarks)
    return all_results


def main():
    import argparse
    ap = argparse.ArgumentParser(description="EVA Sentry Procore Ingest Scanner")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--interval", type=int, default=600)
    ap.add_argument("--project-id", type=int, nargs="*", default=None)
    args = ap.parse_args()

    INGEST_DIR.mkdir(parents=True, exist_ok=True)

    if args.daemon:
        print(f"[SENTRY:PROCORE] Daemon mode — polling every {args.interval}s")
        while True:
            results = poll_once(args.project_id)
            flagged = [r for r in results if r["aggregate_verdict"] != "allow"]
            if results:
                print(f"[SENTRY:PROCORE] Scanned {len(results)} items, {len(flagged)} flagged")
            time.sleep(args.interval)
    else:
        results = poll_once(args.project_id)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
