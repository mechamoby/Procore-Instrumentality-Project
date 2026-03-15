"""SteelSync Command Center API — CC-1.2 + CC-1.3

REST API endpoints for the Command Center frontend:
- CC-1.2: Procore data (projects, RFIs, submittals, daily logs, schedule, change orders)
- CC-1.3: Intelligence data (signals, intelligence items, synthesis cycles)

All endpoints return consistent JSON with pagination support.
"""

import logging
import os
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Body, File, UploadFile, Form
from fastapi.responses import FileResponse
from steelsync_db import get_cursor, serialize_row, serialize_rows

DOCUMENTS_ROOT = os.environ.get("DOCUMENTS_ROOT", "/home/moby/nerv-data/email-archive")
UPLOADS_ROOT = os.environ.get("UPLOADS_ROOT", "/home/moby/nerv-data/uploads")

ALLOWED_UPLOAD_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.dwg', '.dxf', '.png', '.jpg', '.jpeg', '.tiff', '.csv', '.eml', '.msg'}
EXTENSION_MIME_MAP = {
    '.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.dwg': 'application/dwg', '.dxf': 'application/dxf',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.tiff': 'image/tiff',
    '.csv': 'text/csv', '.eml': 'message/rfc822', '.msg': 'application/vnd.ms-outlook',
}
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

logger = logging.getLogger("steelsync.api")

router = APIRouter(prefix="/api", tags=["command-center"])


# =============================================================================
# UTILITY
# =============================================================================

def paginated_response(rows, total_count: int, limit: int, offset: int):
    """Wrap rows in a standard paginated response."""
    return {
        "data": rows,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_count,
    }


# =============================================================================
# CC-1.2: PROCORE DATA ENDPOINTS
# =============================================================================

@router.get("/projects")
def list_projects(
    status: Optional[str] = Query(None, description="Filter by status: active, completed, archived"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all projects with basic stats."""
    with get_cursor() as cur:
        # Count
        where = "WHERE p.is_deleted = FALSE"
        params = []
        if status:
            where += " AND p.status = %s"
            params.append(status)

        cur.execute(f"SELECT COUNT(*) as cnt FROM projects p {where}", params)
        total = cur.fetchone()["cnt"]

        # Fetch projects with stats
        cur.execute(f"""
            SELECT p.id, p.name, p.number, p.description, p.address, p.status,
                   p.project_type, p.start_date, p.estimated_completion,
                   p.contract_value, p.square_footage, p.procore_id,
                   p.last_synced_at, p.created_at, p.updated_at,
                   (SELECT COUNT(*) FROM rfis r WHERE r.project_id = p.id AND r.is_deleted = FALSE) as rfi_count,
                   (SELECT COUNT(*) FROM submittals s WHERE s.project_id = p.id AND s.is_deleted = FALSE) as submittal_count,
                   (SELECT COUNT(*) FROM daily_reports d WHERE d.project_id = p.id AND d.is_deleted = FALSE) as daily_report_count,
                   (SELECT COUNT(*) FROM change_orders co WHERE co.project_id = p.id AND co.is_deleted = FALSE) as change_order_count,
                   (SELECT COUNT(*) FROM drawings dw WHERE dw.project_id = p.id AND dw.is_deleted = FALSE) as drawing_count
            FROM projects p
            {where}
            ORDER BY p.updated_at DESC NULLS LAST, p.name
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = serialize_rows(cur.fetchall())
        return paginated_response(rows, total, limit, offset)


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    """Get detailed project info."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM rfis r WHERE r.project_id = p.id AND r.is_deleted = FALSE) as rfi_count,
                   (SELECT COUNT(*) FROM submittals s WHERE s.project_id = p.id AND s.is_deleted = FALSE) as submittal_count,
                   (SELECT COUNT(*) FROM daily_reports d WHERE d.project_id = p.id AND d.is_deleted = FALSE) as daily_report_count,
                   (SELECT COUNT(*) FROM change_orders co WHERE co.project_id = p.id AND co.is_deleted = FALSE) as change_order_count,
                   (SELECT COUNT(*) FROM drawings dw WHERE dw.project_id = p.id AND dw.is_deleted = FALSE) as drawing_count,
                   (SELECT COUNT(*) FROM meetings m WHERE m.project_id = p.id AND m.is_deleted = FALSE) as meeting_count
            FROM projects p
            WHERE p.id = %s AND p.is_deleted = FALSE
        """, (project_id,))

        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"data": serialize_row(row)}


@router.get("/projects/{project_id}/rfis")
def list_project_rfis(
    project_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("number", description="Sort by: due_date, date_initiated, number"),
):
    """List RFIs for a project with aging and overdue status."""
    with get_cursor() as cur:
        # Verify project exists
        cur.execute("SELECT id FROM projects WHERE id = %s AND is_deleted = FALSE", (project_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        where = "WHERE r.project_id = %s AND r.is_deleted = FALSE"
        params = [project_id]
        if status:
            where += " AND r.status = %s::rfi_status"
            params.append(status)

        cur.execute(f"SELECT COUNT(*) as cnt FROM rfis r {where}", params)
        total = cur.fetchone()["cnt"]

        # Get status breakdown for accurate stats (unaffected by pagination)
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status NOT IN ('closed', 'answered', 'void')) as open_count,
                COUNT(*) FILTER (WHERE status NOT IN ('closed', 'answered', 'void')
                    AND due_date IS NOT NULL AND due_date < CURRENT_DATE) as overdue_count
            FROM rfis
            WHERE project_id = %s AND is_deleted = FALSE
        """, [project_id])
        counts = cur.fetchone()

        sort_col = {"due_date": "r.due_date", "date_initiated": "r.date_initiated", "number": "CAST(r.number AS INTEGER)"}.get(sort, "CAST(r.number AS INTEGER)")

        cur.execute(f"""
            SELECT r.id, r.number, r.subject, r.question, r.status,
                   r.date_initiated, r.due_date, r.date_answered, r.date_closed,
                   r.cost_impact, r.cost_amount, r.schedule_impact, r.schedule_impact_days,
                   r.location, r.official_answer, r.procore_id,
                   r.created_at, r.updated_at,
                   CASE
                       WHEN r.status IN ('closed', 'answered', 'void') THEN NULL
                       WHEN r.date_initiated IS NOT NULL THEN (CURRENT_DATE - r.date_initiated)
                       ELSE NULL
                   END as days_open,
                   CASE
                       WHEN r.status IN ('closed', 'answered', 'void') THEN FALSE
                       WHEN r.due_date IS NOT NULL AND r.due_date < CURRENT_DATE THEN TRUE
                       ELSE FALSE
                   END as is_overdue
            FROM rfis r
            {where}
            ORDER BY {sort_col} {"DESC" if sort == "number" else "ASC"} NULLS LAST
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = serialize_rows(cur.fetchall())

        # Add Procore deep link actions to each row
        from action_resolver import resolver as action_resolver
        cur.execute("SELECT procore_id FROM projects WHERE id = %s", [project_id])
        ppid_row = cur.fetchone()
        ppid = ppid_row['procore_id'] if ppid_row else None
        for row in rows:
            actions = action_resolver.resolve_for_entity_row("rfi", row.get('procore_id'), ppid)
            row['actions'] = [a.to_dict() for a in actions]

        resp = paginated_response(rows, total, limit, offset)
        resp["open_count"] = counts["open_count"]
        resp["overdue_count"] = counts["overdue_count"]
        return resp


@router.get("/projects/{project_id}/submittals")
def list_project_submittals(
    project_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List submittals for a project with turnaround tracking."""
    with get_cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE id = %s AND is_deleted = FALSE", (project_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        where = "WHERE s.project_id = %s AND s.is_deleted = FALSE"
        params = [project_id]
        if status:
            where += " AND s.status = %s::submittal_status"
            params.append(status)

        cur.execute(f"SELECT COUNT(*) as cnt FROM submittals s {where}", params)
        total = cur.fetchone()["cnt"]

        # Get status breakdown for accurate stats
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status NOT IN ('approved', 'approved_as_noted', 'closed', 'void')) as open_count
            FROM submittals
            WHERE project_id = %s AND is_deleted = FALSE
        """, [project_id])
        sub_counts = cur.fetchone()

        cur.execute(f"""
            SELECT s.id, s.number, s.title, s.description, s.status,
                   s.submittal_type, s.spec_section_number,
                   s.submitted_date, s.required_date, s.received_date, s.returned_date,
                   s.cost_impact, s.cost_amount, s.schedule_impact, s.lead_time_days,
                   s.revision, s.procore_id, s.created_at, s.updated_at,
                   CASE
                       WHEN s.status IN ('approved', 'approved_as_noted', 'closed', 'void') THEN NULL
                       WHEN s.submitted_date IS NOT NULL THEN (CURRENT_DATE - s.submitted_date)
                       ELSE NULL
                   END as days_in_review,
                   CASE
                       WHEN s.status IN ('approved', 'approved_as_noted', 'closed', 'void') THEN FALSE
                       WHEN s.required_date IS NOT NULL AND s.required_date < CURRENT_DATE THEN TRUE
                       ELSE FALSE
                   END as is_overdue
            FROM submittals s
            {where}
            ORDER BY
                CASE WHEN s.status IN ('approved', 'approved_as_noted', 'closed', 'void') THEN 1 ELSE 0 END,
                s.required_date ASC NULLS LAST
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = serialize_rows(cur.fetchall())

        # Add Procore deep link actions to each row
        from action_resolver import resolver as action_resolver
        cur.execute("SELECT procore_id FROM projects WHERE id = %s", [project_id])
        ppid_row = cur.fetchone()
        ppid = ppid_row['procore_id'] if ppid_row else None
        for row in rows:
            actions = action_resolver.resolve_for_entity_row("submittal", row.get('procore_id'), ppid)
            row['actions'] = [a.to_dict() for a in actions]

        resp = paginated_response(rows, total, limit, offset)
        resp["open_count"] = sub_counts["open_count"]
        return resp


@router.get("/projects/{project_id}/daily-logs")
def list_project_daily_logs(
    project_id: str,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List daily logs for a project with compliance status."""
    with get_cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE id = %s AND is_deleted = FALSE", (project_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        cur.execute("SELECT COUNT(*) as cnt FROM daily_reports WHERE project_id = %s AND is_deleted = FALSE", (project_id,))
        total = cur.fetchone()["cnt"]

        cur.execute("""
            SELECT d.id, d.report_date, d.weather, d.work_performed, d.delays,
                   d.safety_notes, d.general_notes, d.total_workers,
                   d.workforce, d.equipment, d.deliveries,
                   d.procore_id, d.created_at, d.updated_at,
                   CASE
                       WHEN d.created_at::date <= d.report_date + INTERVAL '1 day' THEN 'on_time'
                       WHEN d.created_at::date <= d.report_date + INTERVAL '2 days' THEN 'late'
                       ELSE 'very_late'
                   END as compliance_status
            FROM daily_reports d
            WHERE d.project_id = %s AND d.is_deleted = FALSE
            ORDER BY d.report_date DESC
            LIMIT %s OFFSET %s
        """, (project_id, limit, offset))

        rows = serialize_rows(cur.fetchall())
        return paginated_response(rows, total, limit, offset)


@router.get("/projects/{project_id}/schedule")
def list_project_schedule(
    project_id: str,
    milestones_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List schedule activities for a project."""
    with get_cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE id = %s AND is_deleted = FALSE", (project_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        milestone_filter = "AND sa.is_milestone = TRUE" if milestones_only else ""

        cur.execute(f"""
            SELECT COUNT(*) as cnt
            FROM schedule_activities sa
            JOIN schedules sch ON sch.id = sa.schedule_id
            WHERE sch.project_id = %s AND sch.is_current = TRUE AND sch.is_deleted = FALSE
            {milestone_filter}
        """, (project_id,))
        total = cur.fetchone()["cnt"]

        cur.execute(f"""
            SELECT sa.id, sa.activity_id, sa.name, sa.start_date, sa.finish_date,
                   sa.actual_start, sa.actual_finish, sa.duration_days,
                   sa.percent_complete, sa.is_critical, sa.is_milestone,
                   sch.name as schedule_name,
                   CASE
                       WHEN sa.actual_finish IS NOT NULL THEN 'complete'
                       WHEN sa.finish_date < CURRENT_DATE AND sa.actual_finish IS NULL THEN 'overdue'
                       WHEN sa.finish_date <= CURRENT_DATE + INTERVAL '14 days' THEN 'approaching'
                       ELSE 'on_track'
                   END as schedule_status
            FROM schedule_activities sa
            JOIN schedules sch ON sch.id = sa.schedule_id
            WHERE sch.project_id = %s AND sch.is_current = TRUE AND sch.is_deleted = FALSE
            {milestone_filter}
            ORDER BY sa.start_date ASC NULLS LAST
            LIMIT %s OFFSET %s
        """, (project_id, limit, offset))

        rows = serialize_rows(cur.fetchall())
        return paginated_response(rows, total, limit, offset)


@router.get("/projects/{project_id}/change-orders")
def list_project_change_orders(
    project_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List change orders for a project with financial summary."""
    with get_cursor() as cur:
        cur.execute("SELECT id FROM projects WHERE id = %s AND is_deleted = FALSE", (project_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        where = "WHERE co.project_id = %s AND co.is_deleted = FALSE"
        params = [project_id]
        if status:
            where += " AND co.status = %s::change_order_status"
            params.append(status)

        cur.execute(f"SELECT COUNT(*) as cnt FROM change_orders co {where}", params)
        total = cur.fetchone()["cnt"]

        # Financial summary
        cur.execute(f"""
            SELECT COALESCE(SUM(co.amount), 0) as total_amount,
                   COALESCE(SUM(CASE WHEN co.status = 'approved' THEN co.amount ELSE 0 END), 0) as approved_amount,
                   COALESCE(SUM(CASE WHEN co.status = 'pending' THEN co.amount ELSE 0 END), 0) as pending_amount
            FROM change_orders co
            {where}
        """, params)
        financial = serialize_row(cur.fetchone())

        cur.execute(f"""
            SELECT co.id, co.number, co.title, co.description, co.status,
                   co.change_reason, co.amount, co.schedule_impact_days,
                   co.date_initiated, co.date_approved,
                   co.procore_id, co.created_at, co.updated_at
            FROM change_orders co
            {where}
            ORDER BY co.date_initiated DESC NULLS LAST
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = serialize_rows(cur.fetchall())
        response = paginated_response(rows, total, limit, offset)
        response["financial_summary"] = financial
        return response


# =============================================================================
# CC-1.3: INTELLIGENCE DATA ENDPOINTS
# =============================================================================

def _check_intel_tables_exist(cur) -> bool:
    """Check if intelligence layer tables have been created."""
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'signals'
        ) as exists
    """)
    return cur.fetchone()["exists"]


@router.get("/projects/{project_id}/signals")
def list_project_signals(
    project_id: str,
    signal_category: Optional[str] = Query(None),
    signal_type: Optional[str] = Query(None),
    hours: int = Query(72, ge=1, le=720, description="Look back N hours"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List recent signals for a project. Default: last 72 hours, not archived."""
    with get_cursor() as cur:
        if not _check_intel_tables_exist(cur):
            return paginated_response([], 0, limit, offset)

        cur.execute("SELECT id FROM projects WHERE id = %s AND is_deleted = FALSE", (project_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        where = "WHERE s.project_id = %s AND s.archived_at IS NULL AND s.created_at > NOW() - INTERVAL '%s hours'"
        params = [project_id, hours]

        if signal_category:
            where += " AND s.signal_category = %s::signal_category"
            params.append(signal_category)
        if signal_type:
            where += " AND s.signal_type = %s"
            params.append(signal_type)

        cur.execute(f"SELECT COUNT(*) as cnt FROM signals s {where}", params)
        total = cur.fetchone()["cnt"]

        cur.execute(f"""
            SELECT s.id, s.project_id, s.source_type, s.source_document_id,
                   s.signal_type, s.signal_category, s.summary,
                   s.confidence, s.strength, s.effective_weight,
                   s.decay_profile, s.entity_type, s.entity_value,
                   s.supporting_context_json, s.last_reinforced_at,
                   s.created_at, s.resolved_at
            FROM signals s
            {where}
            ORDER BY s.effective_weight DESC, s.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = serialize_rows(cur.fetchall())
        return paginated_response(rows, total, limit, offset)


@router.get("/projects/{project_id}/intelligence-items")
def list_intelligence_items(
    project_id: str,
    item_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="Filter: new, active, watch, resolved, archived"),
    include: Optional[str] = Query(None, description="Set to 'evidence' to include evidence chain"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List intelligence items for a project. Default: active + watch items."""
    with get_cursor() as cur:
        if not _check_intel_tables_exist(cur):
            return paginated_response([], 0, limit, offset)

        cur.execute("SELECT id FROM projects WHERE id = %s AND is_deleted = FALSE", (project_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        where = "WHERE i.project_id = %s"
        params = [project_id]

        if status:
            where += " AND i.status = %s::intelligence_status"
            params.append(status)
        else:
            where += " AND i.status IN ('new', 'active', 'watch')"

        if item_type:
            where += " AND i.item_type = %s::intelligence_item_type"
            params.append(item_type)
        if severity:
            where += " AND i.severity = %s::intelligence_severity"
            params.append(severity)

        cur.execute(f"SELECT COUNT(*) as cnt FROM intelligence_items i {where}", params)
        total = cur.fetchone()["cnt"]

        cur.execute(f"""
            SELECT i.id, i.project_id, i.item_type, i.title, i.summary,
                   i.severity, i.confidence, i.status,
                   i.first_created_at, i.last_updated_at, i.last_reinforced_at,
                   i.resolved_at, i.synthesis_cycle_id,
                   i.source_evidence_count, i.recommended_attention_level,
                   i.delivery_channels_json
            FROM intelligence_items i
            {where}
            ORDER BY
                CASE i.severity
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                i.last_updated_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = serialize_rows(cur.fetchall())

        # Check which items are Radar-linked (have radar_match evidence signals)
        if rows:
            item_ids = [r["id"] for r in rows]
            placeholders = ",".join(["%s"] * len(item_ids))

            # Find items linked to Radar via evidence signals
            cur.execute(f"""
                SELECT DISTINCT e.intelligence_item_id,
                       s.supporting_context_json->>'radar_item_id' as radar_item_id,
                       s.supporting_context_json->>'radar_title' as radar_title
                FROM intelligence_item_evidence e
                JOIN signals s ON s.id = e.signal_id
                WHERE e.intelligence_item_id IN ({placeholders})
                  AND s.signal_category = 'radar_match'
            """, item_ids)

            radar_link_map = {}
            for rl in serialize_rows(cur.fetchall()):
                iid = rl["intelligence_item_id"]
                radar_link_map.setdefault(iid, []).append({
                    "radar_item_id": rl["radar_item_id"],
                    "radar_title": rl["radar_title"],
                })

            for row in rows:
                linked = radar_link_map.get(row["id"], [])
                row["radar_linked"] = len(linked) > 0
                row["linked_radar_items"] = linked

        # Optionally include evidence chain
        if include == "evidence" and rows:
            placeholders = ",".join(["%s"] * len(item_ids))
            cur.execute(f"""
                SELECT e.intelligence_item_id, e.id as evidence_id,
                       e.evidence_weight_level, e.added_at, e.notes,
                       s.id as signal_id, s.signal_type, s.signal_category,
                       s.summary as signal_summary, s.source_type,
                       s.confidence as signal_confidence, s.created_at as signal_created_at
                FROM intelligence_item_evidence e
                JOIN signals s ON s.id = e.signal_id
                WHERE e.intelligence_item_id IN ({placeholders})
                ORDER BY e.added_at DESC
            """, item_ids)

            evidence_map = {}
            for ev in serialize_rows(cur.fetchall()):
                item_id = ev.pop("intelligence_item_id")
                evidence_map.setdefault(item_id, []).append(ev)

            for row in rows:
                row["evidence"] = evidence_map.get(row["id"], [])

        # Resolve actions for each item
        from action_resolver import resolver as action_resolver
        cur.execute("SELECT procore_id FROM projects WHERE id = %s", [project_id])
        proj_row = cur.fetchone()
        ppid = proj_row['procore_id'] if proj_row else None
        for row in rows:
            # Extract entity info from evidence signals if available
            entity_type = (row.get('item_type') or '').replace('_', '')
            procore_id = None
            signal_cat = ''
            supporting_ctx = {}
            if row.get('evidence'):
                for ev in row['evidence']:
                    if ev.get('source_type'):
                        entity_type = ev['source_type']
                    signal_cat = signal_cat or ev.get('signal_category', '')
            actions = action_resolver.resolve(
                entity_type=entity_type, procore_id=procore_id,
                procore_project_id=ppid, signal_category=signal_cat,
                supporting_context=supporting_ctx,
                project_name=row.get('project_name', ''),
                title=row.get('title', ''), summary=row.get('summary', ''),
            )
            row['actions'] = [a.to_dict() for a in actions]

        return paginated_response(rows, total, limit, offset)


@router.get("/projects/{project_id}/intelligence-items/{item_id}")
def get_intelligence_item(project_id: str, item_id: str):
    """Get a single intelligence item with full evidence chain."""
    with get_cursor() as cur:
        if not _check_intel_tables_exist(cur):
            raise HTTPException(status_code=404, detail="Intelligence layer not initialized")

        cur.execute("""
            SELECT i.*
            FROM intelligence_items i
            WHERE i.id = %s AND i.project_id = %s
        """, (item_id, project_id))

        item = cur.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Intelligence item not found")

        item = serialize_row(item)

        # Get evidence chain
        cur.execute("""
            SELECT e.id as evidence_id, e.evidence_weight_level, e.added_at, e.notes,
                   s.id as signal_id, s.signal_type, s.signal_category,
                   s.summary as signal_summary, s.source_type, s.entity_type,
                   s.entity_value, s.confidence as signal_confidence,
                   s.supporting_context_json, s.created_at as signal_created_at
            FROM intelligence_item_evidence e
            JOIN signals s ON s.id = e.signal_id
            WHERE e.intelligence_item_id = %s
            ORDER BY e.added_at DESC
        """, (item_id,))

        item["evidence"] = serialize_rows(cur.fetchall())
        return {"data": item}


@router.get("/synthesis/cycles")
def list_synthesis_cycles(
    project_id: Optional[str] = Query(None),
    cycle_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List recent synthesis cycles."""
    with get_cursor() as cur:
        if not _check_intel_tables_exist(cur):
            return paginated_response([], 0, limit, offset)

        where_parts = []
        params = []

        if project_id:
            where_parts.append("sc.project_id = %s")
            params.append(project_id)
        if cycle_type:
            where_parts.append("sc.cycle_type = %s::synthesis_cycle_type")
            params.append(cycle_type)

        where = "WHERE " + " AND ".join(where_parts) if where_parts else ""

        cur.execute(f"SELECT COUNT(*) as cnt FROM synthesis_cycles sc {where}", params)
        total = cur.fetchone()["cnt"]

        cur.execute(f"""
            SELECT sc.id, sc.project_id, sc.cycle_type,
                   sc.started_at, sc.completed_at,
                   sc.signals_processed, sc.items_created, sc.items_updated, sc.items_resolved,
                   sc.cycle_summary, sc.overall_health,
                   sc.model_used, sc.input_tokens, sc.output_tokens,
                   sc.error_log,
                   p.name as project_name
            FROM synthesis_cycles sc
            JOIN projects p ON p.id = sc.project_id
            {where}
            ORDER BY sc.started_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = serialize_rows(cur.fetchall())
        return paginated_response(rows, total, limit, offset)


@router.get("/dashboard/overview")
def dashboard_overview():
    """Aggregated view across all projects for the multi-project dashboard.

    Returns project count, active intelligence items by severity,
    last synthesis cycle time per project, overall health per project.
    """
    with get_cursor() as cur:
        # Get all active projects with basic counts
        cur.execute("""
            SELECT p.id, p.name, p.number, p.status, p.project_type,
                   p.start_date, p.estimated_completion, p.contract_value,
                   p.updated_at,
                   (SELECT COUNT(*) FROM rfis r WHERE r.project_id = p.id AND r.is_deleted = FALSE AND r.status NOT IN ('closed', 'answered', 'void')) as open_rfis,
                   (SELECT COUNT(*) FROM submittals s WHERE s.project_id = p.id AND s.is_deleted = FALSE AND s.status NOT IN ('approved', 'approved_as_noted', 'closed', 'void')) as open_submittals,
                   (SELECT COUNT(*) FROM change_orders co WHERE co.project_id = p.id AND co.is_deleted = FALSE AND co.status = 'pending') as pending_change_orders,
                   (SELECT COUNT(*) FROM rfis r WHERE r.project_id = p.id AND r.is_deleted = FALSE AND r.status NOT IN ('closed', 'answered', 'void') AND r.due_date < CURRENT_DATE) as overdue_rfis,
                   (SELECT COUNT(*) FROM documents d WHERE d.project_id = p.id AND d.is_deleted = FALSE) as document_count
            FROM projects p
            WHERE p.is_deleted = FALSE AND p.status = 'active'
            ORDER BY p.name
        """)
        projects = serialize_rows(cur.fetchall())

        # If intelligence tables exist, add intelligence data
        intel_available = _check_intel_tables_exist(cur)
        if intel_available:
            for proj in projects:
                pid = proj["id"]

                # Intelligence items by severity
                cur.execute("""
                    SELECT severity, COUNT(*) as cnt
                    FROM intelligence_items
                    WHERE project_id = %s AND status IN ('new', 'active')
                    GROUP BY severity
                """, (pid,))
                severity_counts = {r["severity"]: r["cnt"] for r in cur.fetchall()}
                proj["intelligence"] = {
                    "critical": severity_counts.get("critical", 0),
                    "high": severity_counts.get("high", 0),
                    "medium": severity_counts.get("medium", 0),
                    "low": severity_counts.get("low", 0),
                    "total_active": sum(severity_counts.values()),
                }

                # Last synthesis cycle
                cur.execute("""
                    SELECT id, cycle_type, completed_at, overall_health
                    FROM synthesis_cycles
                    WHERE project_id = %s AND completed_at IS NOT NULL
                    ORDER BY completed_at DESC
                    LIMIT 1
                """, (pid,))
                last_cycle = cur.fetchone()
                proj["last_synthesis"] = serialize_row(last_cycle)
        else:
            for proj in projects:
                proj["intelligence"] = {
                    "critical": 0, "high": 0, "medium": 0, "low": 0, "total_active": 0
                }
                proj["last_synthesis"] = None

        # Aggregate stats
        total_open_rfis = sum(p.get("open_rfis", 0) for p in projects)
        total_overdue_rfis = sum(p.get("overdue_rfis", 0) for p in projects)
        total_open_submittals = sum(p.get("open_submittals", 0) for p in projects)
        total_pending_cos = sum(p.get("pending_change_orders", 0) for p in projects)

        return {
            "data": {
                "project_count": len(projects),
                "projects": projects,
                "aggregates": {
                    "open_rfis": total_open_rfis,
                    "overdue_rfis": total_overdue_rfis,
                    "open_submittals": total_open_submittals,
                    "pending_change_orders": total_pending_cos,
                },
                "intelligence_available": intel_available,
            }
        }


# =============================================================================
# SYNTHESIS TRIGGER ENDPOINTS
# =============================================================================

# In-memory job tracking (prototype; use Redis in production)
_synthesis_jobs: dict = {}


@router.post("/synthesis/trigger")
def trigger_synthesis(
    project_id: str = Query(...),
    cycle_type: str = Query("morning_briefing"),
):
    """Trigger a manual synthesis cycle. Returns immediately with job_id."""
    import threading

    job_id = str(__import__("uuid").uuid4())
    _synthesis_jobs[job_id] = {"status": "running", "project_id": project_id, "cycle_type": cycle_type}

    def _run():
        try:
            from synthesis_engine import SynthesisEngine
            cycle_id = SynthesisEngine.run_cycle(project_id, cycle_type)
            _synthesis_jobs[job_id] = {
                "status": "completed",
                "cycle_id": cycle_id,
                "project_id": project_id,
                "cycle_type": cycle_type,
            }
        except Exception as e:
            _synthesis_jobs[job_id] = {
                "status": "failed",
                "error": str(e),
                "project_id": project_id,
            }
            logger.error(f"Synthesis job {job_id} failed: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "running"}


@router.get("/synthesis/status/{job_id}")
def synthesis_status(job_id: str):
    """Poll synthesis job status."""
    job = _synthesis_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/synthesis/sweep")
def trigger_signal_sweep(project_id: str = Query(...)):
    """Trigger a deterministic signal sweep for a project."""
    try:
        from signal_generation import run_deterministic_sweep
        results = run_deterministic_sweep(project_id)
        return {"status": "completed", "results": results}
    except Exception as e:
        logger.error(f"Signal sweep failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesis/decay")
def trigger_decay_cycle(project_id: str = Query(...)):
    """Run working memory lifecycle: decay signals and manage item states."""
    try:
        from synthesis_engine import SynthesisEngine
        results = SynthesisEngine.run_decay_cycle(project_id)
        return {"status": "completed", "results": results}
    except Exception as e:
        logger.error(f"Decay cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deep-dive")
def trigger_deep_dive(
    item_id: str = Query(..., description="Intelligence item UUID to deep-dive"),
):
    """Trigger an escalation review synthesis for a specific intelligence item.

    Queues an escalation_review cycle focused on the given item and its related
    signals/items. Returns a job_id for polling via /synthesis/status/{job_id}.
    """
    import threading

    # Validate item exists and get its project_id
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, project_id FROM intelligence_items WHERE id = %s",
            (item_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Intelligence item not found")
        project_id = str(row["project_id"])

    job_id = str(__import__("uuid").uuid4())
    _synthesis_jobs[job_id] = {
        "status": "running",
        "project_id": project_id,
        "cycle_type": "escalation_review",
        "item_id": item_id,
    }

    def _run():
        try:
            from synthesis_engine import SynthesisEngine
            cycle_id = SynthesisEngine.run_cycle(
                project_id, "escalation_review", escalation_item_id=item_id
            )
            _synthesis_jobs[job_id] = {
                "status": "completed",
                "cycle_id": cycle_id,
                "project_id": project_id,
                "cycle_type": "escalation_review",
                "item_id": item_id,
            }
        except Exception as e:
            _synthesis_jobs[job_id] = {
                "status": "failed",
                "error": str(e),
                "project_id": project_id,
                "item_id": item_id,
            }
            logger.error(f"Deep dive job {job_id} failed: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "running", "item_id": item_id}


@router.post("/deep-dive/requests")
def deep_dive_request(body: dict = Body(...)):
    """Deep Dive pipeline — synchronous Opus analysis with context assembly."""
    import uuid
    import time
    import json as json_mod
    import httpx

    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    OPUS_MODEL = os.environ.get("SYNTHESIS_MODEL", "claude-opus-4-20250514")

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    project_id = body.get("project_id")
    linked_item_id = body.get("linked_item_id")
    trigger_type = body.get("trigger_type", "user_open")
    concern_description = body.get("concern_description")
    focus_areas = body.get("focus_areas", [])
    additional_context = body.get("additional_context")
    focus_steering = body.get("focus_steering")

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    start_time = time.time()

    with get_cursor() as cur:
        # Validate project
        cur.execute("SELECT id, name, number FROM projects WHERE id = %s", [project_id])
        project = cur.fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Write request record
        request_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO deep_dive_requests (id, project_id, linked_item_id, trigger_type,
                concern_description, focus_areas, additional_context, focus_steering, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'processing')
        """, [request_id, project_id, linked_item_id, trigger_type,
              concern_description, focus_areas, additional_context, focus_steering])

        # === LAYER 2: Context Assembly ===
        escalation_item = {}
        related_items = []
        supporting_signals = []
        project_snapshot = {}

        # Project snapshot
        cur.execute("""
            SELECT p.name, p.number, p.status, p.start_date, p.estimated_completion, p.contract_value,
                   (SELECT COUNT(*) FROM rfis r WHERE r.project_id = p.id AND r.is_deleted = FALSE AND r.status NOT IN ('closed','answered','void')) as open_rfis,
                   (SELECT COUNT(*) FROM submittals s WHERE s.project_id = p.id AND s.is_deleted = FALSE AND s.status NOT IN ('approved','approved_as_noted','closed','void')) as open_submittals,
                   (SELECT COUNT(*) FROM change_orders co WHERE co.project_id = p.id AND co.is_deleted = FALSE AND co.status = 'pending') as pending_cos
            FROM projects p WHERE p.id = %s
        """, [project_id])
        ps = cur.fetchone()
        project_snapshot = {
            "project_name": ps['name'], "project_number": ps['number'],
            "status": ps['status'],
            "start_date": str(ps['start_date']) if ps['start_date'] else None,
            "estimated_completion": str(ps['estimated_completion']) if ps['estimated_completion'] else None,
            "contract_value": float(ps['contract_value']) if ps['contract_value'] else None,
            "open_rfis": ps['open_rfis'], "open_submittals": ps['open_submittals'],
            "pending_change_orders": ps['pending_cos'],
        }

        if _check_intel_tables_exist(cur):
            # Item counts by severity
            cur.execute("""
                SELECT severity, COUNT(*) as cnt FROM intelligence_items
                WHERE project_id = %s AND status IN ('new','active','watch')
                GROUP BY severity
            """, [project_id])
            project_snapshot["intelligence_items"] = {r['severity']: r['cnt'] for r in cur.fetchall()}

            # Signal counts by category (last 7 days)
            cur.execute("""
                SELECT signal_category, COUNT(*) as cnt FROM signals
                WHERE project_id = %s AND created_at > NOW() - INTERVAL '7 days' AND archived_at IS NULL
                GROUP BY signal_category
            """, [project_id])
            project_snapshot["recent_signals"] = {r['signal_category']: r['cnt'] for r in cur.fetchall()}

            if linked_item_id:
                # Item-linked mode
                cur.execute("""
                    SELECT id, title, summary, severity, confidence, status, item_type,
                           first_created_at, last_updated_at, source_evidence_count
                    FROM intelligence_items WHERE id = %s
                """, [linked_item_id])
                item_row = cur.fetchone()
                if item_row:
                    escalation_item = serialize_row(item_row)
                    # Get evidence chain
                    cur.execute("""
                        SELECT s.summary, s.signal_category, s.confidence, s.entity_type,
                               s.entity_value, s.created_at
                        FROM intelligence_item_evidence e
                        JOIN signals s ON s.id = e.signal_id
                        WHERE e.intelligence_item_id = %s
                        ORDER BY e.added_at DESC
                    """, [linked_item_id])
                    escalation_item["evidence_chain"] = serialize_rows(cur.fetchall())

                # Related items
                cur.execute("""
                    SELECT id, title, summary, severity, confidence, status
                    FROM intelligence_items
                    WHERE project_id = %s AND status IN ('new','active','watch') AND id != %s
                    ORDER BY last_updated_at DESC LIMIT 5
                """, [project_id, linked_item_id])
                related_items = serialize_rows(cur.fetchall())
            else:
                # Open-trigger mode
                escalation_item = {
                    "title": (concern_description or "")[:100],
                    "summary": concern_description or "",
                    "severity": "unknown", "confidence": 0,
                    "source": "user_request", "evidence_chain": [],
                }
                cur.execute("""
                    SELECT id, title, summary, severity, confidence, status
                    FROM intelligence_items
                    WHERE project_id = %s AND status IN ('new','active','watch')
                    ORDER BY last_updated_at DESC LIMIT 10
                """, [project_id])
                related_items = serialize_rows(cur.fetchall())

            # Supporting signals (last 7 days)
            cur.execute("""
                SELECT summary, signal_category, confidence, entity_type, entity_value, created_at
                FROM signals
                WHERE project_id = %s AND created_at > NOW() - INTERVAL '7 days' AND archived_at IS NULL
                ORDER BY created_at DESC LIMIT 50
            """, [project_id])
            supporting_signals = serialize_rows(cur.fetchall())

        # === Build Template D Prompt ===
        # === LAYER 2b: Drawing Analysis (if relevant) ===
        import re as re_mod
        import base64

        drawing_analysis = None
        drawing_cost = 0.0

        combined_text = f"{concern_description or ''} {' '.join(focus_areas or [])} {additional_context or ''} {focus_steering or ''}"

        # Drawing relevance detection
        drawing_pattern = r'\b([A-Z]{1,3}[-.]?\d{1,4}[.-]\d{1,3}[A-Za-z]?)\b'
        detected_numbers = list(set(re_mod.findall(drawing_pattern, combined_text)))
        drawing_keywords = ['drawing', 'drawings', 'sheet', 'plan', 'plans', 'detail', 'section', 'elevation',
            'coordinated', 'coordination', 'conflicts', 'clash', 'aligned', 'alignment', 'verify',
            'location', 'locations', 'pad', 'transformer', 'equipment', 'layout', 'setback',
            'dimension', 'dimensions', 'clearance', 'height', 'width', 'spacing',
            'civil', 'structural', 'mechanical', 'electrical', 'plumbing', 'architectural',
            'site plan', 'floor plan', 'roof plan', 'foundation']
        detected_kws = [kw for kw in drawing_keywords if kw.lower() in combined_text.lower()]
        discipline_map = {'architectural': 'architectural', 'civil': 'civil', 'structural': 'structural',
            'mechanical': 'mechanical', 'electrical': 'electrical', 'plumbing': 'plumbing',
            'landscape': 'landscape', 'fire protection': 'fire_protection'}
        detected_discs = [v for k, v in discipline_map.items() if k in combined_text.lower()]

        involves_drawings = bool(detected_numbers) or len(detected_kws) >= 2

        if involves_drawings:
            logger.info(f"[Deep Dive] Drawing analysis triggered: numbers={detected_numbers}, disciplines={detected_discs}, keywords={detected_kws[:5]}")

            # Select relevant drawings (max 5)
            drawing_where = "WHERE d.project_id = %s AND d.current = TRUE AND d.is_deleted = FALSE"
            drawing_params = [project_id]
            # Get full drawing index for the project
            cur.execute("""
                SELECT d.id, d.number, d.title, d.discipline, d.revision, d.project_id
                FROM drawings d
                WHERE d.project_id = %s AND d.current = TRUE AND d.is_deleted = FALSE
                ORDER BY d.number ASC
            """, [project_id])
            all_project_drawings = [dict(r) for r in cur.fetchall()]

            if not all_project_drawings:
                logger.info("[Deep Dive] No drawings found for project, skipping drawing analysis")
                involves_drawings = False
            else:
                # Opus selects the best drawings (text-only, cheap)
                drawing_index = "\n".join(
                    f"{d['number']} | {d['title']} | {str(d['discipline']) if d['discipline'] else ''} | Rev {d['revision'] or '0'}"
                    for d in all_project_drawings
                )
                selection_prompt = f"""You are a Senior Construction PM reviewing drawings for a project analysis.

The PM has raised this concern:
"{concern_description or combined_text}"

Focus areas: {', '.join(focus_areas) if focus_areas else 'General'}
Additional context: {additional_context or 'None'}

Here is the complete drawing index for this project:

NUMBER | TITLE | DISCIPLINE | REVISION
{drawing_index}

Select exactly 5 drawings that would contain the information needed to evaluate this concern.

Think like a PM: if you were walking to the plan table to answer this question, which sheets would you pull?

RULES:
- Do NOT select cover sheets, indexes, abbreviations, or general notes unless the question specifically asks about them.
- Prefer detail sheets, sections, elevations, and plans that show the actual construction being questioned.
- If the concern involves coordination between disciplines, select drawings from EACH relevant discipline.
- If the concern mentions a specific area or system, select drawings that show that area or system.

Respond with ONLY a JSON array of drawing numbers, most relevant first:
["S-3.01", "A-2.01", "A-5.03", "S-5.02", "A-1.02"]"""

                selected_drawings = []
                try:
                    logger.info("[Deep Dive] Calling Opus for drawing selection")
                    sel_resp = httpx.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={"model": OPUS_MODEL, "max_tokens": 256, "messages": [{"role": "user", "content": selection_prompt}]},
                        timeout=60.0,
                    )
                    sel_resp.raise_for_status()
                    sel_data = sel_resp.json()
                    sel_text = "".join(b.get("text", "") for b in sel_data.get("content", []) if b.get("type") == "text").strip()
                    sel_usage = sel_data.get("usage", {})
                    sel_cost = sel_usage.get("input_tokens", 0) * 0.015 / 1000 + sel_usage.get("output_tokens", 0) * 0.075 / 1000
                    drawing_cost += sel_cost
                    logger.info(f"[Deep Dive] Drawing selection response: {sel_text} (${sel_cost:.4f})")

                    # Parse JSON array from response
                    import json as json_parser
                    # Find JSON array in response
                    arr_start = sel_text.find('[')
                    arr_end = sel_text.rfind(']') + 1
                    if arr_start >= 0 and arr_end > arr_start:
                        selected_numbers = json_parser.loads(sel_text[arr_start:arr_end])
                    else:
                        selected_numbers = []

                    # Match to actual drawing records
                    number_to_drawing = {d['number']: d for d in all_project_drawings}
                    for num in selected_numbers:
                        if num in number_to_drawing and len(selected_drawings) < 5:
                            selected_drawings.append(number_to_drawing[num])

                    logger.info(f"[Deep Dive] Opus selected {len(selected_drawings)} drawings: {[d['number'] for d in selected_drawings]}")

                except Exception as sel_err:
                    logger.error(f"[Deep Dive] Drawing selection failed, falling back to discipline filter: {sel_err}")
                    # Fallback: filter by discipline, skip X-0.xx sheets
                    for d in all_project_drawings:
                        if len(selected_drawings) >= 5:
                            break
                        num_parts = d['number'].split('-')
                        if len(num_parts) >= 2 and not num_parts[1].startswith('0'):
                            if not detected_discs or (d.get('discipline') and str(d['discipline']) in detected_discs):
                                selected_drawings.append(d)

            # Prepare PNGs for all drawings first (fast, local)
            import fitz as fitz_mod
            vision_tasks = []
            for drw in selected_drawings:
                cache_dir = Path(DRAWING_CACHE_ROOT) / str(drw['project_id'])
                pdf_path = cache_dir / f"{drw['number']}_rev{drw['revision'] or '0'}.pdf"
                png_path = cache_dir / f"{drw['number']}_rev{drw['revision'] or '0'}.page1.png"
                if not png_path.exists() and pdf_path.exists():
                    doc = fitz_mod.open(str(pdf_path))
                    pg = doc[0]
                    pix = pg.get_pixmap(matrix=fitz_mod.Matrix(1.5, 1.5))
                    pix.save(str(png_path))
                    doc.close()
                if png_path.exists():
                    vision_tasks.append((drw, png_path))
                else:
                    logger.warning(f"[Deep Dive] No PNG for drawing {drw['number']}")

            # Parallel Vision API calls via ThreadPoolExecutor
            def _analyze_drawing(task):
                drw, png_path = task
                try:
                    png_data = png_path.read_bytes()
                    b64_img = base64.b64encode(png_data).decode('utf-8')
                    vision_query = f"Construction drawing analysis: {concern_description or combined_text}\n\nFor drawing {drw['number']} ({drw['title']}), identify relevant details, dimensions, locations, notes, and any items related to the query. Be specific — cite grid lines, dimensions, notes by number."
                    vision_resp = httpx.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={
                            "model": OPUS_MODEL, "max_tokens": 1024,
                            "messages": [{"role": "user", "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64_img}},
                                {"type": "text", "text": vision_query},
                            ]}],
                        },
                        timeout=90.0,
                    )
                    vision_resp.raise_for_status()
                    vision_data = vision_resp.json()
                    vision_usage = vision_data.get("usage", {})
                    vision_text = "".join(b.get("text", "") for b in vision_data.get("content", []) if b.get("type") == "text")
                    call_cost = vision_usage.get("input_tokens", 0) * 0.003 / 1000 + vision_usage.get("output_tokens", 0) * 0.015 / 1000
                    logger.info(f"[Deep Dive] Vision analysis done for {drw['number']} (${call_cost:.4f})")
                    return {
                        "drawing_number": drw['number'], "title": drw['title'] or '',
                        "discipline": str(drw['discipline']) if drw['discipline'] else '',
                        "revision": f"Rev {drw['revision'] or '0'}",
                        "analysis": vision_text.strip(), "confidence": "high",
                        "model_used": "opus", "cost": round(call_cost, 4),
                    }
                except Exception as ve:
                    logger.error(f"[Deep Dive] Vision analysis failed for {drw['number']}: {ve}")
                    return None

            from concurrent.futures import ThreadPoolExecutor
            analyses = []
            if vision_tasks:
                logger.info(f"[Deep Dive] Running {len(vision_tasks)} vision calls in parallel")
                with ThreadPoolExecutor(max_workers=5) as executor:
                    results = list(executor.map(_analyze_drawing, vision_tasks))
                analyses = [r for r in results if r is not None]
                drawing_cost = sum(a['cost'] for a in analyses)

            if analyses:
                drawing_analysis = {
                    "drawings_analyzed": analyses,
                    "total_cost": round(drawing_cost, 4),
                    "drawings_available_but_not_analyzed": max(0, len(selected_drawings) - len(analyses)),
                }
                logger.info(f"[Deep Dive] Drawing analysis complete: {len(analyses)} drawings, ${drawing_cost:.4f}")

        system_prompt = """You are SteelSync, an AI Senior Project Manager for commercial construction. You perform deep-dive escalation analysis on concerns flagged by the intelligence pipeline or requested by the PM.

Your analysis must be:
- Evidence-based: every claim must reference specific signals, documents, or data points
- Construction-aware: understand trade dependencies, critical path implications, and GC risk exposure
- Actionable: recommendations must be specific enough for a PM to act on immediately
- Honest about uncertainty: clearly state assumptions and identify missing information

Output your analysis as a JSON object matching this exact schema:
{
  "escalation_assessment": {
    "justified": true/false,
    "confidence": "high" | "medium" | "low",
    "evidence_quality": "strong" | "moderate" | "weak" | "insufficient",
    "impact_assessment": "2-4 sentence plain language impact summary",
    "recommended_actions": ["specific action 1", "specific action 2", ...],
    "assumptions": ["assumption 1", "assumption 2", ...]
  },
  "evidence_chain": [
    {
      "signal_summary": "what was detected",
      "evidence_weight": "primary" | "supporting" | "circumstantial",
      "source_reliability": "high" | "medium" | "low",
      "source_reference": "where this came from"
    }
  ],
  "related_context": {
    "cross_project_relevance": "any cross-project patterns or null",
    "historical_patterns": "any historical patterns observed",
    "missing_information": "what additional data would strengthen this analysis"
  },
  "updated_intelligence_item": {
    "action": "update" | "escalate" | "downgrade" | "resolve" | "none",
    "reason": "why this action is recommended"
  }
}

DRAWING EVIDENCE RULES:
- If drawing analysis evidence is provided in <drawing_analysis>, treat it as PRIMARY evidence —
  it represents what the actual construction drawings show, not secondhand reports.
- Cross-discipline conflicts identified in drawing analysis are HIGH SIGNIFICANCE findings.
- When drawing evidence contradicts signal-based evidence, the drawings take precedence.
  Drawings are the contract documents.
- Always cite specific drawing numbers, revisions, and the relevant detail when referencing
  drawing evidence in your assessment.
- If drawings were analyzed but no conflicts were found, that is a POSITIVE finding worth
  reporting — "coordination verified across [disciplines] based on [drawing numbers]."

Respond ONLY with the JSON object. No markdown, no explanation outside the JSON."""

        user_prompt = f"""Analyze this concern for escalation:

<escalation_item>
{json_mod.dumps(escalation_item, default=str)}
</escalation_item>

<related_items>
{json_mod.dumps(related_items, default=str)}
</related_items>

<supporting_signals>
{json_mod.dumps(supporting_signals, default=str)}
</supporting_signals>

<project_snapshot>
{json_mod.dumps(project_snapshot, default=str)}
</project_snapshot>

<cross_project_context>
[]
</cross_project_context>"""

        # Add drawing analysis context if available
        if drawing_analysis:
            user_prompt += f"""

<drawing_analysis>
{json_mod.dumps(drawing_analysis, default=str)}
</drawing_analysis>"""

        # Add user directive
        if focus_areas or additional_context or focus_steering:
            directive = "\n<user_directive>\n"
            if focus_steering:
                directive += f'Specific focus requested: "{focus_steering}"\n\n'
            if focus_areas:
                focus_labels = {
                    'schedule_impact': 'Schedule Impact', 'cost_exposure': 'Cost Exposure',
                    'trade_dependencies': 'Trade Dependencies', 'document_gaps': 'Document Gaps',
                    'recommended_actions': 'Recommended Actions', 'risk_assessment': 'Risk Assessment',
                }
                areas_str = ', '.join(focus_labels.get(f, f) for f in focus_areas)
                directive += f"The requesting user has asked this analysis to focus on:\n{areas_str}\n\n"
            if additional_context:
                directive += f'Additional context from the user:\n"{additional_context}"\n\n'
            directive += "Weight your analysis toward the requested focus areas.\nIf the user provided additional context, incorporate it but note that user-provided context is unverified.\n</user_directive>"
            user_prompt += directive

        # === LAYER 3: Opus API Call ===
        logger.info(f"[Deep Dive] Calling Opus for request {request_id}")
        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": OPUS_MODEL,
                    "max_tokens": 4096,
                    "system": [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=180.0,
            )
            response.raise_for_status()
            data = response.json()

            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            logger.info(f"[Deep Dive] Opus tokens: input={input_tokens}, output={output_tokens}")

            # Parse response
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:])
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            try:
                result = json_mod.loads(text)
            except json_mod.JSONDecodeError:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    result = json_mod.loads(text[start:end])
                else:
                    raise

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[Deep Dive] Failed: {e}")
            cur.execute("""
                UPDATE deep_dive_requests SET status = 'failed', error_message = %s,
                       completed_at = NOW(), processing_duration_ms = %s WHERE id = %s
            """, [str(e), duration_ms, request_id])
            return {"request_id": request_id, "status": "failed", "error": str(e)}

        # === LAYER 4: Result Storage ===
        duration_ms = int((time.time() - start_time) * 1000)
        result_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO deep_dive_results (id, request_id, escalation_assessment, evidence_chain,
                related_context, updated_item_action, input_tokens, output_tokens, model_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            result_id, request_id,
            json_mod.dumps(result.get("escalation_assessment", {})),
            json_mod.dumps(result.get("evidence_chain", [])),
            json_mod.dumps(result.get("related_context")),
            json_mod.dumps(result.get("updated_intelligence_item")),
            input_tokens, output_tokens, OPUS_MODEL,
        ])

        cur.execute("""
            UPDATE deep_dive_requests SET status = 'completed', completed_at = NOW(),
                   processing_duration_ms = %s WHERE id = %s
        """, [duration_ms, request_id])

        logger.info(f"[Deep Dive] Completed in {duration_ms}ms — {input_tokens} in, {output_tokens} out")

        return {
            "request_id": request_id,
            "status": "completed",
            "result": result,
            "processing_duration_ms": duration_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "drawing_analysis": drawing_analysis,
            "drawing_cost": drawing_cost,
        }


@router.post("/documents/refire-signals")
def refire_document_signals(body: dict = Body(...)):
    """CC-2.4: Re-fire signal generation after PM confirms project assignment.

    Body: {document_id, confirmed_project_id, classification_data, extraction_data?}
    """
    document_id = body.get("document_id")
    confirmed_project_id = body.get("confirmed_project_id")
    classification_data = body.get("classification_data", {})
    extraction_data = body.get("extraction_data")

    if not document_id or not confirmed_project_id:
        raise HTTPException(status_code=400, detail="document_id and confirmed_project_id required")

    try:
        from signal_generation import refire_signals_for_document
        result = refire_signals_for_document(
            document_id=document_id,
            confirmed_project_id=confirmed_project_id,
            classification_data=classification_data,
            extraction_data=extraction_data,
        )
        return {"data": result}
    except Exception as e:
        logger.error(f"Document signal refire failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/stats")
def signal_stats(project_id: Optional[str] = Query(None)):
    """Signal generation statistics."""
    with get_cursor() as cur:
        if not _check_intel_tables_exist(cur):
            return {"data": {"total_today": 0, "by_category": {}, "by_source": {}}}

        where = ""
        params = []
        if project_id:
            where = "AND project_id = %s"
            params.append(project_id)

        cur.execute(f"""
            SELECT COUNT(*) as total
            FROM signals
            WHERE created_at > CURRENT_DATE {where}
        """, params)
        total = cur.fetchone()["cnt"] if False else cur.fetchone()["total"]

        cur.execute(f"""
            SELECT signal_category::text as cat, COUNT(*) as cnt
            FROM signals
            WHERE created_at > CURRENT_DATE {where}
            GROUP BY signal_category
        """, params)
        by_category = {r["cat"]: r["cnt"] for r in cur.fetchall()}

        cur.execute(f"""
            SELECT source_type::text as src, COUNT(*) as cnt
            FROM signals
            WHERE created_at > CURRENT_DATE {where}
            GROUP BY source_type
        """, params)
        by_source = {r["src"]: r["cnt"] for r in cur.fetchall()}

        return {
            "data": {
                "total_today": total,
                "by_category": by_category,
                "by_source": by_source,
            }
        }


@router.get("/signals/recent")
def recent_signals(
    limit: int = Query(20, ge=1, le=100),
):
    """Cross-project recent signals for the activity feed."""
    with get_cursor() as cur:
        if not _check_intel_tables_exist(cur):
            return {"data": []}

        cur.execute("""
            SELECT s.id, s.project_id, s.signal_category, s.summary,
                   s.effective_weight, s.created_at,
                   p.name as project_name
            FROM signals s
            LEFT JOIN projects p ON p.id = s.project_id
            WHERE s.archived_at IS NULL
            ORDER BY s.created_at DESC
            LIMIT %s
        """, [limit])
        return {"data": serialize_rows(cur.fetchall())}


@router.get("/activity/recent")
def recent_activity(
    limit: int = Query(30, ge=1, le=100),
):
    """Unified activity feed: webhook events + signals, newest first."""
    with get_cursor() as cur:
        activities = []

        # Webhook events (real-time Procore changes) — enrich with document titles + person
        cur.execute("""
            SELECT w.id, w.event_type, w.procore_resource, w.procore_id,
                   w.procore_project_id, w.status, w.created_at,
                   w.payload->>'user_id' as user_procore_id,
                   p.name as project_name,
                   r.number as rfi_number, r.subject as rfi_subject,
                   sub.number as sub_number, sub.title as sub_title
            FROM webhook_events w
            LEFT JOIN projects p ON p.procore_id = w.procore_project_id
            LEFT JOIN rfis r ON r.procore_id = w.procore_id AND w.procore_resource = 'rfis'
            LEFT JOIN submittals sub ON sub.procore_id = w.procore_id AND w.procore_resource = 'submittals'
            WHERE w.status = 'completed'
            ORDER BY w.created_at DESC
            LIMIT %s
        """, [limit])
        webhook_rows = cur.fetchall()

        # Deduplicate: Procore fires both create+update for the same resource
        # within milliseconds. Drop the 'update' when a 'create' exists for the
        # same resource+procore_id within 5 seconds.
        create_times = {}
        for row in webhook_rows:
            if row['event_type'] == 'create':
                key = (row['procore_resource'], row['procore_id'])
                create_times[key] = row['created_at']
        deduped_rows = []
        for row in webhook_rows:
            if row['event_type'] == 'update':
                key = (row['procore_resource'], row['procore_id'])
                ct = create_times.get(key)
                if ct and abs((row['created_at'] - ct).total_seconds()) < 5:
                    continue  # skip phantom update that accompanies a create
            deduped_rows.append(row)
        webhook_rows = deduped_rows

        # Batch-resolve user names from contacts
        user_ids = set(r['user_procore_id'] for r in webhook_rows if r.get('user_procore_id'))
        user_names = {}
        if user_ids:
            placeholders = ','.join(['%s'] * len(user_ids))
            cur.execute(f"""
                SELECT procore_id, first_name || ' ' || last_name as full_name
                FROM contacts WHERE procore_id IN ({placeholders})
            """, [int(uid) for uid in user_ids])
            user_names = {str(r['procore_id']): r['full_name'] for r in cur.fetchall()}

        for row in webhook_rows:
            resource = row['procore_resource'] or ''
            event = row['event_type'] or ''
            person = user_names.get(row.get('user_procore_id', ''), '')
            procore_project_id = row['procore_project_id']
            procore_id = row['procore_id']
            # Build rich summary
            if resource == 'rfis' and row.get('rfi_number'):
                summary = f"RFI #{row['rfi_number']} {event}d — {row.get('rfi_subject', '')}"
            elif resource == 'submittals' and row.get('sub_number'):
                summary = f"Submittal #{row['sub_number']} {event}d — {row.get('sub_title', '')}"
            else:
                summary = f"{resource.replace('_', ' ').title()} #{procore_id} — {event}d"
            # Build Procore deep link (sandbox environment)
            procore_url = None
            company_id = row.get('user_procore_id') and (row.get('payload_company_id') or '4281379')
            # Extract company_id from webhook payload if available
            procore_base = "https://sandbox.procore.com/webclients/host/companies/4281379/projects"
            if procore_project_id and procore_id:
                if resource == 'rfis':
                    procore_url = f"{procore_base}/{procore_project_id}/tools/rfis/{procore_id}"
                elif resource == 'submittals':
                    procore_url = f"{procore_base}/{procore_project_id}/tools/submittals/{procore_id}"
                elif resource == 'daily logs':
                    procore_url = f"{procore_base}/{procore_project_id}/tools/daily_log"
                else:
                    resource_path = resource.replace(' ', '_')
                    procore_url = f"{procore_base}/{procore_project_id}/tools/{resource_path}/{procore_id}"
            activities.append({
                "type": "webhook",
                "summary": summary.strip(' —'),
                "project_name": row['project_name'] or '',
                "person": person,
                "project_id": None,
                "procore_url": procore_url,
                "created_at": row['created_at'].isoformat() if row['created_at'] else '',
                "is_critical": False,
            })

        # Signals (intelligence layer detections) — deduplicated by summary, with Procore links
        if _check_intel_tables_exist(cur):
            cur.execute("""
                SELECT DISTINCT ON (LEFT(s.summary, 80))
                       s.id, s.signal_category, s.summary, s.effective_weight,
                       s.entity_type, s.entity_value, s.source_document_id,
                       s.created_at, p.name as project_name, s.project_id,
                       p.procore_id as procore_project_id,
                       r.procore_id as rfi_procore_id,
                       r.status as rfi_status,
                       sub.procore_id as sub_procore_id,
                       sub.status as sub_status
                FROM signals s
                LEFT JOIN projects p ON p.id = s.project_id
                LEFT JOIN rfis r ON r.id = s.source_document_id AND s.entity_type = 'rfi'
                LEFT JOIN submittals sub ON sub.id = s.source_document_id AND s.entity_type = 'submittal'
                WHERE s.archived_at IS NULL
                ORDER BY LEFT(s.summary, 80), s.created_at DESC
            """, [])
            procore_base = "https://sandbox.procore.com/webclients/host/companies/4281379/projects"
            for row in cur.fetchall():
                # Skip signals for documents that have been closed/resolved
                if row.get('rfi_status') in ('closed', 'answered', 'void'):
                    continue
                if row.get('sub_status') in ('approved', 'approved_as_noted', 'closed', 'void'):
                    continue

                is_critical = (row.get('signal_category') == 'contradiction' or
                               (row.get('effective_weight') and row['effective_weight'] > 0.8))
                # Build Procore link for signals that reference specific documents
                procore_url = None
                ppid = row.get('procore_project_id')
                if ppid:
                    if row.get('rfi_procore_id'):
                        procore_url = f"{procore_base}/{ppid}/tools/rfis/{row['rfi_procore_id']}"
                    elif row.get('sub_procore_id'):
                        procore_url = f"{procore_base}/{ppid}/tools/submittals/{row['sub_procore_id']}"
                activities.append({
                    "type": "signal",
                    "summary": row['summary'] or '',
                    "project_name": row['project_name'] or '',
                    "project_id": str(row['project_id']) if row['project_id'] else '',
                    "procore_url": procore_url,
                    "created_at": row['created_at'].isoformat() if row['created_at'] else '',
                    "is_critical": is_critical,
                })

        # Portal uploads (documents uploaded via Command Center)
        cur.execute("""
            SELECT d.id, d.title, d.file_name, d.doc_type, d.created_at,
                   p.name as project_name, d.project_id
            FROM documents d
            LEFT JOIN projects p ON p.id = d.project_id
            WHERE d.is_deleted = FALSE
              AND d.category = 'portal_upload'
            ORDER BY d.created_at DESC
            LIMIT %s
        """, [limit])
        for row in cur.fetchall():
            activities.append({
                "type": "upload",
                "summary": f"Document uploaded — {row['file_name'] or row['title']}",
                "project_name": row['project_name'] or '',
                "project_id": str(row['project_id']) if row['project_id'] else '',
                "procore_url": None,
                "document_id": str(row['id']),
                "created_at": row['created_at'].isoformat() if row['created_at'] else '',
                "is_critical": False,
            })

        # Sort by created_at DESC
        activities.sort(key=lambda a: a['created_at'], reverse=True)

        # Deduplicate: collapse create+update webhook pairs for same resource,
        # and collapse signals with similar summaries
        seen_webhooks = set()  # (resource_key)
        seen_summaries = set()
        deduped = []
        for a in activities:
            if a['type'] == 'webhook':
                # Key by resource type + procore_id (strip "created"/"updated" distinction)
                parts = a['summary'].split(' — ', 1)
                resource_key = parts[0].rsplit(' ', 1)[0] if parts else a['summary'][:40]
                if resource_key in seen_webhooks:
                    continue
                seen_webhooks.add(resource_key)
            else:
                key = a['summary'][:60]
                if key in seen_summaries:
                    continue
                seen_summaries.add(key)
            deduped.append(a)
            if len(deduped) >= limit:
                break

        return {"data": deduped}


# =============================================================================
# =============================================================================
# CROSS-PROJECT SEARCH
# =============================================================================

@router.get("/search")
def cross_project_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    types: Optional[str] = Query(None, description="Comma-separated entity types to include"),
    project_id: Optional[str] = Query(None, description="Filter to a specific project UUID"),
    status: Optional[str] = Query(None, description="Filter by status: open, closed, any"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search across RFIs, submittals, drawings, documents, intelligence items, and contacts."""
    with get_cursor() as cur:
        results = {}
        procore_base = "https://sandbox.procore.com/webclients/host/companies/4281379/projects"
        search_term = f"%{q}%"
        active_types = set(types.split(",")) if types else {"rfis", "submittals", "drawings", "documents", "intelligence", "contacts"}
        proj_filter = ""
        proj_params: list = []
        if project_id:
            proj_filter = " AND {alias}.project_id = %s"
            proj_params = [project_id]

        # --- RFIs ---
        if "rfis" in active_types:
            status_clause = ""
            if status == "open":
                status_clause = " AND r.status NOT IN ('closed')"
            elif status == "closed":
                status_clause = " AND r.status = 'closed'"
            pf = proj_filter.format(alias="r")
            cur.execute(f"""
                SELECT COUNT(*) as cnt FROM rfis r
                JOIN projects p ON p.id = r.project_id
                WHERE r.is_deleted = FALSE
                  AND (r.subject ILIKE %s OR r.question ILIKE %s OR r.official_answer ILIKE %s
                       OR r.number = %s){pf}{status_clause}
            """, [search_term, search_term, search_term, q.strip()] + proj_params)
            rfi_total = cur.fetchone()["cnt"]
            cur.execute(f"""
                SELECT r.id, r.number, r.subject, r.status, r.due_date,
                       r.procore_id, r.project_id, p.name as project_name, p.procore_id as procore_project_id,
                       CASE WHEN r.status NOT IN ('closed','answered','void')
                            AND r.due_date IS NOT NULL AND r.due_date < CURRENT_DATE
                            THEN TRUE ELSE FALSE END as is_overdue
                FROM rfis r
                JOIN projects p ON p.id = r.project_id
                WHERE r.is_deleted = FALSE
                  AND (r.subject ILIKE %s OR r.question ILIKE %s OR r.official_answer ILIKE %s
                       OR r.number = %s){pf}{status_clause}
                ORDER BY r.created_at DESC
                LIMIT %s
            """, [search_term, search_term, search_term, q.strip()] + proj_params + [limit])
            rows = []
            for row in cur.fetchall():
                r = dict(row)
                ppid = r.pop('procore_project_id', None)
                if ppid and r.get('procore_id'):
                    r['procore_url'] = f"{procore_base}/{ppid}/tools/rfis/{r['procore_id']}"
                rows.append(r)
            if rows or rfi_total > 0:
                results['rfis'] = {"total_count": rfi_total, "results": rows}

        # --- Submittals ---
        if "submittals" in active_types:
            status_clause = ""
            if status == "open":
                status_clause = " AND s.status NOT IN ('closed')"
            elif status == "closed":
                status_clause = " AND s.status = 'closed'"
            pf = proj_filter.format(alias="s")
            cur.execute(f"""
                SELECT COUNT(*) as cnt FROM submittals s
                JOIN projects p ON p.id = s.project_id
                WHERE s.is_deleted = FALSE
                  AND (s.title ILIKE %s OR s.description ILIKE %s OR s.number = %s){pf}{status_clause}
            """, [search_term, search_term, q.strip()] + proj_params)
            sub_total = cur.fetchone()["cnt"]
            cur.execute(f"""
                SELECT s.id, s.number, s.title, s.status, s.required_date,
                       s.procore_id, s.project_id, p.name as project_name, p.procore_id as procore_project_id
                FROM submittals s
                JOIN projects p ON p.id = s.project_id
                WHERE s.is_deleted = FALSE
                  AND (s.title ILIKE %s OR s.description ILIKE %s OR s.number = %s){pf}{status_clause}
                ORDER BY s.created_at DESC
                LIMIT %s
            """, [search_term, search_term, q.strip()] + proj_params + [limit])
            rows = []
            for row in cur.fetchall():
                r = dict(row)
                ppid = r.pop('procore_project_id', None)
                if ppid and r.get('procore_id'):
                    r['procore_url'] = f"{procore_base}/{ppid}/tools/submittals/{r['procore_id']}"
                rows.append(r)
            if rows or sub_total > 0:
                results['submittals'] = {"total_count": sub_total, "results": rows}

        # --- Drawings ---
        if "drawings" in active_types:
            status_clause = ""
            if status == "open":
                status_clause = " AND d.current = TRUE"
            elif status == "closed":
                status_clause = " AND d.current = FALSE"
            pf = proj_filter.format(alias="d")
            cur.execute(f"""
                SELECT COUNT(*) as cnt FROM drawings d
                JOIN projects p ON p.id = d.project_id
                WHERE d.is_deleted = FALSE
                  AND (d.number ILIKE %s OR d.title ILIKE %s OR d.set_name ILIKE %s
                       OR d.discipline::text ILIKE %s OR d.number = %s){pf}{status_clause}
            """, [search_term, search_term, search_term, search_term, q.strip()] + proj_params)
            draw_total = cur.fetchone()["cnt"]
            cur.execute(f"""
                SELECT d.id, d.number, d.title, d.discipline, d.set_name,
                       d.revision, d.revision_date, d.current as is_current,
                       d.procore_id, d.project_id, p.name as project_name, p.procore_id as procore_project_id
                FROM drawings d
                JOIN projects p ON p.id = d.project_id
                WHERE d.is_deleted = FALSE
                  AND (d.number ILIKE %s OR d.title ILIKE %s OR d.set_name ILIKE %s
                       OR d.discipline::text ILIKE %s OR d.number = %s){pf}{status_clause}
                ORDER BY d.created_at DESC
                LIMIT %s
            """, [search_term, search_term, search_term, search_term, q.strip()] + proj_params + [limit])
            rows = []
            for row in cur.fetchall():
                r = dict(row)
                ppid = r.pop('procore_project_id', None)
                if ppid and r.get('procore_id'):
                    r['procore_url'] = f"{procore_base}/{ppid}/tools/drawings"
                if r.get('discipline'):
                    r['discipline'] = str(r['discipline'])
                rows.append(r)
            if rows or draw_total > 0:
                results['drawings'] = {"total_count": draw_total, "results": rows}

        # --- Documents ---
        if "documents" in active_types:
            pf = proj_filter.format(alias="d")
            cur.execute(f"""
                SELECT COUNT(*) as cnt FROM documents d
                LEFT JOIN projects p ON p.id = d.project_id
                WHERE d.is_deleted = FALSE
                  AND (d.title ILIKE %s OR d.description ILIKE %s
                       OR d.file_name ILIKE %s OR d.category ILIKE %s){pf}
            """, [search_term, search_term, search_term, search_term] + proj_params)
            doc_total = cur.fetchone()["cnt"]
            cur.execute(f"""
                SELECT d.id, d.title, d.description, d.doc_type, d.category,
                       d.file_name, d.author, d.issue_date, d.version,
                       d.file_path,
                       d.procore_id, d.project_id, p.name as project_name, p.procore_id as procore_project_id
                FROM documents d
                LEFT JOIN projects p ON p.id = d.project_id
                WHERE d.is_deleted = FALSE
                  AND (d.title ILIKE %s OR d.description ILIKE %s
                       OR d.file_name ILIKE %s OR d.category ILIKE %s){pf}
                ORDER BY d.created_at DESC
                LIMIT %s
            """, [search_term, search_term, search_term, search_term] + proj_params + [limit])
            rows = []
            for row in cur.fetchall():
                r = dict(row)
                ppid = r.pop('procore_project_id', None)
                if ppid and r.get('procore_id'):
                    r['procore_url'] = f"{procore_base}/{ppid}/tools/documents/{r['procore_id']}"
                if r.get('file_path'):
                    r['file_url'] = f"/api/documents/{r['id']}/file"
                r.pop('file_path', None)
                rows.append(r)
            if rows or doc_total > 0:
                results['documents'] = {"total_count": doc_total, "results": rows}

        # --- Intelligence items ---
        if "intelligence" in active_types and _check_intel_tables_exist(cur):
            status_clause = ""
            if status == "open":
                status_clause = " AND i.status IN ('new', 'active', 'watch')"
            elif status == "closed":
                status_clause = " AND i.status IN ('resolved', 'archived')"
            else:
                status_clause = " AND i.status NOT IN ('archived', 'resolved')"
            pf = proj_filter.format(alias="i")
            cur.execute(f"""
                SELECT COUNT(*) as cnt FROM intelligence_items i
                JOIN projects p ON p.id = i.project_id
                WHERE (i.title ILIKE %s OR i.summary ILIKE %s){pf}{status_clause}
            """, [search_term, search_term] + proj_params)
            intel_total = cur.fetchone()["cnt"]
            cur.execute(f"""
                SELECT i.id, i.title, i.summary, i.severity, i.confidence,
                       i.item_type, i.status, i.project_id, p.name as project_name
                FROM intelligence_items i
                JOIN projects p ON p.id = i.project_id
                WHERE (i.title ILIKE %s OR i.summary ILIKE %s){pf}{status_clause}
                ORDER BY i.last_updated_at DESC
                LIMIT %s
            """, [search_term, search_term] + proj_params + [limit])
            items = serialize_rows(cur.fetchall())
            if items or intel_total > 0:
                results['intelligence'] = {"total_count": intel_total, "results": items}

        # --- Contacts ---
        if "contacts" in active_types:
            cur.execute("""
                SELECT COUNT(*) as cnt FROM contacts c
                LEFT JOIN companies co ON co.id = c.company_id
                WHERE c.is_deleted = FALSE
                  AND (c.first_name ILIKE %s OR c.last_name ILIKE %s
                       OR (c.first_name || ' ' || c.last_name) ILIKE %s
                       OR c.email ILIKE %s)
            """, [search_term, search_term, search_term, search_term])
            contact_total = cur.fetchone()["cnt"]
            cur.execute("""
                SELECT c.id, c.first_name, c.last_name, c.title, c.email,
                       c.phone, co.name as company_name
                FROM contacts c
                LEFT JOIN companies co ON co.id = c.company_id
                WHERE c.is_deleted = FALSE
                  AND (c.first_name ILIKE %s OR c.last_name ILIKE %s
                       OR (c.first_name || ' ' || c.last_name) ILIKE %s
                       OR c.email ILIKE %s)
                ORDER BY c.last_name, c.first_name
                LIMIT %s
            """, [search_term, search_term, search_term, search_term, limit])
            contacts = serialize_rows(cur.fetchall())
            if contacts or contact_total > 0:
                results['contacts'] = {"total_count": contact_total, "results": contacts}

        total = sum(g.get("total_count", 0) for g in results.values())
        return {
            "query": q,
            "filters": {
                "types": list(active_types),
                "project_id": project_id,
                "status": status or "any",
            },
            "results": results,
            "total_results": total,
        }


INLINE_MIME_TYPES = {
    'application/pdf', 'image/png', 'image/jpeg', 'image/gif', 'image/tiff',
    'image/webp', 'text/plain', 'text/html', 'text/csv',
}


def _resolve_doc_path(file_path: str) -> Path:
    """Resolve a document file_path to an absolute Path, with traversal check."""
    # Try DOCUMENTS_ROOT first (email archive), then UPLOADS_ROOT
    for root in [DOCUMENTS_ROOT, UPLOADS_ROOT]:
        full_path = Path(root) / file_path
        if full_path.resolve().is_relative_to(Path(root).resolve()) and full_path.exists():
            return full_path
    raise HTTPException(status_code=404, detail="File not found on disk")


def _get_doc_record(cur, doc_id: str) -> dict:
    """Fetch a document record or raise 404."""
    cur.execute("""
        SELECT d.id, d.title, d.file_path, d.file_name, d.mime_type,
               d.file_size_bytes, d.doc_type, d.category, d.description,
               d.author, d.issue_date, d.version, d.project_id,
               p.name as project_name
        FROM documents d
        LEFT JOIN projects p ON p.id = d.project_id
        WHERE d.id = %s AND d.is_deleted = FALSE
    """, [doc_id])
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(row)


@router.get("/documents/{doc_id}")
def get_document_metadata(doc_id: str):
    """Return document metadata as JSON."""
    with get_cursor() as cur:
        doc = _get_doc_record(cur, doc_id)
        has_file = False
        if doc.get('file_path'):
            try:
                _resolve_doc_path(doc['file_path'])
                has_file = True
            except HTTPException:
                pass
        return {
            "id": doc['id'],
            "title": doc['title'],
            "original_filename": doc.get('file_name'),
            "mime_type": doc.get('mime_type'),
            "file_size": doc.get('file_size_bytes'),
            "doc_type": doc.get('doc_type'),
            "category": doc.get('category'),
            "description": doc.get('description'),
            "author": doc.get('author'),
            "issue_date": str(doc['issue_date']) if doc.get('issue_date') else None,
            "version": doc.get('version'),
            "project_id": str(doc['project_id']) if doc.get('project_id') else None,
            "project_name": doc.get('project_name'),
            "has_file": has_file,
            "view_url": f"/api/documents/{doc_id}/view",
            "download_url": f"/api/documents/{doc_id}/file",
        }


@router.get("/documents/{doc_id}/file")
def serve_document_file(doc_id: str):
    """Serve a document file — inline for PDFs/images, attachment for others."""
    with get_cursor() as cur:
        doc = _get_doc_record(cur, doc_id)
        if not doc.get('file_path'):
            raise HTTPException(status_code=404, detail="Document file not found")
        full_path = _resolve_doc_path(doc['file_path'])
        mime = doc.get('mime_type') or 'application/octet-stream'
        filename = doc.get('file_name') or full_path.name
        disposition = 'inline' if mime in INLINE_MIME_TYPES else 'attachment'
        headers = {
            'Content-Disposition': f'{disposition}; filename="{filename}"',
            'Cache-Control': 'private, max-age=3600',
        }
        return FileResponse(
            path=str(full_path),
            filename=filename,
            media_type=mime,
            headers=headers,
        )


def _extract_display_name(addr_str: str) -> str:
    """Extract display name from email address string. 'John Doe <john@x.com>' -> 'John Doe'."""
    import re
    if not addr_str:
        return ''
    # Handle comma-separated addresses
    parts = []
    for addr in re.split(r',\s*', addr_str):
        addr = addr.strip()
        m = re.match(r'^"?([^"<]+?)"?\s*<[^>]+>$', addr)
        if m:
            parts.append(m.group(1).strip())
        elif '<' in addr:
            parts.append(addr.split('<')[0].strip().strip('"'))
        else:
            # Plain email address — show as-is
            parts.append(addr)
    return ', '.join(p for p in parts if p)


def _split_email_thread(body_html: str, body_text: str) -> list:
    """Split email body into thread segments. Returns list of dicts with sender, date, body."""
    import re
    import html as html_mod

    # Work with plain text for thread splitting (more reliable than HTML)
    text = body_text or ''
    if not text and body_html:
        # Crude HTML-to-text: strip tags
        text = re.sub(r'<br\s*/?\s*>', '\n', body_html, flags=re.I)
        text = re.sub(r'<[^>]+>', '', text)
        text = html_mod.unescape(text)

    if not text.strip():
        return [{'sender': '', 'date': '', 'body': body_html or '', 'is_html': bool(body_html)}]

    # Thread boundary patterns
    patterns = [
        # "On Mon, Jan 5, 2026, Name <email> wrote:"
        r'(?m)^On .+?wrote:\s*$',
        # "From: ... Sent: ... To: ... Subject: ..." block
        r'(?m)^-*\s*From:\s*.+?\n\s*Sent:\s*.+?\n',
        # "---------- Forwarded message ----------"
        r'-{5,}\s*Forwarded message\s*-{5,}',
        # "________" dividers often before quoted content
        r'_{10,}',
    ]

    # Find split points
    splits = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            splits.append(m.start())

    if not splits:
        # No thread — single message
        return [{'sender': '', 'date': '', 'body': body_html or f'<pre style="white-space:pre-wrap;font-family:inherit;">{html_mod.escape(text)}</pre>', 'is_html': bool(body_html)}]

    splits = sorted(set(splits))
    segments = []

    # First segment = most recent message
    first_text = text[:splits[0]].strip()
    if first_text:
        segments.append({'sender': '', 'date': '', 'body': '', 'raw_text': first_text, 'is_html': False})

    # Remaining segments
    for i, start in enumerate(splits):
        end = splits[i + 1] if i + 1 < len(splits) else len(text)
        seg_text = text[start:end].strip()
        if not seg_text:
            continue
        # Try to extract sender/date from the boundary
        sender = ''
        seg_date = ''
        on_match = re.match(r'On (.+?),\s*(.+?)\s+wrote:', seg_text, re.DOTALL)
        if on_match:
            seg_date = on_match.group(1).strip()
            sender = on_match.group(2).strip()
            # Clean up sender — extract name from "Name <email>"
            sender = _extract_display_name(sender) or sender
            seg_text = seg_text[on_match.end():].strip()
        else:
            from_match = re.search(r'From:\s*(.+?)(?:\n|$)', seg_text)
            sent_match = re.search(r'Sent:\s*(.+?)(?:\n|$)', seg_text)
            if from_match:
                sender = _extract_display_name(from_match.group(1).strip())
            if sent_match:
                seg_date = sent_match.group(1).strip()
            # Strip the header block from the body
            subj_match = re.search(r'Subject:\s*.+?(?:\n|$)', seg_text)
            if subj_match:
                seg_text = seg_text[subj_match.end():].strip()
            elif from_match:
                seg_text = seg_text[from_match.end():].strip()

        # Strip > quote prefixes
        lines = seg_text.split('\n')
        cleaned = '\n'.join(re.sub(r'^>\s?', '', line) for line in lines)
        segments.append({'sender': sender, 'date': seg_date, 'body': '', 'raw_text': cleaned.strip(), 'is_html': False})

    # If we have HTML for the first segment, use it (more readable)
    if body_html and segments:
        segments[0]['body'] = body_html
        segments[0]['is_html'] = True
        segments[0]['raw_text'] = ''

    return segments if segments else [{'sender': '', 'date': '', 'body': body_html or f'<pre style="white-space:pre-wrap;font-family:inherit;">{html_mod.escape(text)}</pre>', 'is_html': bool(body_html)}]


def _strip_signature(text: str) -> str:
    """Strip verbose email signatures, keeping only the name line."""
    import re
    # Common signature delimiters
    sig_patterns = [
        r'(?m)^--\s*$',           # "-- " standard sig delimiter
        r'(?m)^_{10,}$',          # Long underscore lines
        r'(?m)^Sent from my ',    # Mobile signatures
        r'(?m)^Get Outlook for',  # Outlook mobile
    ]
    for pat in sig_patterns:
        m = re.search(pat, text)
        if m:
            text = text[:m.start()].rstrip()
            break
    return text


def _parse_eml(file_path: Path) -> dict:
    """Parse an .eml file and return structured email data with thread segments."""
    import email
    from email import policy
    from email.utils import parsedate_to_datetime

    with open(file_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    sender = str(msg.get('From', ''))
    to = str(msg.get('To', ''))
    cc = str(msg.get('Cc', ''))
    subject = str(msg.get('Subject', ''))
    date_str = msg.get('Date', '')
    try:
        date_parsed = parsedate_to_datetime(date_str).strftime('%B %d, %Y at %I:%M %p') if date_str else ''
    except Exception:
        date_parsed = str(date_str)

    # Extract body — prefer HTML, fall back to plain text
    body_html = ''
    body_text = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/html' and not body_html:
                try:
                    body_html = part.get_content()
                except Exception:
                    pass
            elif ct == 'text/plain' and not body_text:
                try:
                    body_text = part.get_content()
                except Exception:
                    pass
    else:
        ct = msg.get_content_type()
        try:
            content = msg.get_content()
        except Exception:
            content = ''
        if ct == 'text/html':
            body_html = content
        else:
            body_text = content

    # Split into thread segments
    thread = _split_email_thread(body_html, body_text)

    # Extract attachments
    attachments = []
    if msg.is_multipart():
        for idx, part in enumerate(msg.walk()):
            fn = part.get_filename()
            if fn:
                payload = part.get_payload(decode=True)
                attachments.append({
                    'index': idx,
                    'filename': fn,
                    'content_type': part.get_content_type(),
                    'size': len(payload) if payload else 0,
                })

    return {
        'from': sender,
        'from_display': _extract_display_name(sender),
        'to': to,
        'to_display': _extract_display_name(to),
        'cc': cc,
        'cc_display': _extract_display_name(cc),
        'date': date_parsed,
        'subject': subject,
        'thread': thread,
        'attachments': attachments,
    }


@router.get("/documents/{doc_id}/view")
def view_document(doc_id: str):
    """Render a document for viewing. Emails render as styled HTML; others redirect to /file."""
    from fastapi.responses import HTMLResponse, RedirectResponse

    with get_cursor() as cur:
        doc = _get_doc_record(cur, doc_id)
        if not doc.get('file_path'):
            raise HTTPException(status_code=404, detail="Document file not found")
        full_path = _resolve_doc_path(doc['file_path'])
        mime = doc.get('mime_type') or ''

        # For non-email documents, redirect to the file endpoint
        if mime not in ('message/rfc822', 'application/vnd.ms-outlook'):
            return RedirectResponse(url=f"/api/documents/{doc_id}/file")

        # Parse and render email
        try:
            eml = _parse_eml(full_path)
        except Exception as e:
            logger.error(f"Failed to parse email {doc_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse email file")

        import html as html_mod

        def h(s):
            return html_mod.escape(str(s)) if s else ''

        # Build thread HTML
        thread_html = ''
        for i, seg in enumerate(eml['thread']):
            opacity = max(0.5, 0.8 - (i * 0.15))
            border_color = 'rgba(55,138,221,0.25)' if i == 1 else 'rgba(255,255,255,0.1)'

            if seg.get('is_html') and seg.get('body'):
                body_content = seg['body']
            elif seg.get('raw_text'):
                body_content = f'<pre style="white-space:pre-wrap;font-family:inherit;margin:0;">{h(seg["raw_text"])}</pre>'
            else:
                continue

            if i == 0:
                # Most recent message — no indent, full opacity
                thread_html += f'<div class="thread-segment" style="padding:24px;color:rgba(255,255,255,{opacity});">{body_content}</div>'
            else:
                # Earlier messages — indented with border
                marker_label = f'Earlier in thread — {h(seg["sender"])}' if seg.get('sender') else 'Earlier in thread'
                if seg.get('date'):
                    marker_label += f' &middot; {h(seg["date"])}'
                thread_html += f'''<div style="border-top:0.5px solid rgba(255,255,255,0.08);margin:0 24px;"></div>
<div class="thread-segment" style="padding:20px 24px;border-left:2px solid {border_color};margin-left:24px;color:rgba(255,255,255,{opacity});">
  <div class="thread-marker"><span class="thread-dot"></span>{marker_label}</div>
  <div style="margin-top:10px;">{body_content}</div>
</div>'''

        # Attachments
        att_html = ''
        if eml['attachments']:
            att_items = ''
            for a in eml['attachments']:
                ext = (a['filename'].rsplit('.', 1)[-1] if '.' in a['filename'] else '').lower()
                badge_colors = {
                    'pdf': ('#f09595', 'rgba(232,78,78,0.2)'),
                    'doc': ('#5dcaa5', 'rgba(93,202,165,0.2)'), 'docx': ('#5dcaa5', 'rgba(93,202,165,0.2)'),
                    'xls': ('#5dcaa5', 'rgba(93,202,165,0.2)'), 'xlsx': ('#5dcaa5', 'rgba(93,202,165,0.2)'),
                    'png': ('#85b7eb', 'rgba(55,138,221,0.2)'), 'jpg': ('#85b7eb', 'rgba(55,138,221,0.2)'),
                    'jpeg': ('#85b7eb', 'rgba(55,138,221,0.2)'), 'gif': ('#85b7eb', 'rgba(55,138,221,0.2)'),
                }
                color, bg = badge_colors.get(ext, ('#afa9ec', 'rgba(127,119,221,0.2)'))
                size_str = f'{a["size"] // 1024}KB' if a['size'] < 1048576 else f'{a["size"] / 1048576:.1f}MB'
                att_items += f'''<a href="/api/documents/{doc_id}/attachments/{a["index"]}/file" class="att-link" target="_blank">
  <span class="att-badge" style="background:{bg};color:{color};">{h(ext.upper() or 'FILE')}</span>
  <span class="att-name">{h(a["filename"])}</span>
  <span class="att-size">{size_str}</span>
</a>'''
            att_html = f'''<div style="border-top:0.5px solid rgba(255,255,255,0.08);margin:0 24px;"></div>
<div class="email-attachments"><div class="att-label">Attachments</div>{att_items}</div>'''

        # Context tags
        project_name = doc.get('project_name') or ''
        category = doc.get('doc_type') or doc.get('category') or ''
        tags_html = ''
        if project_name or category:
            tags = ''
            if project_name:
                tags += f'<span class="ctx-tag ctx-project">{h(project_name)}</span>'
            if category:
                tags += f'<span class="ctx-tag ctx-category">{h(str(category).replace("_", " ").title())}</span>'
            tags_html = f'<div class="ctx-tags">{tags}</div>'

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(eml['subject'])} — SteelSync</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#13151a; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif; margin:0; padding:24px 16px; line-height:1.7; }}
  .email-viewer {{ max-width:760px; margin:0 auto; }}
  .top-bar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }}
  .back-link {{ color:rgba(55,138,221,0.7); text-decoration:none; font-size:13px; }}
  .back-link:hover {{ color:rgba(55,138,221,1); }}
  .download-btn {{ font-size:12px; padding:5px 14px; border-radius:6px; background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.5); border:0.5px solid rgba(255,255,255,0.1); text-decoration:none; transition:all 0.15s; }}
  .download-btn:hover {{ background:rgba(255,255,255,0.1); color:rgba(255,255,255,0.7); }}
  .email-container {{ background:#1e2128; border-radius:10px; border:0.5px solid rgba(255,255,255,0.1); overflow:hidden; }}
  .email-header {{ padding:20px 24px; border-bottom:0.5px solid rgba(255,255,255,0.08); }}
  .email-subject {{ font-size:17px; font-weight:500; color:#e8e8e8; margin-bottom:14px; }}
  .meta-grid {{ display:grid; grid-template-columns:48px 1fr; gap:4px 12px; font-size:13px; }}
  .meta-label {{ color:rgba(255,255,255,0.35); text-align:right; }}
  .meta-value {{ color:#e0e0e0; }}
  .meta-value .email-addr {{ color:rgba(255,255,255,0.35); }}
  .ctx-tags {{ margin-top:12px; display:flex; gap:6px; flex-wrap:wrap; }}
  .ctx-tag {{ font-size:11px; padding:3px 10px; border-radius:4px; }}
  .ctx-project {{ background:rgba(93,202,165,0.12); color:rgba(93,202,165,0.8); }}
  .ctx-category {{ background:rgba(212,83,126,0.12); color:rgba(212,83,126,0.8); }}
  .thread-segment img {{ max-width:100%; height:auto; }}
  .thread-segment a {{ color:#85b7eb; }}
  .thread-segment table {{ border-collapse:collapse; max-width:100%; }}
  .thread-segment td, .thread-segment th {{ border:1px solid rgba(255,255,255,0.1); padding:6px 10px; }}
  .thread-segment p {{ margin:0 0 12px; }}
  .thread-marker {{ font-size:12px; color:rgba(255,255,255,0.4); display:flex; align-items:center; gap:8px; }}
  .thread-dot {{ width:6px; height:6px; border-radius:50%; background:rgba(255,255,255,0.2); flex-shrink:0; }}
  .email-attachments {{ padding:16px 24px; }}
  .att-label {{ font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:rgba(255,255,255,0.35); margin-bottom:10px; font-weight:500; }}
  .att-link {{ display:flex; align-items:center; gap:10px; padding:8px 12px; background:rgba(255,255,255,0.04); border-radius:6px; margin-bottom:6px; text-decoration:none; color:#e0e0e0; font-size:13px; transition:background 0.15s; }}
  .att-link:hover {{ background:rgba(255,255,255,0.08); }}
  .att-badge {{ font-size:10px; font-weight:700; padding:3px 8px; border-radius:4px; flex-shrink:0; }}
  .att-name {{ flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .att-size {{ color:rgba(255,255,255,0.3); font-size:11px; flex-shrink:0; }}
  .email-footer {{ text-align:center; margin-top:20px; font-size:11px; color:rgba(255,255,255,0.2); }}
  @media (max-width:600px) {{
    body {{ padding:12px 8px; }}
    .email-header {{ padding:16px; }}
    .email-subject {{ font-size:15px; }}
    .meta-grid {{ grid-template-columns:1fr; gap:2px 0; }}
    .meta-label {{ text-align:left; }}
    .thread-segment {{ padding:16px !important; }}
    .email-attachments {{ padding:12px 16px; }}
  }}
</style>
</head>
<body>
<div class="email-viewer">
  <div class="top-bar">
    <a href="javascript:window.close()" class="back-link">&larr; Back to search</a>
    <a href="/api/documents/{doc_id}/file" class="download-btn" download>Download .eml</a>
  </div>
  <div class="email-container">
    <div class="email-header">
      <div class="email-subject">{h(eml['subject'])}</div>
      <div class="meta-grid">
        <div class="meta-label">From</div>
        <div class="meta-value">{h(eml['from_display'] or eml['from'])}</div>
        <div class="meta-label">To</div>
        <div class="meta-value">{h(eml['to_display'] or eml['to'])}</div>
        {'<div class="meta-label">CC</div><div class="meta-value">' + h(eml['cc_display'] or eml['cc']) + '</div>' if eml['cc'] else ''}
        <div class="meta-label">Date</div>
        <div class="meta-value">{h(eml['date'])}</div>
      </div>
      {tags_html}
    </div>
    {thread_html}
    {att_html}
  </div>
  <div class="email-footer">SteelSync &middot; Document ID: {h(str(doc['id']))}</div>
</div>
</body>
</html>"""
        return HTMLResponse(content=html_content)


@router.get("/documents/{doc_id}/attachments/{att_index}/file")
def serve_email_attachment(doc_id: str, att_index: int):
    """Extract and serve an attachment from an .eml file."""
    from fastapi.responses import Response

    with get_cursor() as cur:
        doc = _get_doc_record(cur, doc_id)
        if not doc.get('file_path'):
            raise HTTPException(status_code=404, detail="Document file not found")
        full_path = _resolve_doc_path(doc['file_path'])

        import email
        from email import policy
        with open(full_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        # Walk parts to find the attachment at the given index
        for idx, part in enumerate(msg.walk()):
            if idx == att_index and part.get_filename():
                payload = part.get_payload(decode=True)
                if not payload:
                    raise HTTPException(status_code=404, detail="Attachment is empty")
                ct = part.get_content_type() or 'application/octet-stream'
                fn = part.get_filename()
                disposition = 'inline' if ct in INLINE_MIME_TYPES else 'attachment'
                return Response(
                    content=payload,
                    media_type=ct,
                    headers={
                        'Content-Disposition': f'{disposition}; filename="{fn}"',
                        'Cache-Control': 'private, max-age=3600',
                    },
                )
        raise HTTPException(status_code=404, detail="Attachment not found")


# =============================================================================
# EXTERNAL TOOLS (CC-7.4)
# =============================================================================

@router.get("/projects/{project_id}/external-tools")
def list_external_tools(project_id: str):
    """List active external tools for a project."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, project_id, tool_name, tool_icon, base_url, display_order
            FROM project_external_tools
            WHERE project_id = %s AND is_active = TRUE
            ORDER BY display_order, created_at
        """, [project_id])
        return {"data": serialize_rows(cur.fetchall())}


@router.post("/projects/{project_id}/external-tools")
def create_external_tool(project_id: str, body: dict = Body(...)):
    """Create a new external tool for a project."""
    import uuid
    name = body.get("tool_name", "").strip()
    icon = body.get("tool_icon", "browser")
    url = body.get("base_url", "").strip()
    order = body.get("display_order", 0)
    if not name:
        raise HTTPException(status_code=400, detail="tool_name is required")
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="base_url must start with http:// or https://")
    if icon not in ("smartsheet", "onedrive", "excel", "sharepoint", "browser"):
        raise HTTPException(status_code=400, detail="Invalid tool_icon")
    with get_cursor() as cur:
        tool_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO project_external_tools (id, project_id, tool_name, tool_icon, base_url, display_order)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [tool_id, project_id, name, icon, url, order])
        return {"data": {"id": tool_id}, "status": "created"}


@router.put("/external-tools/{tool_id}")
def update_external_tool(tool_id: str, body: dict = Body(...)):
    """Update an external tool."""
    with get_cursor() as cur:
        sets, params = [], []
        for field in ("tool_name", "tool_icon", "base_url", "display_order"):
            if field in body:
                val = body[field]
                if field == "base_url" and not str(val).startswith(("http://", "https://")):
                    raise HTTPException(status_code=400, detail="base_url must start with http:// or https://")
                sets.append(f"{field} = %s")
                params.append(val)
        if not sets:
            raise HTTPException(status_code=400, detail="No fields to update")
        sets.append("updated_at = NOW()")
        params.append(tool_id)
        cur.execute(f"UPDATE project_external_tools SET {', '.join(sets)} WHERE id = %s", params)
        return {"status": "updated"}


@router.delete("/external-tools/{tool_id}")
def delete_external_tool(tool_id: str):
    """Soft-delete an external tool."""
    with get_cursor() as cur:
        cur.execute("UPDATE project_external_tools SET is_active = FALSE, updated_at = NOW() WHERE id = %s", [tool_id])
        return {"status": "deleted"}


# =============================================================================
# DOCUMENT UPLOAD
# =============================================================================

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    classification: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    priority: Optional[str] = Form("normal"),
    uploaded_by: Optional[str] = Form("command-center"),
):
    """Upload a document to a project. Stores file, writes DB record, queues for pipeline."""
    import uuid
    import mimetypes

    # Validate file extension
    original_filename = file.filename or "unknown"
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}")

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large ({len(content) // (1024*1024)}MB). Maximum: 50MB")

    # Validate project exists
    with get_cursor() as cur:
        cur.execute("SELECT id, name FROM projects WHERE id = %s AND is_deleted = FALSE", [project_id])
        project = cur.fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Generate IDs and paths
        doc_id = str(uuid.uuid4())
        today = date.today().isoformat()
        storage_dir = Path(UPLOADS_ROOT) / project_id / today
        storage_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = original_filename.replace("/", "_").replace("\\", "_")
        file_path = storage_dir / f"{doc_id}_{safe_filename}"

        # Write file to disk
        with open(file_path, 'wb') as f:
            f.write(content)

        # Determine MIME type
        mime_type = EXTENSION_MIME_MAP.get(ext) or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

        # Determine doc_type from classification hint
        doc_type_map = {
            'drawing': 'drawing', 'specification': 'specification', 'submittal': 'submittal',
            'correspondence': 'correspondence', 'schedule': 'schedule', 'other': 'other',
        }
        doc_type = doc_type_map.get(classification, 'other')

        # Relative path for DB (relative to UPLOADS_ROOT parent)
        rel_path = str(file_path.relative_to(Path(UPLOADS_ROOT)))

        # Write database record
        cur.execute("""
            INSERT INTO documents (id, project_id, title, description, doc_type, category,
                                   file_name, file_path, file_size_bytes, mime_type,
                                   ingestion_status, sync_status, created_at)
            VALUES (%s, %s, %s, %s, %s::document_type, %s, %s, %s, %s, %s, 'queued', 'synced', NOW())
        """, [
            doc_id, project_id, original_filename,
            notes or f"Portal upload by {uploaded_by}",
            doc_type, 'portal_upload',
            original_filename, rel_path, len(content), mime_type,
        ])

        return {
            "status": "accepted",
            "document_id": doc_id,
            "filename": original_filename,
            "project_id": project_id,
            "project_name": project['name'],
            "pipeline_status": "queued",
            "message": "Document accepted and queued for processing",
        }


# =============================================================================
# DRAWING BROWSER (Phase 1)
# =============================================================================

@router.get("/drawings")
def list_drawings(
    project_id: Optional[str] = Query(None),
    discipline: Optional[str] = Query(None),
    current: Optional[bool] = Query(True),
    search: Optional[str] = Query(None),
    set_name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("number"),
):
    """Cross-project drawing listing with filters."""
    with get_cursor() as cur:
        where = "WHERE d.is_deleted = FALSE"
        params = []

        if project_id:
            where += " AND d.project_id = %s"
            params.append(project_id)
        if discipline:
            where += " AND d.discipline = %s::drawing_discipline"
            params.append(discipline)
        if current is not None:
            where += " AND d.current = %s"
            params.append(current)
        if search:
            where += " AND (d.number ILIKE %s OR d.title ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%"])
        if set_name:
            where += " AND d.set_name = %s"
            params.append(set_name)

        cur.execute(f"SELECT COUNT(*) as cnt FROM drawings d {where}", params)
        total = cur.fetchone()["cnt"]

        sort_col = {"number": "d.number", "title": "d.title", "discipline": "d.discipline", "updated_at": "d.updated_at"}.get(sort, "d.number")

        cur.execute(f"""
            SELECT d.id, d.procore_id, d.project_id, d.number, d.title,
                   d.discipline, d.revision, d.current, d.set_name,
                   d.created_at, d.updated_at,
                   p.name as project_name, p.number as project_number, p.procore_id as procore_project_id
            FROM drawings d
            JOIN projects p ON p.id = d.project_id
            {where}
            ORDER BY {sort_col} ASC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        procore_base = "https://sandbox.procore.com/webclients/host/companies/4281379/projects"
        drawings = []
        for row in cur.fetchall():
            r = dict(row)
            ppid = r.pop('procore_project_id', None)
            if ppid and r.get('procore_id'):
                r['procore_link'] = f"{procore_base}/{ppid}/tools/drawings"
            if r.get('discipline'):
                r['discipline'] = str(r['discipline'])
            r['pdf_url'] = f"/api/drawings/{r['id']}/pdf"
            drawings.append(r)

        return {
            "drawings": drawings,
            "total_count": total,
            "page": (offset // limit) + 1,
            "has_more": (offset + limit) < total,
        }


@router.get("/drawings/disciplines")
def list_drawing_disciplines():
    """Return distinct drawing disciplines."""
    with get_cursor() as cur:
        cur.execute("SELECT DISTINCT discipline FROM drawings WHERE discipline IS NOT NULL AND is_deleted = FALSE ORDER BY discipline")
        return {"disciplines": [str(r['discipline']) for r in cur.fetchall()]}


@router.get("/drawings/sets")
def list_drawing_sets(project_id: Optional[str] = Query(None)):
    """Return distinct drawing set names with counts."""
    with get_cursor() as cur:
        where = "WHERE d.is_deleted = FALSE AND d.set_name IS NOT NULL"
        params = []
        if project_id:
            where += " AND d.project_id = %s"
            params.append(project_id)
        cur.execute(f"""
            SELECT d.set_name, d.project_id, p.name as project_name, COUNT(*) as drawing_count
            FROM drawings d
            JOIN projects p ON p.id = d.project_id
            {where}
            GROUP BY d.set_name, d.project_id, p.name
            ORDER BY d.set_name
        """, params)
        return {"sets": serialize_rows(cur.fetchall())}


DRAWING_CACHE_ROOT = os.environ.get("DRAWING_CACHE_ROOT", "/home/moby/nerv-data/drawing-cache")


def _fetch_drawing_pdf_from_procore(procore_id: int, procore_project_id: int, cache_path: Path) -> bool:
    """Fetch a drawing PDF from Procore API and cache it locally."""
    import httpx
    import json as json_mod
    try:
        # Load Procore credentials
        creds_dir = Path(os.environ.get("PROCORE_CREDS_DIR", "/home/moby/.openclaw/workspace/.credentials"))
        with open(creds_dir / "procore.env") as f:
            env = {}
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k] = v
        with open(creds_dir / "procore_token.json") as f:
            token = json_mod.load(f)

        # Refresh token if needed
        import time
        saved_at = token.get('saved_at', 0)
        expires_in = token.get('expires_in', 5400)
        if time.time() - saved_at > (expires_in - 300):
            resp = httpx.post("https://login-sandbox.procore.com/oauth/token", data={
                'grant_type': 'refresh_token',
                'refresh_token': token['refresh_token'],
                'client_id': env['PROCORE_CLIENT_ID'],
                'client_secret': env['PROCORE_CLIENT_SECRET'],
            }, timeout=30)
            resp.raise_for_status()
            token = resp.json()
            token['saved_at'] = time.time()
            with open(creds_dir / "procore_token.json", 'w') as f:
                json_mod.dump(token, f)

        headers = {
            'Authorization': f'Bearer {token["access_token"]}',
            'Procore-Company-Id': '4281379',
        }

        # Get drawing revision with pdf_url
        resp = httpx.get(
            f"https://sandbox.procore.com/rest/v1.0/projects/{procore_project_id}/drawing_revisions",
            headers=headers,
            params={'filters[drawing_id]': procore_id, 'filters[current]': 'true', 'per_page': 1},
            timeout=30,
        )
        resp.raise_for_status()
        revisions = resp.json()
        if not revisions:
            logger.warning(f"No drawing revisions found for procore_id {procore_id}")
            return False

        pdf_url = revisions[0].get('pdf_url')
        if not pdf_url:
            logger.warning(f"No pdf_url in drawing revision for procore_id {procore_id}")
            return False

        # Download the PDF
        pdf_resp = httpx.get(pdf_url, headers=headers, timeout=60, follow_redirects=True)
        pdf_resp.raise_for_status()

        # Cache locally
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'wb') as f:
            f.write(pdf_resp.content)
        logger.info(f"Cached drawing PDF: {cache_path} ({len(pdf_resp.content)} bytes)")
        return True

    except Exception as e:
        logger.error(f"Failed to fetch drawing PDF from Procore: {e}")
        return False


@router.get("/drawings/{drawing_id}/pdf")
def serve_drawing_pdf(drawing_id: str, download: bool = Query(False)):
    """Serve drawing PDF — from local cache or fetch from Procore API."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT d.id, d.number, d.title, d.revision, d.file_path, d.procore_id,
                   d.project_id, p.procore_id as procore_project_id
            FROM drawings d
            JOIN projects p ON p.id = d.project_id
            WHERE d.id = %s
        """, [drawing_id])
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Drawing not found")

        filename = f"{row['number']}_{row['title'] or 'drawing'}.pdf".replace('/', '_').replace(' ', '_')
        disposition = 'attachment' if download else 'inline'

        # Check local cache first
        cache_path = Path(DRAWING_CACHE_ROOT) / str(row['project_id']) / f"{row['number']}_rev{row['revision'] or '0'}.pdf"
        if cache_path.exists():
            return FileResponse(
                path=str(cache_path), filename=filename, media_type='application/pdf',
                headers={'Content-Disposition': f'{disposition}; filename="{filename}"', 'Cache-Control': 'private, max-age=86400'},
            )

        # Check file_path
        if row.get('file_path'):
            for root in [DOCUMENTS_ROOT, UPLOADS_ROOT]:
                full_path = Path(root) / row['file_path']
                if full_path.exists():
                    return FileResponse(
                        path=str(full_path), filename=filename, media_type='application/pdf',
                        headers={'Content-Disposition': f'{disposition}; filename="{filename}"', 'Cache-Control': 'private, max-age=86400'},
                    )

        # Fetch from Procore API and cache
        if row.get('procore_id') and row.get('procore_project_id'):
            if _fetch_drawing_pdf_from_procore(row['procore_id'], row['procore_project_id'], cache_path):
                return FileResponse(
                    path=str(cache_path), filename=filename, media_type='application/pdf',
                    headers={'Content-Disposition': f'{disposition}; filename="{filename}"', 'Cache-Control': 'private, max-age=86400'},
                )

        raise HTTPException(status_code=404, detail="Drawing PDF not available")


# =============================================================================
# DRAWING BROWSER — Phase 2 (Views, Favorites, RFI Links)
# =============================================================================

@router.post("/drawings/{drawing_id}/view")
def record_drawing_view(drawing_id: str):
    """Record a drawing view event. Deduplicates within 5 minutes."""
    import uuid
    with get_cursor() as cur:
        # Check for recent view (dedup within 5 min)
        cur.execute("""
            SELECT id FROM drawing_views
            WHERE drawing_id = %s AND viewed_at > NOW() - INTERVAL '5 minutes'
            LIMIT 1
        """, [drawing_id])
        if cur.fetchone():
            return {"status": "already_recorded"}
        cur.execute("""
            INSERT INTO drawing_views (id, drawing_id) VALUES (%s, %s)
        """, [str(uuid.uuid4()), drawing_id])
        return {"status": "recorded"}


@router.get("/drawings/recent")
def get_recent_drawings(limit: int = Query(20, ge=1, le=50)):
    """Returns recently viewed drawings, deduplicated by drawing_id."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (dv.drawing_id)
                   dv.drawing_id, d.number, d.title, d.discipline, d.revision,
                   p.name as project_name, dv.viewed_at,
                   (SELECT COUNT(*) FROM drawing_views v2 WHERE v2.drawing_id = dv.drawing_id) as view_count
            FROM drawing_views dv
            JOIN drawings d ON d.id = dv.drawing_id
            JOIN projects p ON p.id = d.project_id
            ORDER BY dv.drawing_id, dv.viewed_at DESC
        """)
        # Re-sort by viewed_at desc after DISTINCT ON
        rows = serialize_rows(cur.fetchall())
        rows.sort(key=lambda r: r.get('viewed_at', ''), reverse=True)
        return {"recent_drawings": rows[:limit]}


@router.post("/drawings/{drawing_id}/favorite")
def toggle_drawing_favorite(drawing_id: str):
    """Toggle favorite status for a drawing."""
    import uuid
    with get_cursor() as cur:
        cur.execute("SELECT id FROM drawing_favorites WHERE drawing_id = %s AND user_id IS NULL", [drawing_id])
        existing = cur.fetchone()
        if existing:
            cur.execute("DELETE FROM drawing_favorites WHERE id = %s", [existing['id']])
            return {"favorited": False}
        else:
            cur.execute("INSERT INTO drawing_favorites (id, drawing_id) VALUES (%s, %s)", [str(uuid.uuid4()), drawing_id])
            return {"favorited": True}


@router.get("/drawings/favorites")
def get_drawing_favorites():
    """Returns all favorited drawings."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT df.drawing_id, d.number, d.title, d.discipline, d.revision,
                   p.name as project_name, df.created_at
            FROM drawing_favorites df
            JOIN drawings d ON d.id = df.drawing_id
            JOIN projects p ON p.id = d.project_id
            WHERE df.user_id IS NULL
            ORDER BY df.created_at DESC
        """)
        return {"favorites": serialize_rows(cur.fetchall())}


@router.get("/drawings/{drawing_id}/rfis")
def get_drawing_rfis(drawing_id: str):
    """Returns RFIs linked to this drawing."""
    with get_cursor() as cur:
        procore_base = "https://sandbox.procore.com/webclients/host/companies/4281379/projects"
        cur.execute("""
            SELECT l.reference_text, r.id as rfi_id, r.number, r.subject, r.status,
                   r.procore_id, r.due_date, p.procore_id as procore_project_id,
                   CASE WHEN r.status NOT IN ('closed','answered','void') AND r.date_initiated IS NOT NULL
                        THEN (CURRENT_DATE - r.date_initiated) ELSE NULL END as days_open
            FROM drawing_rfi_links l
            JOIN rfis r ON r.id = l.rfi_id
            JOIN projects p ON p.id = r.project_id
            WHERE l.drawing_id = %s AND r.is_deleted = FALSE
            ORDER BY r.number::int
        """, [drawing_id])
        rows = []
        for row in cur.fetchall():
            r = dict(row)
            ppid = r.pop('procore_project_id', None)
            if ppid and r.get('procore_id'):
                r['procore_link'] = f"{procore_base}/{ppid}/tools/rfis/{r['procore_id']}"
            rows.append(r)
        return {"linked_rfis": rows}


# =============================================================================
# DRAWING MARKUP (Phase 3)
# =============================================================================

@router.get("/drawings/{drawing_id}/png")
def serve_drawing_png(drawing_id: str, page: int = Query(1, ge=1)):
    """Convert a drawing PDF page to PNG for markup overlay."""
    from fastapi.responses import Response

    with get_cursor() as cur:
        cur.execute("SELECT id, number, project_id, revision FROM drawings WHERE id = %s", [drawing_id])
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Drawing not found")

        # Find the cached PDF
        cache_path = Path(DRAWING_CACHE_ROOT) / str(row['project_id']) / f"{row['number']}_rev{row['revision'] or '0'}.pdf"
        if not cache_path.exists():
            raise HTTPException(status_code=404, detail="Drawing PDF not cached")

        # Check for cached PNG
        png_cache = cache_path.with_suffix(f'.page{page}.png')
        if png_cache.exists():
            return Response(content=png_cache.read_bytes(), media_type='image/png',
                           headers={'Cache-Control': 'private, max-age=86400'})

        # Convert PDF page to PNG using PyMuPDF
        try:
            import fitz
            doc = fitz.open(str(cache_path))
            if page > len(doc):
                raise HTTPException(status_code=404, detail=f"Page {page} not found (document has {len(doc)} pages)")
            pg = doc[page - 1]
            # Render at 2x resolution for quality
            mat = fitz.Matrix(2.0, 2.0)
            pix = pg.get_pixmap(matrix=mat)
            png_bytes = pix.tobytes("png")
            doc.close()

            # Cache the PNG
            png_cache.write_bytes(png_bytes)
            return Response(content=png_bytes, media_type='image/png',
                           headers={'Cache-Control': 'private, max-age=86400'})
        except ImportError:
            raise HTTPException(status_code=500, detail="PyMuPDF not installed — PNG conversion unavailable")


@router.get("/drawings/{drawing_id}/markups")
def list_drawing_markups(drawing_id: str):
    """List all markups for a drawing."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, drawing_id, title, page_number, visibility, created_at, updated_at
            FROM drawing_markups
            WHERE drawing_id = %s
            ORDER BY created_at DESC
        """, [drawing_id])
        return {"markups": serialize_rows(cur.fetchall())}


@router.get("/drawings/{drawing_id}/markups/{markup_id}")
def get_drawing_markup(drawing_id: str, markup_id: str):
    """Get a single markup with its data."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, drawing_id, title, page_number, markup_data, visibility, created_at, updated_at
            FROM drawing_markups WHERE id = %s AND drawing_id = %s
        """, [markup_id, drawing_id])
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Markup not found")
        return {"data": serialize_row(row)}


@router.post("/drawings/{drawing_id}/markups")
def create_drawing_markup(drawing_id: str, body: dict = Body(...)):
    """Create a new markup layer."""
    import uuid
    import json as json_mod
    with get_cursor() as cur:
        markup_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO drawing_markups (id, drawing_id, title, page_number, markup_data, visibility)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [
            markup_id, drawing_id,
            body.get('title', 'Untitled markup'),
            body.get('page_number', 1),
            json_mod.dumps(body.get('markup_data', {"elements": []})),
            body.get('visibility', 'personal'),
        ])
        return {"data": {"id": markup_id}, "status": "created"}


@router.put("/drawings/{drawing_id}/markups/{markup_id}")
def update_drawing_markup(drawing_id: str, markup_id: str, body: dict = Body(...)):
    """Update a markup's data."""
    import json as json_mod
    with get_cursor() as cur:
        sets, params = [], []
        if 'markup_data' in body:
            sets.append("markup_data = %s")
            params.append(json_mod.dumps(body['markup_data']))
        if 'title' in body:
            sets.append("title = %s")
            params.append(body['title'])
        if not sets:
            raise HTTPException(status_code=400, detail="No fields to update")
        sets.append("updated_at = NOW()")
        params.extend([markup_id, drawing_id])
        cur.execute(f"UPDATE drawing_markups SET {', '.join(sets)} WHERE id = %s AND drawing_id = %s", params)
        return {"status": "updated"}


@router.delete("/drawings/{drawing_id}/markups/{markup_id}")
def delete_drawing_markup(drawing_id: str, markup_id: str):
    """Delete a markup."""
    with get_cursor() as cur:
        cur.execute("DELETE FROM drawing_markups WHERE id = %s AND drawing_id = %s", [markup_id, drawing_id])
        return {"status": "deleted"}


# CC-2.5: REINFORCEMENT CANDIDATE PIPELINE
# =============================================================================

@router.get("/projects/{project_id}/reinforcement-candidates")
def list_reinforcement_candidates(
    project_id: str,
    status: Optional[str] = Query("pending", description="Filter: pending, promoted, discarded"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List reinforcement candidates for a project's signals."""
    with get_cursor() as cur:
        where = """
            WHERE s.project_id = %s
        """
        params = [project_id]

        if status:
            where += " AND rc.status = %s::reinforcement_status"
            params.append(status)

        cur.execute(f"""
            SELECT COUNT(*) as cnt
            FROM reinforcement_candidates rc
            JOIN signals s ON s.id = rc.target_signal_id
            {where}
        """, params)
        total = cur.fetchone()["cnt"]

        cur.execute(f"""
            SELECT rc.id, rc.target_signal_id, rc.source_signal_id,
                   rc.reason, rc.confidence, rc.status,
                   rc.created_at, rc.evaluated_at,
                   ts.signal_type as target_signal_type,
                   ts.summary as target_signal_summary,
                   ss.signal_type as source_signal_type,
                   ss.summary as source_signal_summary
            FROM reinforcement_candidates rc
            JOIN signals ts ON ts.id = rc.target_signal_id
            JOIN signals ss ON ss.id = rc.source_signal_id
            JOIN signals s ON s.id = rc.target_signal_id
            {where}
            ORDER BY rc.confidence DESC, rc.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = serialize_rows(cur.fetchall())

    return paginated_response(rows, total, limit, offset)


@router.patch("/reinforcement-candidates/{candidate_id}")
def update_reinforcement_candidate(candidate_id: str, body: dict = Body(...)):
    """Update a reinforcement candidate status (promote or discard).

    Body: {status: "promoted"|"discarded"}
    When promoted, updates the target signal's last_reinforced_at.
    """
    new_status = body.get("status")
    if new_status not in ("promoted", "discarded"):
        raise HTTPException(status_code=400, detail="status must be 'promoted' or 'discarded'")

    with get_cursor() as cur:
        cur.execute("""
            SELECT id, target_signal_id, source_signal_id, status
            FROM reinforcement_candidates WHERE id = %s
        """, (candidate_id,))
        candidate = cur.fetchone()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        if candidate["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Candidate already {candidate['status']}")

        cur.execute("""
            UPDATE reinforcement_candidates SET
                status = %s::reinforcement_status,
                evaluated_at = NOW()
            WHERE id = %s
        """, (new_status, candidate_id))

        # If promoted, reinforce the target signal
        if new_status == "promoted":
            cur.execute("""
                UPDATE signals SET last_reinforced_at = NOW()
                WHERE id = %s
            """, (str(candidate["target_signal_id"]),))

            # Also update any intelligence items linked to this signal
            cur.execute("""
                UPDATE intelligence_items SET
                    last_reinforced_at = NOW(),
                    source_evidence_count = source_evidence_count + 1
                WHERE id IN (
                    SELECT intelligence_item_id FROM intelligence_item_evidence
                    WHERE signal_id = %s
                )
            """, (str(candidate["target_signal_id"]),))

    return {"data": {"id": candidate_id, "status": new_status}}


# =============================================================================
# CC-5.1: RADAR API ENDPOINTS
# =============================================================================

def _check_radar_tables_exist(cur) -> bool:
    """Check if radar tables have been created."""
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables WHERE table_name = 'radar_items'
        ) as exists
    """)
    return cur.fetchone()["exists"]


@router.post("/radar/items")
def create_radar_item(body: dict = Body(...)):
    """Create a new Radar item."""
    with get_cursor() as cur:
        if not _check_radar_tables_exist(cur):
            raise HTTPException(status_code=503, detail="Radar tables not initialized")

        item_id = str(__import__("uuid").uuid4())
        cur.execute("""
            INSERT INTO radar_items (id, project_id, title, description, priority, monitoring_scope_json, primary_target)
            VALUES (%s, %s, %s, %s, %s::radar_priority, %s, %s)
        """, (
            item_id,
            body.get("project_id"),
            body.get("title"),
            body.get("description"),
            body.get("priority", "watch"),
            __import__("json").dumps(body.get("monitoring_scope", {})),
            body.get("primary_target"),
        ))

        # Create initial activity entry
        cur.execute("""
            INSERT INTO radar_activity (id, radar_item_id, activity_type, content)
            VALUES (%s, %s, 'status_change'::radar_activity_type, %s)
        """, (str(__import__("uuid").uuid4()), item_id, f"Radar item created: {body.get('title')}"))

        return {"data": {"id": item_id}, "status": "created"}


@router.get("/radar/items")
def list_radar_items(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List Radar items with filtering."""
    with get_cursor() as cur:
        if not _check_radar_tables_exist(cur):
            return paginated_response([], 0, limit, offset)

        where_parts = ["1=1"]
        params = []

        if project_id:
            where_parts.append("r.project_id = %s")
            params.append(project_id)
        if status:
            where_parts.append("r.status = %s::radar_status")
            params.append(status)
        else:
            where_parts.append("r.status = 'active'")
        if priority:
            where_parts.append("r.priority = %s::radar_priority")
            params.append(priority)

        where = " AND ".join(where_parts)

        cur.execute(f"SELECT COUNT(*) as cnt FROM radar_items r WHERE {where}", params)
        total = cur.fetchone()["cnt"]

        cur.execute(f"""
            SELECT r.id, r.project_id, r.title, r.description, r.priority, r.status,
                   r.monitoring_scope_json, r.primary_target,
                   r.created_at, r.updated_at, r.resolved_at,
                   p.name as project_name,
                   (SELECT COUNT(*) FROM radar_activity ra WHERE ra.radar_item_id = r.id) as activity_count,
                   (SELECT COUNT(*) FROM radar_document_links rl WHERE rl.radar_item_id = r.id) as link_count
            FROM radar_items r
            JOIN projects p ON p.id = r.project_id
            WHERE {where}
            ORDER BY
                CASE r.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'watch' THEN 2 END,
                r.updated_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        return paginated_response(serialize_rows(cur.fetchall()), total, limit, offset)


@router.get("/radar/items/{item_id}")
def get_radar_item(item_id: str):
    """Get Radar item detail with activity log and document links."""
    with get_cursor() as cur:
        if not _check_radar_tables_exist(cur):
            raise HTTPException(status_code=503, detail="Radar tables not initialized")

        cur.execute("""
            SELECT r.*, p.name as project_name
            FROM radar_items r
            JOIN projects p ON p.id = r.project_id
            WHERE r.id = %s
        """, (item_id,))
        item = cur.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Radar item not found")

        item = serialize_row(item)

        # Activity log
        cur.execute("""
            SELECT id, activity_type, content, source_signal_id, severity, created_at
            FROM radar_activity
            WHERE radar_item_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (item_id,))
        item["activity"] = serialize_rows(cur.fetchall())

        # Document links
        cur.execute("""
            SELECT id, document_type, document_id, relevance_score, linked_at, linked_by
            FROM radar_document_links
            WHERE radar_item_id = %s
            ORDER BY relevance_score DESC
        """, (item_id,))
        item["document_links"] = serialize_rows(cur.fetchall())

        # Linked intelligence items (via radar_match evidence signals)
        cur.execute("""
            SELECT DISTINCT i.id, i.item_type, i.title, i.severity, i.status,
                   i.confidence, i.first_created_at
            FROM intelligence_items i
            JOIN intelligence_item_evidence e ON e.intelligence_item_id = i.id
            JOIN signals s ON s.id = e.signal_id
            WHERE s.signal_category = 'radar_match'
              AND s.supporting_context_json->>'radar_item_id' = %s
              AND i.status NOT IN ('archived', 'dismissed')
            ORDER BY i.first_created_at DESC
        """, (item_id,))
        item["linked_intelligence_items"] = serialize_rows(cur.fetchall())

        return {"data": item}


@router.patch("/radar/items/{item_id}")
def update_radar_item(item_id: str, body: dict = Body(...)):
    """Update Radar item status, priority, or description."""
    with get_cursor() as cur:
        if not _check_radar_tables_exist(cur):
            raise HTTPException(status_code=503, detail="Radar tables not initialized")

        cur.execute("SELECT id, status FROM radar_items WHERE id = %s", (item_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Radar item not found")

        updates = []
        params = []

        if "status" in body:
            updates.append("status = %s::radar_status")
            params.append(body["status"])
            if body["status"] == "resolved":
                updates.append("resolved_at = NOW()")
            elif body["status"] == "archived":
                updates.append("archived_at = NOW()")
        if "priority" in body:
            updates.append("priority = %s::radar_priority")
            params.append(body["priority"])
        if "description" in body:
            updates.append("description = %s")
            params.append(body["description"])
        if "title" in body:
            updates.append("title = %s")
            params.append(body["title"])
        if "monitoring_scope" in body:
            updates.append("monitoring_scope_json = %s")
            params.append(__import__("json").dumps(body["monitoring_scope"]))

        if updates:
            params.append(item_id)
            cur.execute(f"UPDATE radar_items SET {', '.join(updates)} WHERE id = %s", params)

            # Log activity
            changes = ", ".join(body.keys())
            cur.execute("""
                INSERT INTO radar_activity (id, radar_item_id, activity_type, content)
                VALUES (%s, %s, 'status_change'::radar_activity_type, %s)
            """, (str(__import__("uuid").uuid4()), item_id, f"Updated: {changes}"))

            # CC-5.6: Post-resolution flagging — when Radar item resolved,
            # flag linked intelligence items for re-evaluation in next synthesis
            if body.get("status") == "resolved":
                cur.execute("""
                    UPDATE intelligence_items SET
                        recommended_attention_level = 'review_needed'
                    WHERE id IN (
                        SELECT DISTINCT e.intelligence_item_id
                        FROM intelligence_item_evidence e
                        JOIN signals s ON s.id = e.signal_id
                        WHERE s.signal_category = 'radar_match'
                          AND s.supporting_context_json->>'radar_item_id' = %s
                    )
                    AND status IN ('new', 'active', 'watch')
                """, (item_id,))
                flagged = cur.rowcount
                if flagged:
                    logger.info(
                        f"Radar resolution: flagged {flagged} intelligence items "
                        f"for re-evaluation (radar_item={item_id})"
                    )

        return {"status": "updated"}


@router.post("/radar/items/{item_id}/activity")
def add_radar_activity(item_id: str, body: dict = Body(...)):
    """Add a user annotation to a Radar item."""
    with get_cursor() as cur:
        if not _check_radar_tables_exist(cur):
            raise HTTPException(status_code=503, detail="Radar tables not initialized")

        cur.execute("SELECT id FROM radar_items WHERE id = %s", (item_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Radar item not found")

        activity_id = str(__import__("uuid").uuid4())
        cur.execute("""
            INSERT INTO radar_activity (id, radar_item_id, activity_type, content, severity)
            VALUES (%s, %s, 'user_annotation'::radar_activity_type, %s, %s::intelligence_severity)
        """, (activity_id, item_id, body.get("content", ""), body.get("severity", "medium")))

        return {"data": {"id": activity_id}, "status": "created"}


@router.post("/radar/items/{item_id}/watchers")
def add_radar_watcher(item_id: str, body: dict = Body(...)):
    """Add a watcher to a Radar item."""
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    with get_cursor() as cur:
        cur.execute("SELECT id FROM radar_items WHERE id = %s", (item_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Radar item not found")

        watcher_id = str(__import__("uuid").uuid4())
        try:
            cur.execute("""
                INSERT INTO radar_watchers (id, radar_item_id, user_id, notification_preference)
                VALUES (%s, %s, %s, %s)
            """, (watcher_id, item_id, user_id, body.get("notification_preference", "all")))
        except Exception:
            raise HTTPException(status_code=409, detail="User is already watching this item")

    return {"data": {"id": watcher_id}, "status": "created"}


@router.delete("/radar/items/{item_id}/watchers/{user_id}")
def remove_radar_watcher(item_id: str, user_id: str):
    """Remove a watcher from a Radar item."""
    with get_cursor() as cur:
        cur.execute("""
            DELETE FROM radar_watchers
            WHERE radar_item_id = %s AND user_id = %s
        """, (item_id, user_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Watcher not found")

    return {"status": "deleted"}


@router.post("/intelligence-items/{item_id}/feedback")
def submit_feedback(item_id: str, body: dict = Body(...)):
    """Submit user feedback on an intelligence item (confirm or dismiss).

    Body: {feedback_type: "confirmed"|"dismissed", dismiss_reason?: string, dismiss_comment?: string}
    """
    feedback_type = body.get("feedback_type")
    if feedback_type not in ("confirmed", "dismissed"):
        raise HTTPException(status_code=400, detail="feedback_type must be 'confirmed' or 'dismissed'")

    with get_cursor() as cur:
        # Verify item exists
        cur.execute("SELECT id, status FROM intelligence_items WHERE id = %s", (item_id,))
        item = cur.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Intelligence item not found")

        # Record feedback
        feedback_id = str(__import__("uuid").uuid4())
        cur.execute("""
            INSERT INTO intelligence_item_feedback
                (id, intelligence_item_id, feedback_type, dismiss_reason, dismiss_comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            feedback_id, item_id, feedback_type,
            body.get("dismiss_reason"),
            body.get("dismiss_comment"),
        ))

        # Update item status
        if feedback_type == "confirmed":
            cur.execute("""
                UPDATE intelligence_items SET
                    status = CASE WHEN status = 'new' THEN 'active'::intelligence_status ELSE status END,
                    confidence = LEAST(1.0, confidence + 0.1)
                WHERE id = %s
            """, (item_id,))
        elif feedback_type == "dismissed":
            cur.execute("""
                UPDATE intelligence_items SET
                    status = 'dismissed'::intelligence_status
                WHERE id = %s
            """, (item_id,))

    return {"data": {"id": feedback_id, "feedback_type": feedback_type}, "status": "created"}


@router.get("/intelligence-items/feedback-stats")
def feedback_stats(project_id: Optional[str] = Query(None)):
    """Get feedback statistics for intelligence items."""
    with get_cursor() as cur:
        where = ""
        params = []
        if project_id:
            where = "AND ii.project_id = %s"
            params.append(project_id)

        cur.execute(f"""
            SELECT
                COUNT(*) as total_items,
                SUM(CASE WHEN f.feedback_type = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                SUM(CASE WHEN f.feedback_type = 'dismissed' THEN 1 ELSE 0 END) as dismissed,
                COUNT(*) FILTER (WHERE f.id IS NULL) as no_feedback
            FROM intelligence_items ii
            LEFT JOIN intelligence_item_feedback f ON f.intelligence_item_id = ii.id
            WHERE ii.status NOT IN ('archived') {where}
        """, params)
        stats = serialize_row(cur.fetchone())

        # Dismissed reasons breakdown
        cur.execute(f"""
            SELECT f.dismiss_reason, COUNT(*) as cnt
            FROM intelligence_item_feedback f
            JOIN intelligence_items ii ON ii.id = f.intelligence_item_id
            WHERE f.feedback_type = 'dismissed' {where}
            GROUP BY f.dismiss_reason
        """, params)
        dismiss_breakdown = {r["dismiss_reason"] or "unspecified": r["cnt"] for r in cur.fetchall()}

    return {"data": {**stats, "dismiss_reasons": dismiss_breakdown}}


@router.get("/projects/{project_id}/onboarding")
def get_onboarding_status(project_id: str):
    """Get the onboarding phase and status for a project."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT p.id, p.name, p.onboarding_phase::text as phase,
                   (SELECT COUNT(*) FROM signals WHERE project_id = p.id) as signal_count,
                   (SELECT COUNT(*) FROM intelligence_items WHERE project_id = p.id
                    AND status IN ('new', 'active')) as active_items,
                   (SELECT COUNT(*) FROM synthesis_cycles WHERE project_id = p.id
                    AND completed_at IS NOT NULL) as completed_cycles,
                   (SELECT COUNT(*) FROM rfis WHERE project_id = p.id AND is_deleted = FALSE) as rfi_count,
                   (SELECT COUNT(*) FROM submittals WHERE project_id = p.id AND is_deleted = FALSE) as submittal_count,
                   (SELECT COUNT(*) FROM drawings WHERE project_id = p.id AND is_deleted = FALSE) as drawing_count
            FROM projects p WHERE p.id = %s
        """, (project_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        phase = row["phase"]
        data = serialize_row(row)

        # Evaluate go-live readiness
        data["go_live_criteria"] = {
            "has_signals": row["signal_count"] > 0,
            "has_active_items": row["active_items"] > 0,
            "has_completed_cycles": row["completed_cycles"] >= 5,
            "has_data": (row["rfi_count"] + row["submittal_count"] + row["drawing_count"]) > 0,
        }
        data["go_live_ready"] = all(data["go_live_criteria"].values())
        return {"data": data}


@router.post("/admin/set-onboarding-phase")
def set_onboarding_phase(
    project_id: str = Query(...),
    phase: str = Query(..., description="historical_ingest, calibration, or live"),
):
    """Admin endpoint to transition a project's onboarding phase."""
    valid_phases = ("historical_ingest", "calibration", "live")
    if phase not in valid_phases:
        raise HTTPException(status_code=400, detail=f"Phase must be one of: {valid_phases}")

    with get_cursor() as cur:
        cur.execute("SELECT id, onboarding_phase::text as current FROM projects WHERE id = %s", (project_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        current = row["current"]
        cur.execute("""
            UPDATE projects SET onboarding_phase = %s::onboarding_phase
            WHERE id = %s
        """, (phase, project_id))

    logger.info(f"Onboarding phase for {project_id}: {current} → {phase}")
    return {"data": {"project_id": project_id, "previous_phase": current, "new_phase": phase}}


@router.post("/admin/go-live")
def go_live(
    project_id: str = Query(...),
    force: bool = Query(False, description="Skip criteria validation"),
):
    """Validate exit criteria and transition project from calibration → live.

    Exit criteria (per CC-6.2 spec):
    - Currently in calibration phase
    - Has signals generated
    - Has at least 1 intelligence item
    - Has completed at least 5 synthesis cycles
    - Has ingested Procore data (RFIs + submittals + drawings > 0)
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT p.id, p.onboarding_phase::text as phase,
                   (SELECT COUNT(*) FROM signals WHERE project_id = p.id) as signal_count,
                   (SELECT COUNT(*) FROM intelligence_items WHERE project_id = p.id
                    AND status IN ('new', 'active')) as active_items,
                   (SELECT COUNT(*) FROM synthesis_cycles WHERE project_id = p.id
                    AND completed_at IS NOT NULL) as completed_cycles,
                   (SELECT COUNT(*) FROM rfis WHERE project_id = p.id AND is_deleted = FALSE) as rfi_count,
                   (SELECT COUNT(*) FROM submittals WHERE project_id = p.id AND is_deleted = FALSE) as submittal_count,
                   (SELECT COUNT(*) FROM drawings WHERE project_id = p.id AND is_deleted = FALSE) as drawing_count
            FROM projects p WHERE p.id = %s
        """, (project_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        if row["phase"] != "calibration":
            raise HTTPException(
                status_code=400,
                detail=f"Project must be in calibration phase to go live (currently: {row['phase']})"
            )

        criteria = {
            "has_signals": row["signal_count"] > 0,
            "has_active_items": row["active_items"] > 0,
            "has_completed_cycles": row["completed_cycles"] >= 5,
            "has_data": (row["rfi_count"] + row["submittal_count"] + row["drawing_count"]) > 0,
        }
        all_met = all(criteria.values())

        if not all_met and not force:
            return {
                "data": {
                    "project_id": project_id,
                    "go_live_approved": False,
                    "criteria": criteria,
                    "message": "Exit criteria not met. Use force=true to override.",
                }
            }

        # Transition to live
        cur.execute("""
            UPDATE projects SET onboarding_phase = 'live'::onboarding_phase
            WHERE id = %s
        """, (project_id,))

        logger.info(f"Project {project_id} transitioned to LIVE (force={force}, criteria={criteria})")
        return {
            "data": {
                "project_id": project_id,
                "go_live_approved": True,
                "criteria": criteria,
                "forced": force,
            }
        }


@router.post("/radar/monitor")
def trigger_radar_monitoring(project_id: str = Query(...)):
    """Run the Radar passive monitoring pipeline against recent signals."""
    try:
        from radar_monitor import evaluate_signals_against_radar
        from steelsync_db import get_cursor as gc, serialize_rows as sr
        with gc() as cur:
            cur.execute("""
                SELECT id, project_id, signal_type, signal_category, summary,
                       confidence, strength, effective_weight, entity_type,
                       entity_value, supporting_context_json, source_document_id
                FROM signals
                WHERE project_id = %s AND archived_at IS NULL
                ORDER BY created_at DESC LIMIT 50
            """, (project_id,))
            signals = sr(cur.fetchall())
        results = evaluate_signals_against_radar(project_id, signals)
        return {"status": "completed", "results": results}
    except Exception as e:
        logger.error(f"Radar monitoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            intel_ready = _check_intel_tables_exist(cur)
            radar_ready = _check_radar_tables_exist(cur)
            return {
                "status": "healthy",
                "database": "connected",
                "intelligence_layer": "ready" if intel_ready else "pending",
                "radar": "ready" if radar_ready else "pending",
                "service": "steelsync-command-center",
            }
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
