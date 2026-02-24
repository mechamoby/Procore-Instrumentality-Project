# Procore OAuth Troubleshooting & Resolution Log

> This is a recurring pain point. Must be solved before client deployments.

## Issue History

### 2026-02-19: Token Expired + Wrong Auth URLs
**Problem:** Procore OAuth token expired, refresh token fully dead. Needed browser-based re-auth.

**Troubleshooting timeline:**
1. Auth script was using `login.procore.com` (production) — sandbox apps need `login-sandbox.procore.com`
2. Redirect URI was `http://192.168.8.124:9876/callback` (LAN IP) — Procore rejects non-localhost HTTP URIs
3. Error: "Client authentication failed due to unknown client" — misleading error, actually meant wrong auth server + wrong redirect URI
4. Changed redirect URI to `http://localhost:9876/callback` in Procore Developer Portal
5. Changed auth URLs to `login-sandbox.procore.com` in script
6. Had to run auth server on Moby-1 and open browser on Moby-1 (so localhost resolves correctly)
7. Token exchange also needs sandbox URL: `login-sandbox.procore.com/oauth/token`
8. API calls need sandbox base: `sandbox.procore.com` NOT `api.procore.com`
9. `/me` endpoint returned 401 on `api.procore.com` but 200 on `sandbox.procore.com`

**Resolution:** All URLs corrected to sandbox, token saved and working.

### 2026-02-17 (earlier session): Initial OAuth setup
- Similar confusion with sandbox vs production URLs
- Redirect URI had to be registered in Developer Portal
- Token refresh worked initially but eventually died

## The Three URL Traps

| Purpose | Production | Sandbox | Monthly Sandbox |
|---------|-----------|---------|-----------------|
| **OAuth authorize** | `login.procore.com/oauth/authorize` | `login-sandbox.procore.com/oauth/authorize` | `login-sandbox-monthly.procore.com/oauth/authorize` |
| **Token exchange** | `login.procore.com/oauth/token` | `login-sandbox.procore.com/oauth/token` | `login-sandbox-monthly.procore.com/oauth/token` |
| **API base** | `api.procore.com` | `sandbox.procore.com` | `monthly-sandbox.procore.com` |

**ALL THREE must match the same environment.** Mixing them = instant failure with misleading error messages.

## Redirect URI Rules
- `http://localhost` is the ONLY acceptable non-HTTPS redirect URI
- Any other HTTP URI (LAN IP, hostname, etc.) is rejected
- For production: must be HTTPS
- Must match EXACTLY what's registered in the Developer Portal (including trailing slashes, port, path)

## Token Lifecycle
- Access token expires in **5400 seconds (90 minutes)**
- Refresh token has longer life but DOES eventually expire
- If refresh token dies, need full browser re-auth flow
- **This is the client deployment problem** — tokens will expire and need renewal

## Client Deployment Concerns (CRITICAL)

### The Problem
For client NERV deployments, we need persistent Procore API access. Current OAuth flow requires:
1. A human to open a browser
2. Log in to Procore
3. Authorize our app
4. Catch the callback

This is fine for initial setup (SEELE onboarding) but terrible for ongoing operations. If the refresh token dies at 2 AM on a Saturday, the agent goes dark until someone re-auths.

### Questions for MAGI to Research
1. **Service Account / Client Credentials flow** — Does Procore support machine-to-machine auth without browser?
2. **Token refresh best practices** — How to keep refresh tokens alive? Proactive refresh before expiry?
3. **Webhook-based token management** — Can we set up automated token refresh?
4. **Long-lived tokens** — Any Procore app setting for extended token lifetimes?
5. **Procore Marketplace apps** — Do published apps get different auth options?
6. **Error handling** — Graceful degradation when token expires mid-operation
7. **Multi-project auth** — One token per company or per project?

### Proposed Auto-Refresh Architecture
```
EVA Agent → API call → 401? → Auto-refresh token → Retry → Still 401? → Alert admin
                                    ↓
                              Save new token
                                    ↓
                              Log refresh event
```

Every API call should:
1. Check token age before calling (refresh proactively at 80% of expiry)
2. Catch 401 responses and attempt refresh
3. If refresh fails, queue the failed request and alert admin
4. Never crash or go silent — always surface auth issues

### For Client Onboarding (SEELE Flow)
1. During setup wizard, walk client through Procore app authorization
2. Catch and save initial token
3. Set up cron job to proactively refresh every 60 minutes
4. Monitor refresh failures and alert immediately
5. Document re-auth procedure for when everything breaks

## Scripts

### Auth script: `scripts/procore-auth.py`
- Starts HTTP server on port 9876
- Opens browser to sandbox OAuth authorize URL
- Catches callback code
- Exchanges for token
- Saves to `.credentials/procore_token.json`
- **Must be run on same machine where browser opens** (localhost redirect)

### Token refresh (inline):
```python
import json, requests
creds_dir = "/path/to/.credentials"
token = json.load(open(f"{creds_dir}/procore_token.json"))
env = {}
for line in open(f"{creds_dir}/procore.env"):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        env[k] = v

# MATCH YOUR ENVIRONMENT
TOKEN_URL = "https://login-sandbox.procore.com/oauth/token"  # or login.procore.com for production

r = requests.post(TOKEN_URL, data={
    "grant_type": "refresh_token",
    "refresh_token": token["refresh_token"],
    "client_id": env["PROCORE_CLIENT_ID"],
    "client_secret": env["PROCORE_CLIENT_SECRET"],
})
if r.status_code == 200:
    new_token = r.json()
    json.dump(new_token, open(f"{creds_dir}/procore_token.json", "w"), indent=2)
    print(f"Token refreshed! Expires in {new_token['expires_in']}s")
else:
    print(f"REFRESH FAILED: {r.status_code} {r.text}")
```

---

*Last updated: 2026-02-19*
*This is a recurring problem. Solving token management is a prerequisite for client deployments.*
