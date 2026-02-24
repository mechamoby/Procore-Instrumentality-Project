#!/usr/bin/env python3
"""Procore token keepalive — refreshes the OAuth token to prevent expiry.
Run via cron every 12 hours."""

import json, requests, sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
CREDS = WORKSPACE / '.credentials'

def main():
    with open(CREDS / 'procore.env') as f:
        env = {}
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k] = v

    with open(CREDS / 'procore_token.json') as f:
        token = json.load(f)

    r = requests.post('https://sandbox.procore.com/oauth/token', data={
        'grant_type': 'refresh_token',
        'refresh_token': token['refresh_token'],
        'client_id': env['PROCORE_CLIENT_ID'],
        'client_secret': env['PROCORE_CLIENT_SECRET'],
        'redirect_uri': 'http://localhost:9876/callback'
    })

    if r.status_code == 200:
        with open(CREDS / 'procore_token.json', 'w') as f:
            json.dump(r.json(), f, indent=2)
        print("Token refreshed successfully")
    else:
        print(f"FAILED: {r.status_code} {r.text[:200]}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
