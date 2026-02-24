#!/usr/bin/env python3
"""EVA Sentry — Ingest API routes for NERV integration.

Import and mount in NERV server.py:
    from eva_sentry_v1_ingest import mount_ingest_routes
    mount_ingest_routes(app)
"""

from __future__ import annotations

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
INGEST_EMAIL_DIR = WORKSPACE / "eva-sentry-v1" / "ingest" / "email"
INGEST_PROCORE_DIR = WORKSPACE / "eva-sentry-v1" / "ingest" / "procore"


def mount_ingest_routes(app):
    """Mount ingest scanning + reporting routes onto a FastAPI app."""

    @app.post("/api/sentry/ingest/email")
    async def trigger_email_ingest():
        """Trigger a one-shot email ingest scan. Returns manifests."""
        import subprocess
        result = subprocess.run(
            ["python3", str(WORKSPACE / "eva-sentry-v1" / "ingest_email.py")],
            capture_output=True, text=True, timeout=120
        )
        try:
            manifests = json.loads(result.stdout)
        except Exception:
            manifests = []
        return {
            "ok": True,
            "scanned": len(manifests),
            "flagged": len([m for m in manifests if m.get("aggregate_verdict") != "allow"]),
            "manifests": manifests,
            "stderr": result.stderr[:500] if result.stderr else None,
        }

    @app.post("/api/sentry/ingest/procore")
    async def trigger_procore_ingest(data: dict = None):
        """Trigger a one-shot Procore ingest scan. Optionally pass {"project_ids": [...]}."""
        import subprocess
        cmd = ["python3", str(WORKSPACE / "eva-sentry-v1" / "ingest_procore.py")]
        if data and data.get("project_ids"):
            for pid in data["project_ids"]:
                cmd.extend(["--project-id", str(pid)])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        try:
            manifests = json.loads(result.stdout)
        except Exception:
            manifests = []
        return {
            "ok": True,
            "scanned": len(manifests),
            "flagged": len([m for m in manifests if m.get("aggregate_verdict") != "allow"]),
            "manifests": manifests,
            "stderr": result.stderr[:500] if result.stderr else None,
        }

    @app.get("/api/sentry/ingest/report")
    async def ingest_report(source: str = "all", limit: int = 50):
        """Get recent ingest scan results across email and/or Procore."""
        manifests = []

        dirs = []
        if source in ("all", "email"):
            if INGEST_EMAIL_DIR.exists():
                dirs.extend(sorted(INGEST_EMAIL_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit])
        if source in ("all", "procore"):
            if INGEST_PROCORE_DIR.exists():
                for proj in INGEST_PROCORE_DIR.iterdir():
                    for item_type in ("rfis", "submittals", "documents"):
                        type_dir = proj / item_type
                        if type_dir.exists():
                            dirs.extend(sorted(type_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit])

        for d in dirs[:limit]:
            mf = d / "manifest.json"
            if mf.exists():
                try:
                    manifests.append(json.loads(mf.read_text()))
                except Exception:
                    pass

        # Sort by scan time descending
        manifests.sort(key=lambda m: m.get("scanned_at", ""), reverse=True)
        flagged = [m for m in manifests if m.get("aggregate_verdict") != "allow"]

        return {
            "ok": True,
            "total": len(manifests),
            "flagged": len(flagged),
            "manifests": manifests[:limit],
        }
