#!/usr/bin/env python3
"""Procore API helper with auto-refresh. Use from any agent.

Usage:
  python3 procore-api.py get /rest/v1.0/projects/316469/submittals
  python3 procore-api.py post /rest/v1.0/projects/316469/submittals '{"submittal":{...}}'
  python3 procore-api.py upload /rest/v1.0/projects/316469/submittals/ID/attachments /path/to/file.pdf
  python3 procore-api.py patch /rest/v1.0/projects/316469/submittals/ID '{"submittal":{...}}'
  python3 procore-api.py token  # just prints current valid token
"""

import json, requests, sys, time
from pathlib import Path

# EVA-01 hardening helper (shared guardrail)
sys.path.append('/home/moby/.openclaw/workspace/eva-agent/submittal-agent')
from eva00.eva01_flow import require_attachment_path

CREDS_DIR = Path.home() / ".openclaw" / "workspace" / ".credentials"
TOKEN_FILE = CREDS_DIR / "procore_token.json"
ENV_FILE = CREDS_DIR / "procore.env"
API_BASE = "https://sandbox.procore.com"
AUTH_BASE = "https://login-sandbox.procore.com"
COMPANY_ID = "4281379"
REFRESH_MARGIN = 600  # refresh if <10 min remaining

def load_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v.strip().strip('"')
    return env

def get_token():
    """Get a valid access token, refreshing if needed."""
    with open(TOKEN_FILE) as f:
        token_data = json.load(f)
    
    expires_at = token_data["created_at"] + token_data["expires_in"]
    remaining = expires_at - time.time()
    
    if remaining > REFRESH_MARGIN:
        return token_data["access_token"]
    
    # Refresh needed
    env = load_env()
    print(f"⟳ Token expires in {remaining:.0f}s, refreshing...", file=sys.stderr)
    resp = requests.post(f"{AUTH_BASE}/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
        "client_id": env["PROCORE_CLIENT_ID"],
        "client_secret": env["PROCORE_CLIENT_SECRET"],
        "redirect_uri": "http://localhost:9876/callback",
    }, timeout=30)
    
    if resp.status_code != 200:
        print(f"❌ Token refresh failed: {resp.status_code} {resp.text[:200]}", file=sys.stderr)
        sys.exit(1)
    
    new_token = resp.json()
    with open(TOKEN_FILE, "w") as f:
        json.dump(new_token, f, indent=2)
    print("✅ Token refreshed", file=sys.stderr)
    return new_token["access_token"]

def api_call(method, path, body=None, file_path=None, retry=True):
    token = get_token()
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Procore-Company-Id": COMPANY_ID,
    }
    
    if file_path:
        # Multipart file upload — use submittal[attachments][] field name
        # Endpoint is PATCH /submittals/{id} (NOT a separate /attachments endpoint)
        safe_file = require_attachment_path(file_path)
        with open(safe_file, "rb") as f:
            mime = "application/pdf" if safe_file.lower().endswith(".pdf") else "application/octet-stream"
            files = {"submittal[attachments][]": (Path(safe_file).name, f, mime)}
            resp = requests.patch(url, headers=headers, files=files, timeout=60)
    elif method == "get":
        headers["Accept"] = "application/json"
        resp = requests.get(url, headers=headers, timeout=30)
    elif method == "post":
        headers["Content-Type"] = "application/json"
        resp = requests.post(url, headers=headers, data=body or "{}", timeout=30)
    elif method == "patch":
        headers["Content-Type"] = "application/json"
        resp = requests.patch(url, headers=headers, data=body or "{}", timeout=30)
    elif method == "delete":
        resp = requests.delete(url, headers=headers, timeout=30)
    else:
        print(f"Unknown method: {method}", file=sys.stderr)
        sys.exit(1)
    
    # Auto-retry on 401 (token expired between check and call)
    if resp.status_code == 401 and retry:
        print("⟳ Got 401, forcing token refresh...", file=sys.stderr)
        # Invalidate by setting created_at to 0
        with open(TOKEN_FILE) as f:
            td = json.load(f)
        td["created_at"] = 0
        with open(TOKEN_FILE, "w") as f:
            json.dump(td, f, indent=2)
        return api_call(method, path, body, file_path, retry=False)
    
    return resp

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    method = sys.argv[1].lower()
    
    if method == "token":
        print(get_token())
        return
    
    if len(sys.argv) < 3:
        print("Need: method path [body|file]", file=sys.stderr)
        sys.exit(1)
    
    path = sys.argv[2]
    
    if method == "upload":
        if len(sys.argv) < 4:
            print("Need file path for upload", file=sys.stderr)
            sys.exit(1)
        resp = api_call("patch", path, file_path=sys.argv[3])
    else:
        body = sys.argv[3] if len(sys.argv) > 3 else None
        resp = api_call(method, path, body)
    
    print(json.dumps({
        "status": resp.status_code,
        "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:500]
    }, indent=2))

if __name__ == "__main__":
    main()
