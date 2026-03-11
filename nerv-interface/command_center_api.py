"""SteelSync Command Center API — CC-1.2 + CC-1.3

REST API endpoints for the Command Center frontend:
- CC-1.2: Procore data (projects, RFIs, submittals, daily logs, schedule, change orders)
- CC-1.3: Intelligence data (signals, intelligence items, synthesis cycles)

All endpoints return consistent JSON with pagination support.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Body
from steelsync_db import get_cursor, serialize_row, serialize_rows

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
    sort: str = Query("due_date", description="Sort by: due_date, date_initiated, number"),
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

        sort_col = {"due_date": "r.due_date", "date_initiated": "r.date_initiated", "number": "r.number"}.get(sort, "r.due_date")

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
            ORDER BY {sort_col} ASC NULLS LAST
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = serialize_rows(cur.fetchall())
        return paginated_response(rows, total, limit, offset)


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
        return paginated_response(rows, total, limit, offset)


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
                   (SELECT COUNT(*) FROM rfis r WHERE r.project_id = p.id AND r.is_deleted = FALSE AND r.status NOT IN ('closed', 'answered', 'void') AND r.due_date < CURRENT_DATE) as overdue_rfis
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


# =============================================================================
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
