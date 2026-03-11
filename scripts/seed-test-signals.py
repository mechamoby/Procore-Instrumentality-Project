#!/usr/bin/env python3
"""Seed test signals for SteelSync synthesis validation (CC-3.5).

Creates realistic test signal data for 5 construction scenarios to validate
that the synthesis engine produces genuine intelligence, not reformatted summaries.

Usage:
    python3 scripts/seed-test-signals.py [--project-id UUID]

If no project_id is given, uses the first active project in the database.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

import psycopg2
import psycopg2.extras

DB_NAME = os.environ.get("EVA00_DB", "nerv_eva00")
DB_USER = os.environ.get("EVA00_DB_USER", "moby")
DB_HOST = os.environ.get("EVA00_DB_HOST", "localhost")
DB_PORT = os.environ.get("EVA00_DB_PORT", "5432")


def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, host=DB_HOST, port=DB_PORT,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def insert_signal(cur, project_id, **kwargs):
    """Insert a test signal."""
    sig_id = str(uuid4())
    cur.execute("""
        INSERT INTO signals (
            id, project_id, source_type, signal_type, signal_category,
            summary, confidence, strength, effective_weight,
            decay_profile, entity_type, entity_value,
            supporting_context_json, created_at
        ) VALUES (
            %s, %s, %s::signal_source_type, %s, %s::signal_category,
            %s, %s, %s, %s,
            %s::decay_profile, %s, %s,
            %s, %s
        )
    """, (
        sig_id, project_id,
        kwargs.get("source_type", "procore_webhook"),
        kwargs["signal_type"],
        kwargs["signal_category"],
        kwargs["summary"],
        kwargs.get("confidence", 0.9),
        kwargs.get("strength", 0.8),
        kwargs.get("confidence", 0.9) * kwargs.get("strength", 0.8),
        kwargs.get("decay_profile", "medium_72h"),
        kwargs.get("entity_type"),
        kwargs.get("entity_value"),
        json.dumps(kwargs.get("context", {})),
        kwargs.get("created_at", datetime.now()),
    ))
    return sig_id


def scenario_1_mechanical_behind(cur, project_id):
    """Scenario 1: Mechanical rough-in falling behind.
    Daily log shows declining manpower + RFI overdue + email promise it's on track.
    Tests: contradiction detection.
    """
    print("  Scenario 1: Mechanical rough-in behind schedule (contradiction)")
    now = datetime.now()

    insert_signal(cur, project_id,
        signal_type="daily_log_manpower_decline",
        signal_category="status_change",
        summary="Mechanical contractor headcount dropped from 12 to 4 workers over the past 3 days",
        confidence=0.95, strength=0.9,
        entity_type="daily_report", entity_value="2026-03-07",
        context={"trade": "mechanical", "trend": "declining", "days": [12, 8, 4]},
        created_at=now - timedelta(hours=2),
    )

    insert_signal(cur, project_id,
        signal_type="rfi_became_overdue",
        signal_category="status_change",
        summary="RFI #023 'HVAC duct routing at grid C-4' is 5 days overdue (mechanical coordination)",
        confidence=0.98, strength=0.85,
        entity_type="rfi", entity_value="023",
        context={"days_overdue": 5, "trade": "mechanical"},
        created_at=now - timedelta(hours=4),
    )

    insert_signal(cur, project_id,
        signal_type="schedule_milestone_approaching",
        signal_category="timeline",
        summary="Milestone 'Mechanical Rough-In Complete' due in 8 days (March 18). Currently 35% complete.",
        confidence=0.98, strength=0.9,
        entity_type="schedule_activity", entity_value="Mechanical Rough-In Complete",
        context={"days_until": 8, "percent_complete": 35, "is_critical": True},
        created_at=now - timedelta(hours=1),
    )

    insert_signal(cur, project_id,
        signal_type="correspondence_assurance",
        signal_category="document_significance",
        summary="Email from ABC Mechanical: 'We are on track for the March 18 milestone. Additional crew arriving Monday.'",
        confidence=0.7, strength=0.6,
        entity_type="correspondence", entity_value="ABC Mechanical",
        context={"from": "ABC Mechanical PM", "claim": "on track", "date": "2026-03-07"},
        created_at=now - timedelta(hours=3),
    )


def scenario_2_rfi_convergence(cur, project_id):
    """Scenario 2: Multiple RFIs converging on same coordination issue.
    Three different trades filing RFIs about the same ceiling area.
    Tests: convergence detection.
    """
    print("  Scenario 2: Multi-trade RFI convergence at ceiling grid B-3")
    now = datetime.now()

    insert_signal(cur, project_id,
        signal_type="rfi_became_overdue",
        signal_category="status_change",
        summary="RFI #031 'Electrical conduit routing conflict at grid B-3 ceiling' — 3 days overdue",
        confidence=0.98, strength=0.8,
        entity_type="rfi", entity_value="031",
        context={"trade": "electrical", "location": "grid B-3 ceiling", "days_overdue": 3},
        created_at=now - timedelta(hours=6),
    )

    insert_signal(cur, project_id,
        signal_type="rfi_became_overdue",
        signal_category="status_change",
        summary="RFI #034 'Fire sprinkler head placement at grid B-3' — 2 days overdue",
        confidence=0.98, strength=0.75,
        entity_type="rfi", entity_value="034",
        context={"trade": "fire_protection", "location": "grid B-3", "days_overdue": 2},
        created_at=now - timedelta(hours=5),
    )

    insert_signal(cur, project_id,
        signal_type="rfi_became_overdue",
        signal_category="status_change",
        summary="RFI #036 'HVAC duct clearance at grid B-3 plenum space' — filed today, needs architect response",
        confidence=0.98, strength=0.7,
        entity_type="rfi", entity_value="036",
        context={"trade": "mechanical", "location": "grid B-3 plenum", "days_overdue": 0},
        created_at=now - timedelta(hours=2),
    )


def scenario_3_submittal_resubmit_no_revision(cur, project_id):
    """Scenario 3: Submittal rejected then resubmitted without changes.
    Tests: pattern/decay detection.
    """
    print("  Scenario 3: Submittal resubmitted without revision")
    now = datetime.now()

    insert_signal(cur, project_id,
        signal_type="submittal_rejected",
        signal_category="status_change",
        summary="Submittal #047 'Concrete Mix Design' was rejected — reviewer noted 'air content specification does not meet spec section 03 30 00'",
        confidence=1.0, strength=0.9,
        entity_type="submittal", entity_value="047",
        context={"rejection_reason": "air content spec non-compliance", "spec_section": "03 30 00"},
        created_at=now - timedelta(days=3),
    )

    insert_signal(cur, project_id,
        signal_type="submittal_resubmitted",
        signal_category="status_change",
        summary="Submittal #047.1 'Concrete Mix Design' resubmitted with no revision number change and identical file hash",
        confidence=0.95, strength=0.85,
        entity_type="submittal", entity_value="047.1",
        context={"original": "047", "file_hash_match": True, "revision_unchanged": True},
        created_at=now - timedelta(hours=4),
    )


def scenario_4_quiet_day(cur, project_id):
    """Scenario 4: A quiet day with no material changes.
    Only routine signals. Tests: empty cycle produces minimal output.
    """
    print("  Scenario 4: Quiet day — routine signals only")
    now = datetime.now()

    insert_signal(cur, project_id,
        signal_type="daily_log_submitted",
        signal_category="status_change",
        summary="Daily log for March 9 submitted on time. 28 workers on site. No delays reported.",
        confidence=0.95, strength=0.3,  # Low strength = routine
        decay_profile="fast_24h",
        entity_type="daily_report", entity_value="2026-03-09",
        context={"workers": 28, "delays": False, "routine": True},
        created_at=now - timedelta(hours=1),
    )


def scenario_5_change_order_chain(cur, project_id):
    """Scenario 5: Chain of change orders from unforeseen conditions.
    Multiple COs from same root cause building up financial exposure.
    Tests: emerging risk detection.
    """
    print("  Scenario 5: Change order chain — unforeseen conditions")
    now = datetime.now()

    insert_signal(cur, project_id,
        signal_type="change_order_status_changed",
        signal_category="status_change",
        summary="CO #008 'Additional rock removal — Building A foundation' approved for $45,000",
        confidence=0.98, strength=0.8,
        entity_type="change_order", entity_value="008",
        context={"amount": 45000, "reason": "unforeseen_condition", "status": "approved"},
        created_at=now - timedelta(days=5),
    )

    insert_signal(cur, project_id,
        signal_type="change_order_status_changed",
        signal_category="status_change",
        summary="CO #011 'Extended dewatering — Building A excavation' pending approval for $28,000",
        confidence=0.98, strength=0.8,
        entity_type="change_order", entity_value="011",
        context={"amount": 28000, "reason": "unforeseen_condition", "status": "pending"},
        created_at=now - timedelta(days=2),
    )

    insert_signal(cur, project_id,
        signal_type="change_order_status_changed",
        signal_category="status_change",
        summary="CO #013 'Revised foundation design — Building A' submitted for $67,000. References geotechnical report findings.",
        confidence=0.98, strength=0.85,
        entity_type="change_order", entity_value="013",
        context={"amount": 67000, "reason": "unforeseen_condition", "status": "pending", "related_cos": ["008", "011"]},
        created_at=now - timedelta(hours=6),
    )

    insert_signal(cur, project_id,
        signal_type="schedule_milestone_approaching",
        signal_category="timeline",
        summary="Milestone 'Building A Foundation Complete' due in 12 days. Foundation work delayed by unforeseen rock conditions.",
        confidence=0.95, strength=0.8,
        entity_type="schedule_activity", entity_value="Building A Foundation Complete",
        context={"days_until": 12, "percent_complete": 40, "is_critical": True, "delay_cause": "unforeseen conditions"},
        created_at=now - timedelta(hours=3),
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed test signals for synthesis validation")
    parser.add_argument("--project-id", help="Project UUID to seed signals for")
    args = parser.parse_args()

    conn = get_conn()

    try:
        with conn.cursor() as cur:
            # Check if intelligence tables exist
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables WHERE table_name = 'signals'
                )
            """)
            if not cur.fetchone()["exists"]:
                print("ERROR: Intelligence layer tables not found.")
                print("Run: python3 scripts/init-intelligence-layer.py")
                sys.exit(1)

            # Get project ID
            project_id = args.project_id
            if not project_id:
                cur.execute("SELECT id, name FROM projects WHERE status = 'active' AND is_deleted = FALSE LIMIT 1")
                project = cur.fetchone()
                if not project:
                    print("ERROR: No active projects found in database.")
                    sys.exit(1)
                project_id = str(project["id"])
                print(f"Using project: {project['name']} ({project_id})")

            print(f"\nSeeding test signals for project {project_id}...\n")

            scenario_1_mechanical_behind(cur, project_id)
            scenario_2_rfi_convergence(cur, project_id)
            scenario_3_submittal_resubmit_no_revision(cur, project_id)
            scenario_4_quiet_day(cur, project_id)
            scenario_5_change_order_chain(cur, project_id)

            conn.commit()

            # Count inserted signals
            cur.execute("SELECT COUNT(*) as cnt FROM signals WHERE project_id = %s", (project_id,))
            count = cur.fetchone()["cnt"]
            print(f"\nDone. Total signals in database for this project: {count}")
            print("\nNext steps:")
            print(f"  1. Run synthesis: POST /api/synthesis/trigger?project_id={project_id}&cycle_type=morning_briefing")
            print("  2. Check results: GET /api/projects/{project_id}/intelligence-items?include=evidence")
            print("  3. Or visit: /command-center")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
