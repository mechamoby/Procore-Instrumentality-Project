#!/usr/bin/env python3
"""Quick Procore OAuth2 browser flow. Run this, click the link, authorize, done."""

import json, http.server, urllib.parse, webbrowser, threading
from pathlib import Path
import requests

CREDS = Path.home() / ".openclaw" / "workspace" / ".credentials"
env = {}
for line in open(CREDS / "procore.env"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k] = v

CLIENT_ID = env["PROCORE_CLIENT_ID"]
CLIENT_SECRET = env["PROCORE_CLIENT_SECRET"]
REDIRECT_URI = "http://localhost:9876/callback"
AUTH_URL = "https://login-sandbox.procore.com/oauth/authorize"
TOKEN_URL = "https://login-sandbox.procore.com/oauth/token"

auth_code = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorized! You can close this tab.</h1>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code received")
    def log_message(self, *a): pass

url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
print(f"\n{'='*60}")
print("Open this URL in a browser:")
print(f"\n{url}\n")
print(f"{'='*60}\n")
print("Waiting for callback on localhost:9876...")

server = http.server.HTTPServer(("0.0.0.0", 9876), Handler)
server.timeout = 120
while auth_code is None:
    server.handle_request()

print(f"\nGot auth code, exchanging for token...")
r = requests.post(TOKEN_URL, data={
    "grant_type": "authorization_code",
    "code": auth_code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
})

if r.status_code == 200:
    token = r.json()
    json.dump(token, open(CREDS / "procore_token.json", "w"), indent=2)
    print(f"✅ Token saved! Expires in {token.get('expires_in', '?')}s")
    # Test it
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    me = requests.get("https://api.procore.com/rest/v1.0/me", headers=headers)
    if me.status_code == 200:
        u = me.json()
        print(f"✅ Authenticated as: {u.get('name', '?')} ({u.get('login', '?')})")
    else:
        print(f"⚠️ Token saved but /me returned {me.status_code}")
else:
    print(f"❌ Token exchange failed: {r.status_code}\n{r.text}")
