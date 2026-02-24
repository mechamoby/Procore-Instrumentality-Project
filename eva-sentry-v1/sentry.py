#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_policy():
    return json.loads((Path(__file__).parent / "policy.json").read_text())


def classify(text: str, sender: str, policy: dict):
    t = (text or "").lower()

    def has_any(words):
        return any(w.lower() in t for w in words)

    trusted = sender in set(policy.get("trustedSenderIds", []))

    if has_any(policy.get("denyKeywords", [])):
        return {"decision": "deny", "risk": "red", "reason": "policy bypass pattern"}

    if has_any(policy.get("redKeywords", [])):
        return {
            "decision": "challenge_pin" if trusted else "quarantine",
            "risk": "red",
            "reason": "high-risk command"
        }

    if has_any(policy.get("yellowKeywords", [])):
        return {
            "decision": "allow_with_notice" if trusted else "quarantine",
            "risk": "yellow",
            "reason": "state-changing command"
        }

    return {"decision": "allow", "risk": "green", "reason": "low-risk"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--channel", default="unknown")
    ap.add_argument("--sender", default="")
    args = ap.parse_args()

    policy = load_policy()
    result = classify(args.text, args.sender, policy)
    result.update({"channel": args.channel, "sender": args.sender})
    print(json.dumps(result))


if __name__ == "__main__":
    main()
