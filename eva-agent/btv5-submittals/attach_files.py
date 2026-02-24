#!/usr/bin/env python3
"""BTV5 Attachment Pipeline: Extract attachment URLs from cover sheets,
download actual files, upload to matching Procore sandbox submittals.

Usage: python3 attach_files.py [--dry-run] [--limit N]
"""

import fitz  # PyMuPDF
import json
import os
import re
import sys
import time
import requests
from pathlib import Path
from collections import defaultdict

# Config
CREDS_DIR = Path.home() / ".openclaw" / "workspace" / ".credentials"
PDF_DIR = "/tmp/btv5-fresh/BTV5"
DOWNLOAD_DIR = Path.home() / ".openclaw" / "workspace" / "eva-agent" / "btv5-submittals" / "attachments"
PROJECT_ID = 316469
BASE_URL = "https://sandbox.procore.com/rest/v1.0"
RATE_DELAY = 0.5  # seconds between API calls

# Parse args
DRY_RUN = "--dry-run" in sys.argv
LIMIT = None
for i, arg in enumerate(sys.argv):
    if arg == "--limit" and i + 1 < len(sys.argv):
        LIMIT = int(sys.argv[i + 1])


def load_token():
    return json.load(open(CREDS_DIR / "procore_token.json"))


def refresh_token(token):
    """Refresh OAuth token if needed."""
    env = {}
    for line in open(CREDS_DIR / "procore.env"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v
    
    r = requests.post("https://login-sandbox.procore.com/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
        "client_id": env["PROCORE_CLIENT_ID"],
        "client_secret": env["PROCORE_CLIENT_SECRET"],
    })
    if r.status_code == 200:
        new_token = r.json()
        json.dump(new_token, open(CREDS_DIR / "procore_token.json", "w"), indent=2)
        print("  [Token refreshed]")
        return new_token
    else:
        print(f"  [Token refresh FAILED: {r.status_code}]")
        return token


def api_get(endpoint, token, params=None):
    """GET with auto-refresh."""
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    r = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)
    if r.status_code == 401:
        token = refresh_token(token)
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        r = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)
    time.sleep(RATE_DELAY)
    return r, token


def api_patch_file(endpoint, token, field_name, filepath):
    """PATCH with multipart file upload + auto-refresh."""
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    with open(filepath, "rb") as f:
        files = {field_name: (os.path.basename(filepath), f, "application/pdf")}
        r = requests.patch(f"{BASE_URL}{endpoint}", headers=headers, files=files)
    if r.status_code == 401:
        token = refresh_token(token)
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        with open(filepath, "rb") as f:
            files = {field_name: (os.path.basename(filepath), f, "application/pdf")}
            r = requests.patch(f"{BASE_URL}{endpoint}", headers=headers, files=files)
    time.sleep(RATE_DELAY)
    return r, token


def extract_attachment_urls(pdf_path):
    """Extract unique storage.procore.com download URLs from cover sheet PDF.
    Only extracts from page 1 (submittal attachments, not approver responses)."""
    doc = fitz.open(pdf_path)
    urls = {}
    
    # Only look at page 1 for submittal attachments
    if len(doc) > 0:
        page = doc[0]
        for link in page.get_links():
            uri = link.get("uri", "")
            if "storage.procore.com" in uri:
                # Deduplicate by file ID (path component)
                # Extract file key from URL
                urls[uri] = True
    
    doc.close()
    return list(urls.keys())


def extract_submittal_number(pdf_name):
    """Extract volume and title from PDF filename for matching.
    Format: BTV5-Brownsville_Transit_Village_V-{vol}-{title}-{date}.pdf"""
    # Remove date suffix and extension
    name = re.sub(r'-\d{4}-\d{2}-\d{2}(\s*\(\d+\))?\.pdf$', '', pdf_name)
    # Remove project prefix
    name = re.sub(r'^BTV5-Brownsville_Transit_Village_V-', '', name)
    return name


def download_file(url, dest_path):
    """Download a file from Procore storage URL."""
    r = requests.get(url, allow_redirects=True, stream=True)
    if r.status_code == 200:
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    return False


def get_sandbox_submittals(token):
    """Get all submittals from sandbox with their current attachment counts."""
    submittals = []
    page = 1
    while True:
        r, token = api_get(
            f"/projects/{PROJECT_ID}/submittals",
            token,
            params={"per_page": 100, "page": page}
        )
        if r.status_code != 200:
            print(f"  Error fetching submittals: {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        submittals.extend(batch)
        page += 1
    return submittals, token


def match_pdf_to_submittal(pdf_name, submittals):
    """Try to match a cover sheet PDF to a sandbox submittal by title similarity."""
    pdf_key = extract_submittal_number(pdf_name).lower().replace("_", " ").replace("-", " ")
    
    best_match = None
    best_score = 0
    
    for sub in submittals:
        sub_title = (sub.get("title") or "").lower()
        # Simple word overlap scoring
        pdf_words = set(pdf_key.split())
        sub_words = set(sub_title.split())
        if not pdf_words or not sub_words:
            continue
        overlap = len(pdf_words & sub_words)
        score = overlap / max(len(pdf_words), len(sub_words))
        if score > best_score:
            best_score = score
            best_match = sub
    
    return best_match, best_score


def main():
    print("=" * 60)
    print("BTV5 Attachment Pipeline")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    if LIMIT:
        print(f"Limit: {LIMIT} submittals")
    print("=" * 60)
    
    # Setup
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    token = load_token()
    
    # Get sandbox submittals
    print("\nFetching sandbox submittals...")
    submittals, token = get_sandbox_submittals(token)
    print(f"  Found {len(submittals)} submittals")
    
    # Scan all PDFs
    pdfs = sorted([f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")])
    print(f"  Found {len(pdfs)} cover sheet PDFs")
    
    # Process
    stats = {
        "pdfs_scanned": 0,
        "pdfs_with_attachments": 0,
        "attachments_downloaded": 0,
        "attachments_uploaded": 0,
        "attachments_failed": 0,
        "no_match": 0,
        "already_has_attachments": 0,
        "download_errors": 0,
    }
    
    processed = 0
    for pdf_name in pdfs:
        if LIMIT and processed >= LIMIT:
            break
        
        stats["pdfs_scanned"] += 1
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        
        # Extract attachment URLs
        urls = extract_attachment_urls(pdf_path)
        if not urls:
            continue
        
        stats["pdfs_with_attachments"] += 1
        pdf_key = extract_submittal_number(pdf_name)
        
        # Match to sandbox submittal
        match, score = match_pdf_to_submittal(pdf_name, submittals)
        if not match or score < 0.3:
            stats["no_match"] += 1
            print(f"\n⚠️  No match: {pdf_key} (best score: {score:.2f})")
            continue
        
        sub_id = match["id"]
        sub_title = match.get("title", "?")
        current_attachments = match.get("attachments_count", 0)
        
        print(f"\n📎 {pdf_key}")
        print(f"   → Matched: [{sub_id}] {sub_title} (score: {score:.2f}, existing: {current_attachments})")
        print(f"   → {len(urls)} attachment URL(s) found")
        
        if current_attachments > 0:
            stats["already_has_attachments"] += 1
            print(f"   ⏭️  Already has {current_attachments} attachment(s), skipping")
            continue
        
        processed += 1
        
        for i, url in enumerate(urls):
            # Download
            dl_filename = f"{sub_id}_{i}.pdf"
            dl_path = DOWNLOAD_DIR / dl_filename
            
            if DRY_RUN:
                print(f"   [DRY RUN] Would download {url[:80]}...")
                print(f"   [DRY RUN] Would upload to submittal {sub_id}")
                stats["attachments_downloaded"] += 1
                stats["attachments_uploaded"] += 1
                continue
            
            print(f"   ⬇️  Downloading attachment {i+1}/{len(urls)}...")
            if download_file(url, dl_path):
                size_mb = os.path.getsize(dl_path) / (1024 * 1024)
                print(f"   ✅ Downloaded ({size_mb:.1f} MB)")
                stats["attachments_downloaded"] += 1
                
                # Upload to sandbox
                print(f"   ⬆️  Uploading to submittal {sub_id}...")
                r, token = api_patch_file(
                    f"/projects/{PROJECT_ID}/submittals/{sub_id}",
                    token,
                    "submittal[attachments][]",
                    dl_path
                )
                if r.status_code == 200:
                    new_count = r.json().get("attachments_count", "?")
                    print(f"   ✅ Uploaded! Attachments now: {new_count}")
                    stats["attachments_uploaded"] += 1
                else:
                    print(f"   ❌ Upload failed: {r.status_code} {r.text[:200]}")
                    stats["attachments_failed"] += 1
                
                # Clean up downloaded file to save space
                os.remove(dl_path)
            else:
                print(f"   ❌ Download failed")
                stats["download_errors"] += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
