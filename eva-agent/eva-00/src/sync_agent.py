#!/usr/bin/env python3
"""EVA-00 Procore Sync Agent — Continuously polls Procore and syncs to local PostgreSQL.

Usage: python sync_agent.py [--once]  (--once = single sync pass then exit)
"""

import os
import sys
import json
import time
import signal
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import psycopg2
import psycopg2.extras

# Add our directory to path for procore_client import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from procore_client import ProcoreClient

# =============================================================================
# Configuration
# =============================================================================

DB_NAME = os.environ.get("EVA00_DB", "nerv_eva00")
DB_USER = os.environ.get("EVA00_DB_USER", "moby")
DB_HOST = os.environ.get("EVA00_DB_HOST", "localhost")
DB_PORT = os.environ.get("EVA00_DB_PORT", "5432")

COMPANY_ID = int(os.environ.get("PROCORE_COMPANY_ID", "4281379"))
PROJECT_IDS = [int(x) for x in os.environ.get("PROCORE_PROJECT_IDS", "316469").split(",")]

API_DELAY = float(os.environ.get("SYNC_API_DELAY", "0.6"))  # seconds between API calls

# Poll intervals in seconds
INTERVALS = {
    "projects":           int(os.environ.get("SYNC_INTERVAL_PROJECTS", "3600")),
    "submittals":         int(os.environ.get("SYNC_INTERVAL_SUBMITTALS", "300")),
    "rfis":               int(os.environ.get("SYNC_INTERVAL_RFIS", "300")),
    "drawing_revisions":  int(os.environ.get("SYNC_INTERVAL_DRAWINGS", "900")),
    "companies":          int(os.environ.get("SYNC_INTERVAL_COMPANIES", "3600")),
    "contacts":           int(os.environ.get("SYNC_INTERVAL_CONTACTS", "3600")),
    "documents":          int(os.environ.get("SYNC_INTERVAL_DOCUMENTS", "1800")),
}

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync_agent")

# =============================================================================
# Globals
# =============================================================================

shutdown_requested = False


def handle_signal(signum, frame):
    global shutdown_requested
    log.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown_requested = True


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


# =============================================================================
# Database helpers
# =============================================================================

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, host=DB_HOST, port=DB_PORT,
    )


def payload_hash(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]


def get_cursor(conn, entity_type: str) -> Optional[datetime]:
    """Get last sync time for an entity type."""
    with conn.cursor() as cur:
        cur.execute("SELECT last_synced_at FROM sync_cursors WHERE entity_type = %s", (entity_type,))
        row = cur.fetchone()
        return row[0] if row else None


def set_cursor(conn, entity_type: str, ts: datetime):
    """Update sync cursor."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sync_cursors (entity_type, last_synced_at, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (entity_type) DO UPDATE SET last_synced_at = %s, updated_at = NOW()
        """, (entity_type, ts, ts))
    conn.commit()


def log_sync(conn, entity_type: str, entity_id, procore_id: int, action: str,
             status: str = "success", error_msg: str = None, p_hash: str = None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sync_log (entity_type, entity_id, procore_id, action,
                                  sync_direction, status, error_message, payload_hash, created_at)
            VALUES (%s, %s, %s, %s, 'procore_to_local', %s, %s, %s, NOW())
        """, (entity_type, entity_id, procore_id, action, status, error_msg, p_hash))


def find_by_procore_id(conn, table: str, procore_id: int) -> Optional[str]:
    """Find local UUID by procore_id. Returns id string or None."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {table} WHERE procore_id = %s", (procore_id,))
        row = cur.fetchone()
        return str(row[0]) if row else None


def get_project_uuid(conn, procore_project_id: int) -> Optional[str]:
    return find_by_procore_id(conn, "projects", procore_project_id)


# =============================================================================
# Status mapping helpers
# =============================================================================

SUBMITTAL_STATUS_MAP = {
    "draft": "draft", "open": "open", "submitted": "submitted",
    "under_review": "under_review", "approved": "approved",
    "approved_as_noted": "approved_as_noted",
    "revise_and_resubmit": "revise_and_resubmit",
    "rejected": "rejected", "closed": "closed", "void": "void",
}

RFI_STATUS_MAP = {
    "draft": "draft", "open": "open", "answered": "answered",
    "closed": "closed", "void": "void",
}


def safe_status(raw: str, mapping: dict, default: str) -> str:
    if not raw:
        return default
    key = raw.lower().strip().replace(" ", "_")
    return mapping.get(key, default)


def safe_date(val) -> Optional[str]:
    """Convert a date string or None safely."""
    if not val:
        return None
    if isinstance(val, str):
        return val[:10]  # YYYY-MM-DD
    return str(val)


# =============================================================================
# Sync functions per entity type
# =============================================================================

def sync_projects(client: ProcoreClient, conn):
    """Sync all projects for the company."""
    log.info("Syncing projects...")
    projects = client.get_all("/rest/v1.1/projects", {"company_id": COMPANY_ID})
    time.sleep(API_DELAY)

    created, updated = 0, 0
    for p in projects:
        pid = p["id"]
        existing_id = find_by_procore_id(conn, "projects", pid)

        address = None
        if p.get("address") or p.get("city"):
            address = json.dumps({
                "street": p.get("address", ""),
                "city": p.get("city", ""),
                "state": p.get("state_code", ""),
                "zip": p.get("zip", ""),
            })

        vals = {
            "procore_id": pid,
            "name": p.get("name", "Unnamed"),
            "number": p.get("project_number") or p.get("code"),
            "description": p.get("description"),
            "address": address,
            "status": "active" if p.get("active") else "completed",
            "start_date": safe_date(p.get("start_date")),
            "estimated_completion": safe_date(p.get("projected_finish_date") or p.get("completion_date")),
            "contract_value": p.get("estimated_value") or p.get("total_value"),
            "project_type": p.get("project_type", {}).get("name") if isinstance(p.get("project_type"), dict) else p.get("project_type"),
            "square_footage": p.get("square_feet"),
            "procore_project_id": pid,
            "sync_status": "synced",
            "last_synced_at": datetime.now(timezone.utc),
        }

        with conn.cursor() as cur:
            if existing_id:
                sets = ", ".join(f"{k} = %s" for k in vals)
                cur.execute(f"UPDATE projects SET {sets} WHERE id = %s",
                            list(vals.values()) + [existing_id])
                log_sync(conn, "project", existing_id, pid, "update", p_hash=payload_hash(p))
                updated += 1
            else:
                cols = ", ".join(vals.keys())
                placeholders = ", ".join(["%s"] * len(vals))
                cur.execute(f"INSERT INTO projects ({cols}) VALUES ({placeholders}) RETURNING id",
                            list(vals.values()))
                new_id = str(cur.fetchone()[0])
                log_sync(conn, "project", new_id, pid, "create", p_hash=payload_hash(p))
                created += 1
        conn.commit()

    log.info(f"Projects: {created} created, {updated} updated (total {len(projects)})")
    set_cursor(conn, "projects", datetime.now(timezone.utc))


def sync_companies(client: ProcoreClient, conn):
    """Sync companies (vendors) for the company directory."""
    log.info("Syncing companies...")
    companies = client.get_all("/rest/v1.0/companies", {"company_id": COMPANY_ID})
    time.sleep(API_DELAY)

    # Also get project-level vendors for each project
    for proj_id in PROJECT_IDS:
        try:
            vendors = client.get_all(f"/rest/v1.0/projects/{proj_id}/vendors")
            time.sleep(API_DELAY)
            # Merge — avoid duplicates by id
            existing_ids = {c["id"] for c in companies}
            for v in vendors:
                if v["id"] not in existing_ids:
                    companies.append(v)
                    existing_ids.add(v["id"])
        except Exception as e:
            log.warning(f"Failed to get vendors for project {proj_id}: {e}")

    created, updated = 0, 0
    for c in companies:
        cid = c["id"]
        existing_id = find_by_procore_id(conn, "companies", cid)

        vals = {
            "procore_id": cid,
            "name": c.get("name", "Unknown"),
            "phone": c.get("phone"),
            "email": c.get("email_address") or c.get("email"),
            "website": c.get("website"),
            "sync_status": "synced",
        }
        # Add address if present
        if c.get("address") or c.get("city"):
            vals["address"] = json.dumps({
                "street": c.get("address", ""),
                "city": c.get("city", ""),
                "state": c.get("state_code", ""),
                "zip": c.get("zip", ""),
            })

        with conn.cursor() as cur:
            if existing_id:
                sets = ", ".join(f"{k} = %s" for k in vals)
                cur.execute(f"UPDATE companies SET {sets} WHERE id = %s",
                            list(vals.values()) + [existing_id])
                updated += 1
            else:
                cols = ", ".join(vals.keys())
                placeholders = ", ".join(["%s"] * len(vals))
                cur.execute(f"INSERT INTO companies ({cols}) VALUES ({placeholders}) RETURNING id",
                            list(vals.values()))
                new_id = str(cur.fetchone()[0])
                log_sync(conn, "company", new_id, cid, "create")
                created += 1
        conn.commit()

    log.info(f"Companies: {created} created, {updated} updated (total {len(companies)})")
    set_cursor(conn, "companies", datetime.now(timezone.utc))


def sync_contacts(client: ProcoreClient, conn):
    """Sync users/contacts from project directories."""
    log.info("Syncing contacts...")
    created, updated = 0, 0

    for proj_id in PROJECT_IDS:
        try:
            users = client.get_all(f"/rest/v1.0/projects/{proj_id}/users")
            time.sleep(API_DELAY)
        except Exception as e:
            log.error(f"Failed to get users for project {proj_id}: {e}")
            continue

        for u in users:
            uid = u["id"]
            existing_id = find_by_procore_id(conn, "contacts", uid)

            # Try to link to company
            company_uuid = None
            vendor = u.get("vendor")
            if vendor and isinstance(vendor, dict) and vendor.get("id"):
                company_uuid = find_by_procore_id(conn, "companies", vendor["id"])

            vals = {
                "procore_id": uid,
                "first_name": u.get("first_name", ""),
                "last_name": u.get("last_name", ""),
                "title": u.get("job_title"),
                "email": u.get("email_address"),
                "phone": u.get("business_phone"),
                "mobile": u.get("mobile_phone"),
                "company_id": company_uuid,
                "sync_status": "synced",
            }

            with conn.cursor() as cur:
                if existing_id:
                    sets = ", ".join(f"{k} = %s" for k in vals)
                    cur.execute(f"UPDATE contacts SET {sets} WHERE id = %s",
                                list(vals.values()) + [existing_id])
                    updated += 1
                else:
                    cols = ", ".join(vals.keys())
                    placeholders = ", ".join(["%s"] * len(vals))
                    cur.execute(f"INSERT INTO contacts ({cols}) VALUES ({placeholders}) RETURNING id",
                                list(vals.values()))
                    new_id = str(cur.fetchone()[0])
                    log_sync(conn, "contact", new_id, uid, "create")
                    created += 1
            conn.commit()

    log.info(f"Contacts: {created} created, {updated} updated")
    set_cursor(conn, "contacts", datetime.now(timezone.utc))


def sync_submittals(client: ProcoreClient, conn):
    """Sync submittals for all tracked projects."""
    log.info("Syncing submittals...")
    created, updated = 0, 0

    for proj_id in PROJECT_IDS:
        project_uuid = get_project_uuid(conn, proj_id)
        if not project_uuid:
            log.warning(f"No local project for Procore ID {proj_id}, skipping submittals")
            continue

        try:
            subs = client.get_all(f"/rest/v1.1/projects/{proj_id}/submittals")
            time.sleep(API_DELAY)
        except Exception as e:
            log.error(f"Failed to get submittals for project {proj_id}: {e}")
            continue

        for s in subs:
            sid = s["id"]
            existing_id = find_by_procore_id(conn, "submittals", sid)

            # Map spec section
            spec_num = None
            spec = s.get("specification_section")
            if spec and isinstance(spec, dict):
                spec_num = spec.get("number") or spec.get("label")

            # Map responsible contractor
            rc_uuid = None
            rc = s.get("responsible_contractor")
            if rc and isinstance(rc, dict) and rc.get("id"):
                rc_uuid = find_by_procore_id(conn, "companies", rc["id"])

            status = safe_status(
                s.get("status", {}).get("name") if isinstance(s.get("status"), dict) else s.get("status"),
                SUBMITTAL_STATUS_MAP, "open"
            )

            vals = {
                "project_id": project_uuid,
                "procore_id": sid,
                "number": str(s.get("formatted_number") or s.get("number", "")),
                "revision": s.get("revision", 0) or 0,
                "title": s.get("title", "Untitled"),
                "description": s.get("description") or None,
                "spec_section_number": spec_num,
                "submittal_type": s.get("type", {}).get("name") if isinstance(s.get("type"), dict) else s.get("type"),
                "status": status,
                "submitted_date": safe_date(s.get("distributed_at") or s.get("created_at")),
                "required_date": safe_date(s.get("required_on_site_date")),
                "received_date": safe_date(s.get("received_date")),
                "lead_time_days": s.get("lead_time"),
                "responsible_contractor_id": rc_uuid,
                "import_source": "procore_api",
                "sync_status": "synced",
            }

            with conn.cursor() as cur:
                if existing_id:
                    sets = ", ".join(f"{k} = %s" for k in vals if k != "project_id")
                    update_vals = [v for k, v in vals.items() if k != "project_id"]
                    cur.execute(f"UPDATE submittals SET {sets} WHERE id = %s",
                                update_vals + [existing_id])
                    log_sync(conn, "submittal", existing_id, sid, "update", p_hash=payload_hash(s))
                    updated += 1
                else:
                    cols = ", ".join(vals.keys())
                    placeholders = ", ".join(["%s"] * len(vals))
                    cur.execute(f"INSERT INTO submittals ({cols}) VALUES ({placeholders}) RETURNING id",
                                list(vals.values()))
                    new_id = str(cur.fetchone()[0])
                    log_sync(conn, "submittal", new_id, sid, "create", p_hash=payload_hash(s))
                    created += 1
            conn.commit()

    log.info(f"Submittals: {created} created, {updated} updated")
    set_cursor(conn, "submittals", datetime.now(timezone.utc))


def sync_rfis(client: ProcoreClient, conn):
    """Sync RFIs for all tracked projects."""
    log.info("Syncing RFIs...")
    created, updated = 0, 0

    for proj_id in PROJECT_IDS:
        project_uuid = get_project_uuid(conn, proj_id)
        if not project_uuid:
            log.warning(f"No local project for Procore ID {proj_id}, skipping RFIs")
            continue

        try:
            rfis = client.get_all(f"/rest/v1.0/projects/{proj_id}/rfis")
            time.sleep(API_DELAY)
        except Exception as e:
            log.error(f"Failed to get RFIs for project {proj_id}: {e}")
            continue

        for r in rfis:
            rid = r["id"]
            existing_id = find_by_procore_id(conn, "rfis", rid)

            status = safe_status(r.get("status"), RFI_STATUS_MAP, "open")

            # Extract question from questions array
            question_text = ""
            questions = r.get("questions")
            if questions and isinstance(questions, list):
                bodies = [q.get("body", "") for q in questions if q.get("body")]
                question_text = "\n\n".join(bodies)
            if not question_text:
                question_text = r.get("subject", "No question text")

            # Extract answer from questions (official responses)
            answer_text = None
            if questions and isinstance(questions, list):
                for q in questions:
                    answers = q.get("answers", [])
                    if answers:
                        official = [a for a in answers if a.get("official")]
                        if official:
                            answer_text = official[0].get("body")
                        elif answers:
                            answer_text = answers[-1].get("body")

            # Cost/schedule impact
            cost_impact = False
            cost_amount = None
            ci = r.get("cost_impact")
            if ci and isinstance(ci, dict):
                cost_impact = ci.get("status") == "yes"
                cost_amount = ci.get("value")

            schedule_impact = False
            schedule_days = None
            si = r.get("schedule_impact")
            if si and isinstance(si, dict):
                schedule_impact = si.get("status") == "yes"
                schedule_days = si.get("value")

            # Location
            loc = r.get("location")
            location_str = None
            if loc and isinstance(loc, dict):
                location_str = loc.get("name") or loc.get("path")
            elif isinstance(loc, str):
                location_str = loc

            vals = {
                "project_id": project_uuid,
                "procore_id": rid,
                "number": str(r.get("full_number") or r.get("number", "")),
                "subject": r.get("subject", "Untitled"),
                "question": question_text,
                "status": status,
                "date_initiated": safe_date(r.get("initiated_at") or r.get("created_at")),
                "due_date": safe_date(r.get("due_date")),
                "cost_impact": cost_impact,
                "cost_amount": cost_amount,
                "schedule_impact": schedule_impact,
                "schedule_impact_days": schedule_days,
                "official_answer": answer_text,
                "location": location_str,
                "cost_code": r.get("cost_code", {}).get("name") if isinstance(r.get("cost_code"), dict) else r.get("cost_code"),
                "import_source": "procore_api",
                "sync_status": "synced",
            }

            with conn.cursor() as cur:
                if existing_id:
                    sets = ", ".join(f"{k} = %s" for k in vals if k != "project_id")
                    update_vals = [v for k, v in vals.items() if k != "project_id"]
                    cur.execute(f"UPDATE rfis SET {sets} WHERE id = %s",
                                update_vals + [existing_id])
                    log_sync(conn, "rfi", existing_id, rid, "update", p_hash=payload_hash(r))
                    updated += 1
                else:
                    cols = ", ".join(vals.keys())
                    placeholders = ", ".join(["%s"] * len(vals))
                    cur.execute(f"INSERT INTO rfis ({cols}) VALUES ({placeholders}) RETURNING id",
                                list(vals.values()))
                    new_id = str(cur.fetchone()[0])
                    log_sync(conn, "rfi", new_id, rid, "create", p_hash=payload_hash(r))
                    created += 1
            conn.commit()

    log.info(f"RFIs: {created} created, {updated} updated")
    set_cursor(conn, "rfis", datetime.now(timezone.utc))


def sync_drawing_revisions(client: ProcoreClient, conn):
    """Sync drawing revisions — also creates/updates parent drawings."""
    log.info("Syncing drawing revisions...")
    created_d, updated_d, created_r = 0, 0, 0

    for proj_id in PROJECT_IDS:
        project_uuid = get_project_uuid(conn, proj_id)
        if not project_uuid:
            continue

        try:
            revisions = client.get_all(f"/rest/v1.0/projects/{proj_id}/drawing_revisions")
            time.sleep(API_DELAY)
        except Exception as e:
            log.error(f"Failed to get drawing revisions for project {proj_id}: {e}")
            continue

        for rev in revisions:
            dr_procore_id = rev["id"]
            drawing_procore_id = rev.get("drawing_id")
            number = rev.get("number", "")
            title = rev.get("title", "")
            revision_num = rev.get("revision_number", "0")

            # Discipline mapping
            disc_raw = rev.get("discipline")
            discipline = None
            if disc_raw and isinstance(disc_raw, str):
                disc_lower = disc_raw.lower()
                disc_map = {
                    "architectural": "architectural", "structural": "structural",
                    "mechanical": "mechanical", "electrical": "electrical",
                    "plumbing": "plumbing", "fire_protection": "fire_protection",
                    "civil": "civil", "landscape": "landscape",
                }
                discipline = disc_map.get(disc_lower, "other")

            set_info = rev.get("drawing_set")
            set_name = set_info.get("name") if isinstance(set_info, dict) else None

            # Upsert drawing (parent) using drawing_procore_id
            if drawing_procore_id:
                existing_drawing_id = find_by_procore_id(conn, "drawings", drawing_procore_id)
            else:
                existing_drawing_id = None

            drawing_vals = {
                "project_id": project_uuid,
                "procore_id": drawing_procore_id,
                "number": number or "UNKNOWN",
                "title": title,
                "discipline": discipline,
                "set_name": set_name,
                "revision": str(revision_num),
                "revision_date": safe_date(rev.get("drawing_date")),
                "received_date": safe_date(rev.get("received_date")),
                "current": bool(rev.get("current", False)),
                "sync_status": "synced",
            }

            with conn.cursor() as cur:
                if existing_drawing_id:
                    # Only update if this is current revision
                    if rev.get("current"):
                        sets = ", ".join(f"{k} = %s" for k in drawing_vals if k != "project_id")
                        update_vals = [v for k, v in drawing_vals.items() if k != "project_id"]
                        cur.execute(f"UPDATE drawings SET {sets} WHERE id = %s",
                                    update_vals + [existing_drawing_id])
                        updated_d += 1
                    drawing_uuid = existing_drawing_id
                else:
                    cols = ", ".join(drawing_vals.keys())
                    placeholders = ", ".join(["%s"] * len(drawing_vals))
                    cur.execute(f"INSERT INTO drawings ({cols}) VALUES ({placeholders}) RETURNING id",
                                list(drawing_vals.values()))
                    drawing_uuid = str(cur.fetchone()[0])
                    log_sync(conn, "drawing", drawing_uuid, drawing_procore_id or 0, "create")
                    created_d += 1
                conn.commit()

                # Insert drawing revision record (check if exists by drawing_id + revision)
                cur.execute("""
                    SELECT id FROM drawing_revisions
                    WHERE drawing_id = %s AND revision = %s
                """, (drawing_uuid, str(revision_num)))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO drawing_revisions (drawing_id, revision, revision_date)
                        VALUES (%s, %s, %s)
                    """, (drawing_uuid, str(revision_num), safe_date(rev.get("drawing_date"))))
                    created_r += 1
                conn.commit()

    log.info(f"Drawings: {created_d} created, {updated_d} updated. Revisions: {created_r} created")
    set_cursor(conn, "drawing_revisions", datetime.now(timezone.utc))


def sync_documents(client: ProcoreClient, conn):
    """Sync documents (files/folders from Procore documents tool)."""
    log.info("Syncing documents...")
    created, updated = 0, 0

    for proj_id in PROJECT_IDS:
        project_uuid = get_project_uuid(conn, proj_id)
        if not project_uuid:
            continue

        try:
            docs = client.get_json(f"/rest/v1.0/projects/{proj_id}/documents")
            time.sleep(API_DELAY)
        except Exception as e:
            log.error(f"Failed to get documents for project {proj_id}: {e}")
            continue

        # Recursively fetch folder contents
        all_files = []
        folders_to_process = []
        for d in docs:
            if d.get("document_type") == "folder":
                folders_to_process.append(d["id"])
            elif d.get("document_type") == "file":
                all_files.append(d)

        # Fetch files from subfolders (limit depth to avoid rate limit burn)
        depth = 0
        while folders_to_process and depth < 3:
            next_folders = []
            for fid in folders_to_process:
                if shutdown_requested:
                    break
                try:
                    children = client.get_json(f"/rest/v1.0/projects/{proj_id}/documents", {"filters[parent_id]": fid})
                    time.sleep(API_DELAY)
                    if isinstance(children, list):
                        for c in children:
                            if c.get("document_type") == "file":
                                all_files.append(c)
                            elif c.get("document_type") == "folder":
                                next_folders.append(c["id"])
                except Exception as e:
                    log.warning(f"Failed to fetch folder {fid}: {e}")
            folders_to_process = next_folders
            depth += 1

        for d in all_files:
            did = d["id"]
            existing_id = find_by_procore_id(conn, "documents", did)

            vals = {
                "project_id": project_uuid,
                "procore_id": did,
                "title": d.get("name", "Untitled"),
                "file_name": d.get("name"),
                "file_size_bytes": d.get("size"),
                "category": d.get("name_with_path"),
                "sync_status": "synced",
            }

            with conn.cursor() as cur:
                if existing_id:
                    sets = ", ".join(f"{k} = %s" for k in vals if k != "project_id")
                    update_vals = [v for k, v in vals.items() if k != "project_id"]
                    cur.execute(f"UPDATE documents SET {sets} WHERE id = %s",
                                update_vals + [existing_id])
                    updated += 1
                else:
                    cols = ", ".join(vals.keys())
                    placeholders = ", ".join(["%s"] * len(vals))
                    cur.execute(f"INSERT INTO documents ({cols}) VALUES ({placeholders}) RETURNING id",
                                list(vals.values()))
                    new_id = str(cur.fetchone()[0])
                    log_sync(conn, "document", new_id, did, "create")
                    created += 1
            conn.commit()

    log.info(f"Documents: {created} created, {updated} updated")
    set_cursor(conn, "documents", datetime.now(timezone.utc))


# =============================================================================
# Main sync loop
# =============================================================================

SYNC_FUNCTIONS = {
    "projects": sync_projects,
    "companies": sync_companies,
    "contacts": sync_contacts,
    "submittals": sync_submittals,
    "rfis": sync_rfis,
    "drawing_revisions": sync_drawing_revisions,
    "documents": sync_documents,
}

# Order matters for first run: projects & companies before entities that reference them
SYNC_ORDER = ["projects", "companies", "contacts", "submittals", "rfis", "drawing_revisions", "documents"]


def run_sync_pass(client: ProcoreClient, conn, force_all: bool = False):
    """Run one pass of all sync functions that are due."""
    now = datetime.now(timezone.utc)

    for entity_type in SYNC_ORDER:
        if shutdown_requested:
            break

        interval = INTERVALS.get(entity_type, 3600)
        last_sync = get_cursor(conn, entity_type)

        if not force_all and last_sync:
            elapsed = (now - last_sync).total_seconds()
            if elapsed < interval:
                continue

        func = SYNC_FUNCTIONS[entity_type]
        try:
            func(client, conn)
        except Exception as e:
            log.error(f"Error syncing {entity_type}: {e}", exc_info=True)
            # Continue with next entity type


def main():
    once = "--once" in sys.argv
    log.info("=" * 60)
    log.info("EVA-00 Procore Sync Agent starting")
    log.info(f"Company: {COMPANY_ID} | Projects: {PROJECT_IDS}")
    log.info(f"Mode: {'single pass' if once else 'continuous'}")
    log.info("=" * 60)

    client = ProcoreClient(company_id=COMPANY_ID)
    conn = get_conn()

    # Check if this is first run (no cursors exist)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sync_cursors")
        cursor_count = cur.fetchone()[0]

    first_run = cursor_count == 0
    if first_run:
        log.info("First run detected — performing full initial sync")

    try:
        if once:
            run_sync_pass(client, conn, force_all=True)
            log.info("Single sync pass complete.")
        else:
            # Initial full sync
            run_sync_pass(client, conn, force_all=True)
            log.info("Initial sync complete. Entering polling loop...")

            while not shutdown_requested:
                time.sleep(30)  # Check every 30s if anything is due
                if shutdown_requested:
                    break
                run_sync_pass(client, conn)

    except KeyboardInterrupt:
        log.info("Interrupted.")
    finally:
        conn.close()
        log.info("Sync agent stopped.")


if __name__ == "__main__":
    main()
