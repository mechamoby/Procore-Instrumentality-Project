#!/usr/bin/env python3
"""CC-3.5 Synthesis Validation Gate — Execute and document test scenarios.

Seeds specific signals per scenario, triggers synthesis, captures the output,
and produces a formatted validation report.

Usage:
    cd nerv-interface
    python3 ../scripts/run-synthesis-validation.py

Requires: ANTHROPIC_API_KEY and SYNTHESIS_MODEL in environment.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add nerv-interface to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nerv-interface"))

from steelsync_db import get_cursor
from synthesis_engine import SynthesisEngine

PROJECT_ID = "0827cef6-4a29-4b9b-9c51-b77c8ec88908"  # Sandbox Test Project
VALIDATION_MARKER = "CC-3.5-VALIDATION"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def insert_signal(project_id, signal_type, signal_category, summary, confidence,
                  strength=1.0, entity_type=None, entity_value=None,
                  source_type="procore_webhook", decay_profile="medium_72h",
                  supporting_context=None, created_at=None):
    """Insert a test signal directly into the database."""
    sig_id = str(uuid4())
    created = created_at or datetime.now()
    with get_cursor() as cur:
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
            sig_id, project_id, source_type, signal_type, signal_category,
            summary, confidence, strength, round(confidence * strength, 2),
            decay_profile, entity_type, entity_value or VALIDATION_MARKER,
            json.dumps(supporting_context) if supporting_context else None,
            created,
        ))
    return sig_id


def cleanup_validation_signals():
    """Remove all signals created for validation (and their evidence links)."""
    with get_cursor() as cur:
        # Delete evidence links first (FK constraint)
        cur.execute("""
            DELETE FROM intelligence_item_evidence
            WHERE signal_id IN (
                SELECT id FROM signals WHERE entity_value = %s
            )
        """, (VALIDATION_MARKER,))
        # Then delete the signals
        cur.execute("DELETE FROM signals WHERE entity_value = %s", (VALIDATION_MARKER,))


def cleanup_validation_items():
    """Remove intelligence items created during validation cycles."""
    with get_cursor() as cur:
        # Delete evidence links first (FK constraint)
        cur.execute("""
            DELETE FROM intelligence_item_evidence
            WHERE intelligence_item_id IN (
                SELECT id FROM intelligence_items
                WHERE synthesis_cycle_id IN (
                    SELECT id FROM synthesis_cycles
                    WHERE error_log = %s
                )
            )
        """, (VALIDATION_MARKER,))
        # Delete items
        cur.execute("""
            DELETE FROM intelligence_items
            WHERE synthesis_cycle_id IN (
                SELECT id FROM synthesis_cycles
                WHERE error_log = %s
            )
        """, (VALIDATION_MARKER,))
        # Delete cycles
        cur.execute("""
            DELETE FROM synthesis_cycles WHERE error_log = %s
        """, (VALIDATION_MARKER,))


def get_cycle_results(cycle_id):
    """Get synthesis cycle details and its intelligence items."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, cycle_type, model_used, overall_health,
                   signals_processed, items_created, items_updated, items_resolved,
                   input_tokens, output_tokens, cycle_summary
            FROM synthesis_cycles WHERE id = %s
        """, (cycle_id,))
        cycle = cur.fetchone()

        cur.execute("""
            SELECT item_type, title, summary, severity, confidence, status,
                   recommended_attention_level, source_evidence_count
            FROM intelligence_items WHERE synthesis_cycle_id = %s
            ORDER BY severity DESC
        """, (cycle_id,))
        items = cur.fetchall()

        return cycle, items


def run_synthesis_for_validation(project_id, cycle_type="morning_briefing"):
    """Run synthesis and tag the cycle for cleanup."""
    cycle_id = SynthesisEngine.run_cycle(project_id, cycle_type)
    if cycle_id:
        # Tag cycle for cleanup identification
        with get_cursor() as cur:
            cur.execute("""
                UPDATE synthesis_cycles SET error_log = %s WHERE id = %s
            """, (VALIDATION_MARKER, cycle_id))
    return cycle_id


def assess_quality(items, scenario_name):
    """Assess items against 4 quality criteria."""
    criteria = {
        "actionable": True,
        "sourced": True,
        "non_fabricated": True,
        "appropriately_scoped": True,
    }
    notes = []

    for item in items:
        # Actionable: has specific recommendation implied by type and severity
        if not item.get("title") or not item.get("summary"):
            criteria["actionable"] = False
            notes.append(f"Item missing title/summary: {item}")

        # Sourced: has evidence count > 0
        if item.get("source_evidence_count", 0) == 0:
            criteria["sourced"] = False
            notes.append(f"Item has no source evidence: {item.get('title', '?')}")

        # Non-fabricated: confidence > 0
        if item.get("confidence", 0) <= 0:
            criteria["non_fabricated"] = False
            notes.append(f"Item has zero confidence: {item.get('title', '?')}")

        # Appropriately scoped: severity matches the actual concern level
        if item.get("severity") == "critical" and item.get("confidence", 0) < 0.7:
            criteria["appropriately_scoped"] = False
            notes.append(f"Critical item with low confidence: {item.get('title', '?')}")

    return criteria, notes


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class ScenarioResult:
    def __init__(self, name, input_signals, prompt_template, items, cycle,
                 quality_criteria, quality_notes):
        self.name = name
        self.input_signals = input_signals
        self.prompt_template = prompt_template
        self.items = items
        self.cycle = cycle
        self.quality_criteria = quality_criteria
        self.quality_notes = quality_notes

    def format(self):
        lines = [
            f"### Scenario: {self.name}",
            "",
            f"**Input signals:** {self.input_signals['count']} signals "
            f"({', '.join(self.input_signals['types'])})",
            "",
            "Signal details:",
        ]
        for s in self.input_signals.get("details", []):
            lines.append(f"- [{s['category']}] {s['summary']} (conf: {s['confidence']})")

        lines.append("")
        lines.append(f"**Prompt template:** {self.prompt_template}")
        lines.append("")

        if self.cycle:
            lines.append(f"**Model used:** {self.cycle.get('model_used', 'unknown')}")
            lines.append(f"**Overall health:** {self.cycle.get('overall_health', 'unknown')}")
            lines.append(f"**Signals processed:** {self.cycle.get('signals_processed', 0)}")
            lines.append(f"**Tokens:** {self.cycle.get('input_tokens', 0)} in / "
                         f"{self.cycle.get('output_tokens', 0)} out")
            lines.append(f"**Cycle summary:** {self.cycle.get('cycle_summary', 'N/A')}")
        lines.append("")

        lines.append(f"**Intelligence items produced:** {len(self.items)}")
        lines.append("")
        if self.items:
            for item in self.items:
                lines.append(
                    f"- **[{item.get('severity', '?').upper()}]** "
                    f"{item.get('title', '?')}"
                )
                lines.append(f"  - Type: {item.get('item_type', '?')}")
                lines.append(f"  - Summary: {item.get('summary', '?')[:200]}")
                lines.append(f"  - Confidence: {item.get('confidence', '?')}")
                lines.append(f"  - Evidence count: {item.get('source_evidence_count', 0)}")
                lines.append(f"  - Attention: {item.get('recommended_attention_level', '?')}")
                lines.append("")
        else:
            lines.append("*(No items produced)*")
            lines.append("")

        lines.append("**Quality criteria:**")
        for criterion, passed in self.quality_criteria.items():
            status = "PASS" if passed else "FAIL"
            label = criterion.replace("_", " ").title()
            lines.append(f"- {label}? **{status}**")

        if self.quality_notes:
            lines.append("")
            lines.append("**Notes:**")
            for note in self.quality_notes:
                lines.append(f"- {note}")

        lines.append("")
        all_pass = all(self.quality_criteria.values())
        lines.append(f"**Scenario verdict: {'PASS' if all_pass else 'FAIL'}**")
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)


def scenario_1_contradiction():
    """Contradiction: Overdue RFI + email turnaround promise from same sub."""
    print("  Running Scenario 1: Contradiction...")
    cleanup_validation_signals()

    signals_info = []

    # RFI overdue signal
    s1 = insert_signal(
        PROJECT_ID, "rfis_overdue", "status_change",
        "RFI #127 (Foundation Reinforcement) is 12 days overdue — assigned to "
        "Marco's Concrete LLC. Originally due Feb 28.",
        confidence=0.95, entity_type="rfi", entity_value=VALIDATION_MARKER,
        supporting_context={"rfi_id": 127, "days_overdue": 12,
                            "assignee": "Marco's Concrete LLC"},
    )
    signals_info.append({"category": "status_change", "confidence": 0.95,
                         "summary": "RFI #127 12 days overdue — Marco's Concrete LLC"})

    # Second overdue RFI from same sub
    s2 = insert_signal(
        PROJECT_ID, "rfis_overdue", "status_change",
        "RFI #134 (Slab Thickness Clarification) is 8 days overdue — assigned to "
        "Marco's Concrete LLC. Due Mar 4.",
        confidence=0.95, entity_type="rfi", entity_value=VALIDATION_MARKER,
        supporting_context={"rfi_id": 134, "days_overdue": 8,
                            "assignee": "Marco's Concrete LLC"},
    )
    signals_info.append({"category": "status_change", "confidence": 0.95,
                         "summary": "RFI #134 8 days overdue — Marco's Concrete LLC"})

    # Email signal: sub promises turnaround
    s3 = insert_signal(
        PROJECT_ID, "document_significance", "document_significance",
        "Email from Marco's Concrete LLC (Mar 11): 'We will have all outstanding "
        "RFI responses to you by end of week.' — contradicts 12-day overdue status.",
        confidence=0.85, entity_type="email",
        source_type="document_pipeline", entity_value=VALIDATION_MARKER,
        supporting_context={"sender": "Marco's Concrete LLC",
                            "promise": "all RFIs by end of week",
                            "contradicts": ["RFI #127", "RFI #134"]},
    )
    signals_info.append({"category": "document_significance", "confidence": 0.85,
                         "summary": "Email from Marco's Concrete promising RFI turnaround"})

    cycle_id = run_synthesis_for_validation(PROJECT_ID, "morning_briefing")
    cycle, items = get_cycle_results(cycle_id) if cycle_id else (None, [])
    quality, notes = assess_quality(items, "contradiction")

    # Extra check: at least one item should mention contradiction or conflicting
    has_contradiction = any(
        "contradict" in (i.get("title", "") + i.get("summary", "")).lower()
        or "conflict" in (i.get("title", "") + i.get("summary", "")).lower()
        or i.get("item_type") == "contradiction"
        for i in items
    )
    if not has_contradiction and items:
        notes.append("WARNING: No item explicitly flags the contradiction between "
                     "overdue RFIs and email promise")

    return ScenarioResult(
        name="Contradiction — Overdue RFIs + Sub Email Promise",
        input_signals={"count": 3, "types": ["status_change", "document_significance"],
                       "details": signals_info},
        prompt_template="Morning Briefing (Template A)",
        items=items, cycle=dict(cycle) if cycle else None,
        quality_criteria=quality, quality_notes=notes,
    )


def scenario_2_convergence():
    """Convergence: Multiple signals from different sources pointing at same trade."""
    print("  Running Scenario 2: Convergence...")
    cleanup_validation_signals()

    signals_info = []

    # Submittal rejected for electrical sub
    s1 = insert_signal(
        PROJECT_ID, "submittals_rejected", "status_change",
        "Submittal #089 (Panel Schedule) REJECTED — reviewer: John Chen. "
        "Reason: 'Does not match updated single-line diagram.' Trade: Electrical.",
        confidence=0.95, entity_type="submittal", entity_value=VALIDATION_MARKER,
        supporting_context={"submittal_id": 89, "trade": "electrical",
                            "reason": "Does not match updated single-line diagram"},
    )
    signals_info.append({"category": "status_change", "confidence": 0.95,
                         "summary": "Submittal #089 (Panel Schedule) rejected — electrical"})

    # Electrical RFI overdue
    s2 = insert_signal(
        PROJECT_ID, "rfis_overdue", "status_change",
        "RFI #156 (Electrical Room Clearance) is 5 days overdue — assigned to "
        "Sparks Electric. Due Mar 7.",
        confidence=0.95, entity_type="rfi", entity_value=VALIDATION_MARKER,
        supporting_context={"rfi_id": 156, "days_overdue": 5,
                            "trade": "electrical", "assignee": "Sparks Electric"},
    )
    signals_info.append({"category": "status_change", "confidence": 0.95,
                         "summary": "RFI #156 (Electrical Room Clearance) overdue"})

    # Submittal overdue for electrical sub
    s3 = insert_signal(
        PROJECT_ID, "submittals_overdue", "timeline",
        "Submittal #091 (Conduit Routing Plan) is 10 days past required date. "
        "Trade: Electrical. Assigned to Sparks Electric.",
        confidence=0.90, entity_type="submittal", entity_value=VALIDATION_MARKER,
        supporting_context={"submittal_id": 91, "days_overdue": 10,
                            "trade": "electrical", "assignee": "Sparks Electric"},
    )
    signals_info.append({"category": "timeline", "confidence": 0.90,
                         "summary": "Submittal #091 (Conduit Routing) 10 days overdue"})

    # Schedule milestone approaching for electrical
    s4 = insert_signal(
        PROJECT_ID, "schedule_milestone", "timeline",
        "Milestone: Electrical rough-in completion due in 5 days (Mar 17). "
        "Multiple electrical submittals and RFIs still unresolved.",
        confidence=0.80, entity_type="schedule", entity_value=VALIDATION_MARKER,
        supporting_context={"milestone": "Electrical rough-in", "days_until": 5,
                            "trade": "electrical"},
    )
    signals_info.append({"category": "timeline", "confidence": 0.80,
                         "summary": "Electrical rough-in milestone in 5 days"})

    cycle_id = run_synthesis_for_validation(PROJECT_ID, "morning_briefing")
    cycle, items = get_cycle_results(cycle_id) if cycle_id else (None, [])
    quality, notes = assess_quality(items, "convergence")

    # Check: should detect pattern across electrical trade
    has_convergence = any(
        "electrical" in (i.get("title", "") + i.get("summary", "")).lower()
        or "pattern" in (i.get("title", "") + i.get("summary", "")).lower()
        or "converge" in (i.get("title", "") + i.get("summary", "")).lower()
        or i.get("item_type") in ("convergence", "pattern_match", "emerging_risk")
        for i in items
    )
    if not has_convergence and items:
        notes.append("WARNING: No item explicitly identifies the convergence across "
                     "electrical trade signals")

    return ScenarioResult(
        name="Convergence — Multiple Electrical Trade Signals",
        input_signals={"count": 4, "types": ["status_change", "timeline"],
                       "details": signals_info},
        prompt_template="Morning Briefing (Template A)",
        items=items, cycle=dict(cycle) if cycle else None,
        quality_criteria=quality, quality_notes=notes,
    )


def scenario_3_quiet_day():
    """Quiet day: Minimal signals → minimal or empty output."""
    print("  Running Scenario 3: Quiet Day...")
    cleanup_validation_signals()

    signals_info = []

    # One low-priority signal only
    s1 = insert_signal(
        PROJECT_ID, "daily_log_missing", "status_change",
        "Daily log not submitted for yesterday (Mar 11).",
        confidence=0.95, strength=0.5, entity_type="daily_log",
        entity_value=VALIDATION_MARKER,
    )
    signals_info.append({"category": "status_change", "confidence": 0.95,
                         "summary": "Daily log missing for Mar 11"})

    cycle_id = run_synthesis_for_validation(PROJECT_ID, "morning_briefing")
    cycle, items = get_cycle_results(cycle_id) if cycle_id else (None, [])
    quality, notes = assess_quality(items, "quiet_day")

    # Quiet day specific: should produce minimal NEW output.
    # NOTE: Because synthesis also runs a deterministic sweep against live data,
    # items from existing signals are expected. The key criterion is that the
    # single test signal (daily log missing) should not by itself trigger
    # high/critical items. Items from the existing backlog are legitimate.
    if len(items) > 3:
        notes.append(f"WARNING: {len(items)} items from quiet-day scenario — "
                     f"verify items are from existing backlog, not fabricated")
    elif len(items) == 0:
        notes.append("Good: zero items produced from quiet-day scenario")
    else:
        notes.append(f"{len(items)} item(s) produced — checking if sourced from "
                     f"existing backlog signals (expected) vs fabricated from test signal")
        # Items from live data are legitimate — only fail if items have
        # zero evidence (truly fabricated)
        for item in items:
            if item.get("source_evidence_count", 0) == 0:
                quality["non_fabricated"] = False
                notes.append(f"FAIL: Unsourced item: {item.get('title')}")

    return ScenarioResult(
        name="Quiet Day — Minimal Signals",
        input_signals={"count": 1, "types": ["status_change"],
                       "details": signals_info},
        prompt_template="Morning Briefing (Template A)",
        items=items, cycle=dict(cycle) if cycle else None,
        quality_criteria=quality, quality_notes=notes,
    )


def scenario_4_high_volume():
    """High volume: 10+ mixed signals → prioritized output."""
    print("  Running Scenario 4: High Volume...")
    cleanup_validation_signals()

    signals_info = []

    # 5 overdue RFIs of varying severity
    for i, (rfi_num, days) in enumerate([(101, 3), (102, 7), (103, 14), (104, 21), (105, 2)]):
        insert_signal(
            PROJECT_ID, "rfis_overdue", "status_change",
            f"RFI #{rfi_num} is {days} days overdue — assigned to Sub {chr(65+i)}.",
            confidence=0.95, entity_type="rfi", entity_value=VALIDATION_MARKER,
            supporting_context={"rfi_id": rfi_num, "days_overdue": days},
        )
        signals_info.append({"category": "status_change", "confidence": 0.95,
                             "summary": f"RFI #{rfi_num} {days} days overdue"})

    # 3 overdue submittals
    for i, (sub_num, days) in enumerate([(201, 5), (202, 12), (203, 1)]):
        insert_signal(
            PROJECT_ID, "submittals_overdue", "timeline",
            f"Submittal #{sub_num} is {days} days past required date.",
            confidence=0.90, entity_type="submittal", entity_value=VALIDATION_MARKER,
            supporting_context={"submittal_id": sub_num, "days_overdue": days},
        )
        signals_info.append({"category": "timeline", "confidence": 0.90,
                             "summary": f"Submittal #{sub_num} {days} days overdue"})

    # 1 rejected submittal
    insert_signal(
        PROJECT_ID, "submittals_rejected", "status_change",
        "Submittal #204 (Fire Stopping Details) REJECTED — incomplete specs.",
        confidence=0.95, entity_type="submittal", entity_value=VALIDATION_MARKER,
        supporting_context={"submittal_id": 204, "reason": "incomplete specs"},
    )
    signals_info.append({"category": "status_change", "confidence": 0.95,
                         "summary": "Submittal #204 rejected"})

    # 1 missing daily log
    insert_signal(
        PROJECT_ID, "daily_log_missing", "status_change",
        "Daily log not submitted for yesterday.",
        confidence=0.95, strength=0.5, entity_type="daily_log",
        entity_value=VALIDATION_MARKER,
    )
    signals_info.append({"category": "status_change", "confidence": 0.95,
                         "summary": "Daily log missing"})

    # 1 change order
    insert_signal(
        PROJECT_ID, "change_order_status_changed", "status_change",
        "Change Order #003 status changed to 'Approved' — $45,000 electrical scope add.",
        confidence=0.95, entity_type="change_order", entity_value=VALIDATION_MARKER,
        supporting_context={"co_id": 3, "amount": 45000, "status": "Approved"},
    )
    signals_info.append({"category": "status_change", "confidence": 0.95,
                         "summary": "CO #003 approved — $45K electrical add"})

    cycle_id = run_synthesis_for_validation(PROJECT_ID, "morning_briefing")
    cycle, items = get_cycle_results(cycle_id) if cycle_id else (None, [])
    quality, notes = assess_quality(items, "high_volume")

    # Check: should prioritize the worst items (21-day overdue RFI, 12-day submittal)
    if len(items) > 8:
        notes.append(f"WARNING: {len(items)} items may overwhelm — synthesis should "
                     f"consolidate similar signals")

    return ScenarioResult(
        name="High Volume — 11 Mixed Signals",
        input_signals={"count": 11, "types": ["status_change", "timeline"],
                       "details": signals_info},
        prompt_template="Morning Briefing (Template A)",
        items=items, cycle=dict(cycle) if cycle else None,
        quality_criteria=quality, quality_notes=notes,
    )


def scenario_5_cross_cycle_continuity():
    """Cross-cycle: Morning → add signals → Midday → verify reference."""
    print("  Running Scenario 5: Cross-Cycle Continuity...")
    cleanup_validation_signals()

    signals_info_morning = []
    signals_info_midday = []

    # Morning signals
    insert_signal(
        PROJECT_ID, "rfis_overdue", "status_change",
        "RFI #200 (HVAC Duct Routing) is 6 days overdue — assigned to CoolAir Mechanical.",
        confidence=0.95, entity_type="rfi", entity_value=VALIDATION_MARKER,
        supporting_context={"rfi_id": 200, "days_overdue": 6,
                            "assignee": "CoolAir Mechanical"},
    )
    signals_info_morning.append({"category": "status_change", "confidence": 0.95,
                                 "summary": "RFI #200 HVAC overdue 6 days"})

    insert_signal(
        PROJECT_ID, "submittals_overdue", "timeline",
        "Submittal #300 (HVAC Equipment Schedule) is 4 days past required date.",
        confidence=0.90, entity_type="submittal", entity_value=VALIDATION_MARKER,
        supporting_context={"submittal_id": 300, "days_overdue": 4,
                            "trade": "HVAC"},
    )
    signals_info_morning.append({"category": "timeline", "confidence": 0.90,
                                 "summary": "Submittal #300 HVAC 4 days overdue"})

    # Run morning cycle
    print("    Running morning briefing...")
    morning_id = run_synthesis_for_validation(PROJECT_ID, "morning_briefing")
    morning_cycle, morning_items = get_cycle_results(morning_id) if morning_id else (None, [])

    # Add midday signals (escalation)
    insert_signal(
        PROJECT_ID, "rfis_overdue", "status_change",
        "RFI #201 (HVAC Return Air Path) is now also overdue — 1 day past due. "
        "Same sub: CoolAir Mechanical. Third HVAC-related delay this week.",
        confidence=0.95, entity_type="rfi", entity_value=VALIDATION_MARKER,
        supporting_context={"rfi_id": 201, "days_overdue": 1,
                            "assignee": "CoolAir Mechanical", "trade": "HVAC"},
    )
    signals_info_midday.append({"category": "status_change", "confidence": 0.95,
                                "summary": "RFI #201 HVAC Return Air also overdue"})

    # Run midday cycle
    print("    Running midday checkpoint...")
    midday_id = run_synthesis_for_validation(PROJECT_ID, "midday_checkpoint")
    midday_cycle, midday_items = get_cycle_results(midday_id) if midday_id else (None, [])

    quality, notes = assess_quality(midday_items, "cross_cycle")

    # Check: midday should reference morning findings
    if midday_cycle:
        summary = midday_cycle.get("cycle_summary", "")
        if not summary:
            notes.append("WARNING: No midday cycle summary produced")

    all_signals = signals_info_morning + signals_info_midday

    return ScenarioResult(
        name="Cross-Cycle Continuity — Morning → Midday",
        input_signals={"count": len(all_signals),
                       "types": ["status_change", "timeline"],
                       "details": all_signals},
        prompt_template="Morning Briefing (A) → Midday Checkpoint (B)",
        items=midday_items, cycle=dict(midday_cycle) if midday_cycle else None,
        quality_criteria=quality,
        quality_notes=[
            f"Morning cycle produced {len(morning_items)} items",
            f"Morning health: {morning_cycle.get('overall_health', '?') if morning_cycle else '?'}",
            f"Morning summary: {morning_cycle.get('cycle_summary', 'N/A')[:200] if morning_cycle else 'N/A'}",
            "",
            "Midday observations:",
        ] + notes,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print("CC-3.5 SYNTHESIS VALIDATION GATE")
    print(f"Executed: {datetime.now().isoformat()}")
    print(f"Model: {os.environ.get('SYNTHESIS_MODEL', 'default')}")
    print(f"Project: {PROJECT_ID}")
    print("=" * 72)
    print()

    scenarios = [
        scenario_1_contradiction,
        scenario_2_convergence,
        scenario_3_quiet_day,
        scenario_4_high_volume,
        scenario_5_cross_cycle_continuity,
    ]

    results = []
    for i, scenario_fn in enumerate(scenarios, 1):
        print(f"Scenario {i}/5: {scenario_fn.__doc__.split(chr(10))[0]}")
        try:
            result = scenario_fn()
            results.append(result)
            all_pass = all(result.quality_criteria.values())
            print(f"  → {'PASS' if all_pass else 'FAIL'} "
                  f"({len(result.items)} items produced)")
        except Exception as e:
            print(f"  → ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(None)
        print()

    # Final cleanup
    cleanup_validation_signals()
    cleanup_validation_items()

    # Generate report
    report_lines = [
        "# CC-3.5 Synthesis Validation Gate — Test Results",
        "",
        f"**Executed:** {datetime.now().isoformat()}",
        f"**Model:** {os.environ.get('SYNTHESIS_MODEL', 'default')}",
        f"**Project:** Sandbox Test Project ({PROJECT_ID})",
        "",
        "## Quality Criteria (per Intelligence Layer System Design v1, Section 10)",
        "",
        "1. **Actionable** — Each item has a clear title, summary, and severity",
        "2. **Sourced** — Each item links to source evidence (evidence count > 0)",
        "3. **Non-fabricated** — Items are grounded in actual signals, not hallucinated",
        "4. **Appropriately scoped** — Severity matches the actual concern level",
        "",
        "---",
        "",
    ]

    pass_count = 0
    fail_count = 0

    for result in results:
        if result:
            report_lines.append(result.format())
            if all(result.quality_criteria.values()):
                pass_count += 1
            else:
                fail_count += 1
        else:
            report_lines.append("### Scenario: ERROR — failed to execute\n\n---\n")
            fail_count += 1

    report_lines.extend([
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Scenarios executed | {len(results)} |",
        f"| Scenarios passed | {pass_count} |",
        f"| Scenarios failed | {fail_count} |",
        f"| Model | {os.environ.get('SYNTHESIS_MODEL', 'default')} |",
        f"| Timestamp | {datetime.now().isoformat()} |",
        "",
    ])

    report = "\n".join(report_lines)

    # Write report
    report_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "CC-3.5_Validation_Results.md"
    )
    with open(report_path, "w") as f:
        f.write(report)

    print("=" * 72)
    print(f"RESULTS: {pass_count} passed, {fail_count} failed out of {len(results)}")
    print(f"Report: {report_path}")
    print("=" * 72)

    return fail_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
