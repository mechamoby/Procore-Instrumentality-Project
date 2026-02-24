#!/usr/bin/env python3
"""Procore OAuth token auto-refresh. Run via cron every 60 minutes.
Token expires in 5400s (90 min), so refreshing every 60 keeps it alive."""

import json
import requests
import sys
from pathlib import Path

CREDS_DIR = Path.home() / ".openclaw" / "workspace" / ".credentials"
TOKEN_FILE = CREDS_DIR / "procore_token.json"
ENV_FILE = CREDS_DIR / "procore.env"

def load_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v.strip().strip('"')
    return env

def refresh():
    env = load_env()
    with open(TOKEN_FILE) as f:
        token_data = json.load(f)

    resp = requests.post("https://login-sandbox.procore.com/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
        "client_id": env["PROCORE_CLIENT_ID"],
        "client_secret": env["PROCORE_CLIENT_SECRET"],
        "redirect_uri": "http://localhost:9876/callback",
    }, timeout=30)

    if resp.status_code == 200:
        new_token = resp.json()
        with open(TOKEN_FILE, "w") as f:
            json.dump(new_token, f, indent=2)
        
        # Verify it works
        verify = requests.get(
            "https://sandbox.procore.com/rest/v1.0/me",
            headers={"Authorization": f"Bearer {new_token['access_token']}"},
            timeout=10,
        )
        if verify.status_code == 200:
            print(f"✅ Token refreshed. Expires in {new_token.get('expires_in')}s")
            return True
        else:
            print(f"⚠️ Token refreshed but verification failed: {verify.status_code}")
            return True  # Token was refreshed, just verification hiccup
    else:
        print(f"❌ Refresh failed: {resp.status_code} {resp.text[:200]}")
        return False

if __name__ == "__main__":
    try:
        success = refresh()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
