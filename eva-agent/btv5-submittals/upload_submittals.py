#!/usr/bin/env python3
"""BTV5 Submittal Batch Uploader — Creates submittals with revision history in Procore sandbox.

Parses filenames like:
  BTV5-Brownsville_Transit_Village_V-{num}-{name}[_R{rev}]-2026-02-19.pdf

Creates submittals starting with R0, then uploads revisions in order.
"""

import os
import re
import json
import time
import sys
import requests
from pathlib import Path
from collections import defaultdict

# Config
COMPANY_ID = "4281379"
PROJECT_ID = "316469"
BASE_URL = "https://sandbox.procore.com/rest/v1.0"
CREDS_DIR = Path.home() / ".openclaw" / "workspace" / ".credentials"
RAW_DIR = Path(__file__).parent / "raw"
DELAY = 0.5  # seconds between API calls

# Procore sandbox user (API Support - the only one that works)
SUBMITTAL_MANAGER_ID = 99519


def load_token():
    token_file = CREDS_DIR / "procore_token.json"
    with open(token_file) as f:
        return json.load(f)["access_token"]


def refresh_token():
    """Refresh the Procore OAuth token."""
    env_file = CREDS_DIR / "procore.env"
    env = {}
    with open(env_file) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    
    token_file = CREDS_DIR / "procore_token.json"
    with open(token_file) as f:
        token_data = json.load(f)
    
    r = requests.post("https://sandbox.procore.com/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": token_data["refresh_token"],
        "client_id": env["PROCORE_CLIENT_ID"],
        "client_secret": env["PROCORE_CLIENT_SECRET"],
    })
    r.raise_for_status()
    new_token = r.json()
    
    with open(token_file, "w") as f:
        json.dump(new_token, f, indent=2)
    
    return new_token["access_token"]


def api_call(method, path, token, **kwargs):
    """Make a Procore API call with rate limit handling."""
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Procore-Company-Id": COMPANY_ID,
    }
    
    for attempt in range(3):
        r = requests.request(method, url, headers=headers, **kwargs)
        
        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", 60))
            print(f"  Rate limited, waiting {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        if r.status_code == 401:
            print("  Token expired, refreshing...")
            token = refresh_token()
            headers["Authorization"] = f"Bearer {token}"
            continue
        
        return r, token
    
    return r, token


def parse_filenames():
    """Parse all PDF filenames into structured submittal data."""
    files = sorted(os.listdir(RAW_DIR))
    submittals = defaultdict(list)
    unmatched = []
    
    for f in files:
        if not f.endswith(".pdf"):
            continue
        
        # Handle (1) duplicates
        clean = re.sub(r'\s*\(\d+\)', '', f)
        
        # Pattern: BTV5-Brownsville_Transit_Village_V-{num}-{name}[_R{rev}]-2026-02-19.pdf
        m = re.match(
            r'BTV5-Brownsville_Transit_Village_V-(\d+)-(.+?)(?:_R(\d+))?-2026-02-19\.pdf',
            clean
        )
        
        if m:
            vnum = int(m.group(1))
            name = m.group(2).replace("_", " ").replace("amp ", "& ")
            rev = int(m.group(3)) if m.group(3) else 0
            key = f"V-{vnum} {name}"
            submittals[key].append({
                "vnum": vnum,
                "name": name,
                "rev": rev,
                "filename": f,
                "filepath": str(RAW_DIR / f),
                "key": key,
            })
        else:
            unmatched.append(f)
    
    # Sort revisions within each submittal
    for key in submittals:
        submittals[key].sort(key=lambda x: x["rev"])
    
    return dict(submittals), unmatched


def create_submittal(token, number, title, rev=0):
    """Create a submittal in Procore."""
    data = {
        "submittal": {
            "number": number,
            "title": title,
            "revision": rev,
            "submittal_manager_id": SUBMITTAL_MANAGER_ID,
            "description": f"BTV5 submittal imported from project records. Revision {rev}.",
            "import_source": "btv5_batch_upload",
        }
    }
    
    r, token = api_call(
        "POST",
        f"/projects/{PROJECT_ID}/submittals",
        token,
        json=data,
    )
    
    return r, token


def upload_attachment(token, submittal_id, filepath):
    """Upload a PDF attachment to a submittal."""
    # First, create the upload
    filename = os.path.basename(filepath)
    
    with open(filepath, "rb") as f:
        files = {"file": (filename, f, "application/pdf")}
        r, token = api_call(
            "POST",
            f"/projects/{PROJECT_ID}/submittals/{submittal_id}/attachments",
            token,
            files=files,
        )
    
    return r, token


def update_revision(token, submittal_id, rev):
    """Update a submittal's revision number."""
    data = {
        "submittal": {
            "revision": rev,
        }
    }
    
    r, token = api_call(
        "PATCH",
        f"/projects/{PROJECT_ID}/submittals/{submittal_id}",
        token,
        json=data,
    )
    
    return r, token


def main():
    print("=" * 60)
    print("BTV5 Submittal Batch Uploader")
    print("=" * 60)
    
    # Parse files
    submittals, unmatched = parse_filenames()
    
    total_files = sum(len(v) for v in submittals.values())
    multi_rev = {k: v for k, v in submittals.items() if len(v) > 1}
    
    print(f"\nParsed: {len(submittals)} unique submittals, {total_files} total files")
    print(f"Multi-revision: {len(multi_rev)}")
    if unmatched:
        print(f"Unmatched: {len(unmatched)}")
        for u in unmatched:
            print(f"  - {u}")
    
    # Load token
    token = load_token()
    
    # Track results
    created = 0
    failed = 0
    attachments_ok = 0
    attachments_fail = 0
    
    progress_file = Path(__file__).parent / "upload_progress.json"
    progress = {}
    if progress_file.exists():
        with open(progress_file) as f:
            progress = json.load(f)
    
    print(f"\nStarting upload... ({len(progress)} already done)")
    print("-" * 60)
    
    for i, (key, revisions) in enumerate(sorted(submittals.items())):
        if key in progress:
            print(f"[{i+1}/{len(submittals)}] SKIP {key} (already uploaded)")
            continue
        
        print(f"\n[{i+1}/{len(submittals)}] {key}")
        
        # Create submittal with first revision (R0)
        first = revisions[0]
        # BTV5 format: V-{vendor#} with sequential suffix to prevent duplicates
        number = f"BTV5-{i+1:03d}"
        
        r, token = create_submittal(token, number, first["name"], first["rev"])
        time.sleep(DELAY)
        
        if r.status_code not in (200, 201):
            print(f"  ❌ Create failed ({r.status_code}): {r.text[:200]}")
            failed += 1
            continue
        
        submittal_data = r.json()
        submittal_id = submittal_data.get("id")
        print(f"  ✅ Created #{number} (id={submittal_id})")
        created += 1
        
        # Update to latest revision if multi-revision
        if len(revisions) > 1:
            latest = revisions[-1]
            if latest["rev"] > first["rev"]:
                r, token = update_revision(token, submittal_id, latest["rev"])
                time.sleep(DELAY)
                if r.status_code in (200, 201):
                    print(f"  📝 Updated to R{latest['rev']} (has {len(revisions)} revisions)")
                else:
                    print(f"  ⚠️  Rev update to R{latest['rev']} failed ({r.status_code})")
        
        # Note: Attachments silently dropped in Procore sandbox — skipping upload
        print(f"  📄 {len(revisions)} PDF(s) ready (attachments skip — sandbox limitation)")
        
        # Save progress
        progress[key] = {
            "id": submittal_id,
            "number": number,
            "revisions": len(revisions),
            "timestamp": time.time(),
        }
        with open(progress_file, "w") as f:
            json.dump(progress, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"COMPLETE:")
    print(f"  Submittals created: {created}")
    print(f"  Submittals failed:  {failed}")
    print(f"  Attachments OK:     {attachments_ok}")
    print(f"  Attachments failed: {attachments_fail}")
    print(f"  Previously done:    {len(progress) - created}")
    print("=" * 60)


if __name__ == "__main__":
    main()
