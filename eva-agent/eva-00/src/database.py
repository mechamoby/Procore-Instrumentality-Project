"""EVA-00 Database Interface — Query layer for the NERV project database.

This is the core of EVA-00. Every question gets answered through here.
Provides structured query functions that return data with full references.
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
import psycopg2.extras

DB_NAME = os.environ.get("EVA00_DB", "nerv_eva00")
DB_USER = os.environ.get("EVA00_DB_USER", "moby")
DB_HOST = os.environ.get("EVA00_DB_HOST", "localhost")
DB_PORT = os.environ.get("EVA00_DB_PORT", "5432")


def get_conn():
    """Get a database connection."""
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, host=DB_HOST, port=DB_PORT,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


# =============================================================================
# PROJECT QUERIES
# =============================================================================

def list_projects() -> List[Dict]:
    """List all projects in the database."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.name, p.number, p.address,
                       p.project_type, p.status, p.start_date, p.estimated_completion,
                       p.procore_id
                FROM projects p
                ORDER BY p.start_date DESC NULLS LAST
            """)
            return cur.fetchall()


def get_project(project_id: int = None, name: str = None) -> Optional[Dict]:
    """Get a project by ID or name (fuzzy match)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if project_id:
                cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
            elif name:
                cur.execute(
                    "SELECT * FROM projects WHERE name ILIKE %s ORDER BY start_date DESC LIMIT 1",
                    (f"%{name}%",)
                )
            return cur.fetchone()


def get_project_stats(project_id: int) -> Dict:
    """Get summary stats for a project — submittals, RFIs, drawings, etc."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            stats = {}
            for table, label in [
                ("submittals", "submittals"),
                ("rfis", "rfis"),
                ("drawings", "drawings"),
                ("daily_reports", "daily_reports"),
                ("change_orders", "change_orders"),
                ("meetings", "meetings"),
                ("photos", "photos"),
            ]:
                cur.execute(f"SELECT count(*) as cnt FROM {table} WHERE project_id = %s", (project_id,))
                stats[label] = cur.fetchone()["cnt"]
            return stats


# =============================================================================
# SUBMITTAL QUERIES
# =============================================================================

def search_submittals(
    project_id: int = None,
    spec_section: str = None,
    keyword: str = None,
    status: str = None,
    number: str = None,
    limit: int = 25
) -> List[Dict]:
    """Search submittals with flexible filters."""
    conditions = []
    params = []

    if project_id:
        conditions.append("s.project_id = %s")
        params.append(project_id)
    if spec_section:
        conditions.append("(ss.number ILIKE %s OR ss.title ILIKE %s)")
        params.extend([f"%{spec_section}%", f"%{spec_section}%"])
    if keyword:
        conditions.append("(s.title ILIKE %s OR s.description ILIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if status:
        conditions.append("s.status ILIKE %s")
        params.append(f"%{status}%")
    if number:
        conditions.append("s.number ILIKE %s")
        params.append(f"%{number}%")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT s.id, s.number, s.title, s.status, s.revision,
                       s.received_date, s.required_date, s.submitted_date,
                       s.description,
                       ss.number as spec_number, ss.title as spec_title,
                       p.name as project_name, p.number as project_number,
                       c.name as responsible_contractor
                FROM submittals s
                LEFT JOIN spec_sections ss ON s.spec_section_id = ss.id
                LEFT JOIN projects p ON s.project_id = p.id
                LEFT JOIN companies c ON s.responsible_contractor_id = c.id
                {where}
                ORDER BY s.number
                LIMIT %s
            """, params + [limit])
            return cur.fetchall()


def get_submittal_history(submittal_id: int) -> List[Dict]:
    """Get workflow history for a specific submittal."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT swh.*, c.name as actor_name
                FROM submittal_workflow_history swh
                LEFT JOIN contacts c ON swh.actor_id = c.id
                WHERE swh.submittal_id = %s
                ORDER BY swh.action_date
            """, (submittal_id,))
            return cur.fetchall()


def get_submittal_with_similar(submittal_id: int) -> Dict:
    """Get a submittal and find similar ones from other projects (cross-reference)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Get the submittal
            cur.execute("""
                SELECT s.*, ss.number as spec_number, ss.title as spec_title,
                       p.name as project_name
                FROM submittals s
                LEFT JOIN spec_sections ss ON s.spec_section_id = ss.id
                LEFT JOIN projects p ON s.project_id = p.id
                WHERE s.id = %s
            """, (submittal_id,))
            submittal = cur.fetchone()

            if not submittal or not submittal.get("spec_section_id"):
                return {"submittal": submittal, "similar": []}

            # Find similar submittals from OTHER projects with same spec section
            cur.execute("""
                SELECT s.number, s.title, s.status, s.revision,
                       p.name as project_name, p.number as project_number,
                       ss.number as spec_number,
                       s.description
                FROM submittals s
                JOIN spec_sections ss ON s.spec_section_id = ss.id
                JOIN projects p ON s.project_id = p.id
                WHERE ss.number = %s AND s.project_id != %s
                ORDER BY p.start_date DESC
            """, (submittal["spec_number"], submittal["project_id"]))
            similar = cur.fetchall()

            return {"submittal": submittal, "similar": similar}


# =============================================================================
# RFI QUERIES
# =============================================================================

def search_rfis(
    project_id: int = None,
    keyword: str = None,
    status: str = None,
    number: str = None,
    limit: int = 25
) -> List[Dict]:
    """Search RFIs with flexible filters."""
    conditions = []
    params = []

    if project_id:
        conditions.append("r.project_id = %s")
        params.append(project_id)
    if keyword:
        conditions.append("(r.subject ILIKE %s OR r.question ILIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if status:
        conditions.append("r.status ILIKE %s")
        params.append(f"%{status}%")
    if number:
        conditions.append("r.number ILIKE %s")
        params.append(f"%{number}%")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT r.id, r.number, r.subject, r.question, r.status,
                       r.due_date, r.date_initiated,
                       r.cost_impact, r.schedule_impact,
                       p.name as project_name, p.number as project_number
                FROM rfis r
                LEFT JOIN projects p ON r.project_id = p.id
                {where}
                ORDER BY r.number
                LIMIT %s
            """, params + [limit])
            return cur.fetchall()


def get_rfi_with_responses(rfi_id: int) -> Dict:
    """Get an RFI with all its responses."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.*, p.name as project_name
                FROM rfis r
                LEFT JOIN projects p ON r.project_id = p.id
                WHERE r.id = %s
            """, (rfi_id,))
            rfi = cur.fetchone()

            cur.execute("""
                SELECT rr.*, c.name as responder_name
                FROM rfi_responses rr
                LEFT JOIN contacts c ON rr.responder_id = c.id
                WHERE rr.rfi_id = %s
                ORDER BY rr.response_date
            """, (rfi_id,))
            responses = cur.fetchall()

            return {"rfi": rfi, "responses": responses}


def find_similar_rfis(rfi_id: int = None, keyword: str = None, spec_section: str = None) -> List[Dict]:
    """Find similar RFIs across ALL projects — the cross-reference power."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if rfi_id:
                cur.execute("SELECT subject, location FROM rfis WHERE id = %s", (rfi_id,))
                rfi = cur.fetchone()
                if not rfi:
                    return []
                keyword = rfi.get("subject", "")

            conditions = []
            params = []
            if keyword:
                # Split keywords for broader matching
                words = [w for w in keyword.split() if len(w) > 3]
                if words:
                    conditions.append("(" + " OR ".join(["r.subject ILIKE %s" for _ in words]) + ")")
                    params.extend([f"%{w}%" for w in words])

            if not conditions:
                return []

            where = "WHERE " + " AND ".join(conditions)
            if rfi_id:
                where += " AND r.id != %s"
                params.append(rfi_id)

            cur.execute(f"""
                SELECT r.number, r.subject, r.question, r.status,
                       r.location,
                       p.name as project_name, p.number as project_number,
                       (SELECT rr.body FROM rfi_responses rr 
                        WHERE rr.rfi_id = r.id ORDER BY rr.created_at DESC LIMIT 1) as latest_response
                FROM rfis r
                LEFT JOIN projects p ON r.project_id = p.id
                {where}
                ORDER BY r.date_initiated DESC
                LIMIT 10
            """, params)
            return cur.fetchall()


# =============================================================================
# DRAWING QUERIES
# =============================================================================

def search_drawings(
    project_id: int = None,
    discipline: str = None,
    number: str = None,
    keyword: str = None,
    limit: int = 25
) -> List[Dict]:
    """Search drawings."""
    conditions = []
    params = []

    if project_id:
        conditions.append("d.project_id = %s")
        params.append(project_id)
    if discipline:
        conditions.append("d.discipline ILIKE %s")
        params.append(f"%{discipline}%")
    if number:
        conditions.append("d.number ILIKE %s")
        params.append(f"%{number}%")
    if keyword:
        conditions.append("(d.title ILIKE %s OR d.ocr_text ILIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT d.id, d.number, d.title, d.discipline,
                       d.revision, d.set_name,
                       p.name as project_name,
                       (SELECT count(*) FROM drawing_revisions dr WHERE dr.drawing_id = d.id) as revision_count
                FROM drawings d
                LEFT JOIN projects p ON d.project_id = p.id
                {where}
                ORDER BY d.discipline, d.number
                LIMIT %s
            """, params + [limit])
            return cur.fetchall()


# =============================================================================
# COMPANY / CONTACT QUERIES
# =============================================================================

def search_companies(name: str = None, trade: str = None) -> List[Dict]:
    """Search companies/subcontractors."""
    conditions = []
    params = []
    if name:
        conditions.append("c.name ILIKE %s")
        params.append(f"%{name}%")
    if trade:
        conditions.append("c.trade ILIKE %s")
        params.append(f"%{trade}%")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT c.id, c.name, c.trade, c.address, c.phone, c.email,
                       (SELECT count(*) FROM project_companies pc WHERE pc.company_id = c.id) as project_count
                FROM companies c
                {where}
                ORDER BY c.name
                LIMIT 25
            """, params)
            return cur.fetchall()


def get_company_history(company_id: int) -> Dict:
    """Get a company's full history across all projects."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Projects
            cur.execute("""
                SELECT p.name, p.number, pc.role, p.status
                FROM project_companies pc
                JOIN projects p ON pc.project_id = p.id
                WHERE pc.company_id = %s
                ORDER BY p.start_date DESC
            """, (company_id,))
            projects = cur.fetchall()

            # Submittal stats per project
            cur.execute("""
                SELECT p.name as project_name,
                       count(*) as total,
                       count(*) FILTER (WHERE s.status = 'approved') as approved,
                       count(*) FILTER (WHERE s.status = 'rejected') as rejected,
                       avg(s.revision) as avg_revisions
                FROM submittals s
                JOIN projects p ON s.project_id = p.id
                WHERE s.responsible_contractor_id = %s
                GROUP BY p.name
            """, (company_id,))
            submittal_stats = cur.fetchall()

            return {
                "projects": projects,
                "submittal_performance": submittal_stats
            }


# =============================================================================
# CROSS-REFERENCE / SEARCH-ALL
# =============================================================================

def search_all(query: str, project_id: int = None, limit: int = 10) -> Dict:
    """Search across ALL tables — the EVA-00 power query.
    Returns categorized results from submittals, RFIs, drawings, companies, etc.
    """
    results = {}
    
    results["submittals"] = search_submittals(
        project_id=project_id, keyword=query, limit=limit
    )
    results["rfis"] = search_rfis(
        project_id=project_id, keyword=query, limit=limit
    )
    results["drawings"] = search_drawings(
        project_id=project_id, keyword=query, limit=limit
    )
    results["companies"] = search_companies(name=query)

    # Summary
    results["summary"] = {
        "query": query,
        "total_results": sum(len(v) for v in results.values() if isinstance(v, list)),
        "searched_at": datetime.now().isoformat()
    }

    return results


# =============================================================================
# DAILY REPORTS
# =============================================================================

def search_daily_reports(
    project_id: int = None,
    date_from: str = None,
    date_to: str = None,
    keyword: str = None,
    limit: int = 25
) -> List[Dict]:
    """Search daily reports."""
    conditions = []
    params = []

    if project_id:
        conditions.append("dr.project_id = %s")
        params.append(project_id)
    if date_from:
        conditions.append("dr.report_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("dr.report_date <= %s")
        params.append(date_to)
    if keyword:
        conditions.append("(dr.notes ILIKE %s OR dr.weather_notes ILIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT dr.id, dr.report_date, dr.weather, dr.weather_notes,
                       dr.notes, dr.workers_on_site, dr.visitors,
                       p.name as project_name
                FROM daily_reports dr
                LEFT JOIN projects p ON dr.project_id = p.id
                {where}
                ORDER BY dr.report_date DESC
                LIMIT %s
            """, params + [limit])
            return cur.fetchall()


# =============================================================================
# DATABASE STATS
# =============================================================================

def get_database_stats() -> Dict:
    """Get overall database statistics — how much data EVA-00 knows about."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            stats = {}
            tables = [
                "projects", "submittals", "rfis", "drawings", "drawing_revisions",
                "daily_reports", "companies", "contacts", "meetings", "photos",
                "change_orders", "documents", "spec_sections"
            ]
            for table in tables:
                try:
                    cur.execute(f"SELECT count(*) as cnt FROM {table}")
                    stats[table] = cur.fetchone()["cnt"]
                except:
                    stats[table] = 0
            return stats
