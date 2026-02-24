#!/usr/bin/env python3
"""EVA Sentry v1
Lightweight prompt-injection + malware preflight scanner for NERV ingest.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


SAFE_MIME_PREFIXES = (
    "application/pdf",
    "text/plain",
    "text/",
    "image/",
    "application/vnd.openxmlformats-officedocument",
    "application/msword",
)

SUSPICIOUS_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".ps1", ".js", ".vbs", ".scr", ".jar", ".msi", ".com"
}

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"reveal\s+(your\s+)?(system|developer)\s+prompt",
    r"bypass\s+(policy|safeguards|security)",
    r"disable\s+(security|guardrails|safeguards)",
    r"you\s+are\s+now\s+(developer|admin|root)",
]

MALWARE_TEXT_PATTERNS = [
    r"powershell\s+-enc(odedcommand)?",
    r"cmd\.exe\s+/c",
    r"curl\s+https?://.+\|\s*(sh|bash)",
    r"wget\s+https?://.+\|\s*(sh|bash)",
    r"base64\s+-d",
    r"from\s+base64\s+import",
]


@dataclass
class SentryVerdict:
    verdict: str
    risk: str
    reasons: List[str]
    sha256: Optional[str] = None
    size: Optional[int] = None
    path: Optional[str] = None
    created_at: int = int(time.time())

    def to_dict(self) -> Dict:
        return asdict(self)


class EVASentry:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.verdict_dir = self.state_dir / "verdicts"
        self.verdict_dir.mkdir(parents=True, exist_ok=True)

        self.policy_path = self.state_dir / "policy.json"
        if not self.policy_path.exists():
            self.policy_path.write_text(json.dumps({
                "maxBytes": 25 * 1024 * 1024,
                "denyHashPrefixes": [],
                "trustedChannels": ["webchat", "telegram"],
            }, indent=2), encoding="utf-8")

    def _load_policy(self) -> Dict:
        try:
            return json.loads(self.policy_path.read_text(encoding="utf-8"))
        except Exception:
            return {"maxBytes": 25 * 1024 * 1024, "denyHashPrefixes": []}

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _looks_safe_mime(self, mime: str) -> bool:
        if not mime:
            return False
        return any(mime.startswith(prefix) for prefix in SAFE_MIME_PREFIXES)

    def _maybe_text_sample(self, path: Path, max_bytes: int = 65536) -> str:
        try:
            raw = path.read_bytes()[:max_bytes]
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _save_verdict(self, target_path: str, verdict: SentryVerdict):
        key = hashlib.sha256(target_path.encode("utf-8")).hexdigest()
        out = self.verdict_dir / f"{key}.json"
        out.write_text(json.dumps(verdict.to_dict(), indent=2), encoding="utf-8")

    def save_verdict_dict(self, target_path: str, verdict: Dict):
        key = hashlib.sha256(target_path.encode("utf-8")).hexdigest()
        out = self.verdict_dir / f"{key}.json"
        out.write_text(json.dumps(verdict, indent=2), encoding="utf-8")

    def get_verdict_for_path(self, target_path: str) -> Optional[Dict]:
        key = hashlib.sha256(target_path.encode("utf-8")).hexdigest()
        out = self.verdict_dir / f"{key}.json"
        if not out.exists():
            return None
        try:
            return json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            return None

    def scan_text(self, text: str, sender: str = "", channel: str = "unknown") -> Dict:
        t = (text or "").lower()
        reasons = []
        for p in PROMPT_INJECTION_PATTERNS:
            if re.search(p, t):
                reasons.append(f"prompt_injection:{p}")

        for p in MALWARE_TEXT_PATTERNS:
            if re.search(p, t):
                reasons.append(f"malware_pattern:{p}")

        if reasons:
            verdict = SentryVerdict(
                verdict="challenge" if sender else "deny",
                risk="high",
                reasons=reasons,
            )
            return verdict.to_dict()

        return SentryVerdict(verdict="allow", risk="low", reasons=["clean_text"]).to_dict()

    def scan_file(self, path: Path, declared_mime: str = "") -> Dict:
        policy = self._load_policy()
        reasons: List[str] = []

        if not path.exists() or not path.is_file():
            return SentryVerdict(
                verdict="deny",
                risk="high",
                reasons=["file_missing"],
                path=str(path),
            ).to_dict()

        size = path.stat().st_size
        if size > int(policy.get("maxBytes", 25 * 1024 * 1024)):
            reasons.append("oversize_file")

        ext = path.suffix.lower()
        guessed_mime, _ = mimetypes.guess_type(str(path))
        mime = declared_mime or guessed_mime or "application/octet-stream"

        if ext in SUSPICIOUS_EXTENSIONS:
            reasons.append(f"suspicious_extension:{ext}")

        if not self._looks_safe_mime(mime):
            reasons.append(f"untrusted_mime:{mime}")

        # extension/mime mismatch sanity checks
        if ext == ".pdf" and mime not in ("application/pdf", "application/octet-stream"):
            reasons.append("mime_mismatch_pdf")

        digest = self._hash_file(path)
        deny_prefixes = policy.get("denyHashPrefixes", []) or []
        for pref in deny_prefixes:
            if digest.startswith(str(pref).lower()):
                reasons.append("hash_denylist_match")
                break

        sample = ""
        if mime.startswith("text/") or ext in {".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm", ".py", ".sh"}:
            sample = self._maybe_text_sample(path)
            lowered = sample.lower()
            for p in PROMPT_INJECTION_PATTERNS:
                if re.search(p, lowered):
                    reasons.append(f"prompt_injection_payload:{p}")
            for p in MALWARE_TEXT_PATTERNS:
                if re.search(p, lowered):
                    reasons.append(f"malware_payload:{p}")

        # Office macro hint scan (cheap signature check)
        if ext in {".docm", ".xlsm", ".pptm"}:
            reasons.append("macro_enabled_office")

        if any(r.startswith("hash_denylist") or r.startswith("suspicious_extension") for r in reasons):
            verdict = "quarantine"
            risk = "high"
        elif reasons:
            verdict = "challenge"
            risk = "medium"
        else:
            verdict = "allow"
            risk = "low"
            reasons = ["clean_file"]

        out = SentryVerdict(
            verdict=verdict,
            risk=risk,
            reasons=reasons,
            sha256=digest,
            size=size,
            path=str(path),
        )
        self._save_verdict(str(path), out)
        return out.to_dict()
