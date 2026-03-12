"""
CC-2.6 — Signal Deduplication Test Suite

Tests the SignalWriter dedup logic against 6 required scenarios from the
Command Center Ticketized Build Breakdown v1.

These are integration tests that hit the real database (nerv_eva00).
All test signals are written to a dedicated test project and cleaned up
after each test.

Usage:
    cd nerv-interface
    python3 -m pytest ../tests/test_signal_dedup.py -v

Or without pytest:
    cd nerv-interface
    python3 ../tests/test_signal_dedup.py
"""

import os
import sys
import uuid
import json
import time
from datetime import datetime

# Add nerv-interface to path so we can import SignalWriter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nerv-interface"))

from signal_generation import SignalWriter
from steelsync_db import get_cursor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_PROJECT_ID = "0827cef6-4a29-4b9b-9c51-b77c8ec88908"  # Sandbox Test Project
TEST_MARKER = "CC-2.6-TEST"  # Entity value marker to identify test signals


def cleanup_test_signals():
    """Remove only test-created signals (identified by entity_value marker)."""
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM signals WHERE entity_value = %s",
            (TEST_MARKER,),
        )


def make_doc_id() -> str:
    """Generate a valid UUID for source_document_id."""
    return str(uuid.uuid4())


def write_test_signal(
    signal_type: str = "rfis_overdue",
    source_document_id: str = None,
    project_id: str = None,
    supporting_context: dict = None,
):
    """Helper to write a signal with sensible defaults for testing."""
    return SignalWriter.write(
        project_id=project_id or TEST_PROJECT_ID,
        source_type="procore_webhook",
        signal_type=signal_type,
        signal_category="status_change",
        summary=f"Test signal: {signal_type}",
        confidence=0.9,
        strength=1.0,
        source_document_id=source_document_id,
        supporting_context=supporting_context,
        entity_type="test",
        entity_value=TEST_MARKER,
    )


def count_signals(project_id: str = None):
    """Count test signals (identified by entity_value marker)."""
    pid = project_id or TEST_PROJECT_ID
    with get_cursor() as cur:
        cur.execute(
            "SELECT count(*) as cnt FROM signals WHERE project_id = %s AND entity_value = %s",
            (pid, TEST_MARKER),
        )
        return cur.fetchone()["cnt"]


def get_signal(signal_id: str):
    """Fetch a signal by ID."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM signals WHERE id = %s", (signal_id,))
        return cur.fetchone()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestResults:
    """Collects and formats test results."""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0

    def record(self, name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        self.results.append((name, status, detail))
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def report(self) -> str:
        lines = [
            "=" * 72,
            "CC-2.6 SIGNAL DEDUPLICATION TEST RESULTS",
            f"Executed: {datetime.now().isoformat()}",
            f"Test project ID: {TEST_PROJECT_ID}",
            "=" * 72,
            "",
        ]
        for name, status, detail in self.results:
            lines.append(f"[{status}] {name}")
            if detail:
                for d in detail.split("\n"):
                    lines.append(f"       {d}")
            lines.append("")

        lines.append("-" * 72)
        lines.append(f"TOTAL: {self.passed + self.failed} tests | "
                      f"{self.passed} passed | {self.failed} failed")
        lines.append("=" * 72)
        return "\n".join(lines)


results = TestResults()


def test_1_exact_duplicate():
    """Same source_document_id + same signal_type within 1 hour → rejected."""
    cleanup_test_signals()

    src_id = make_doc_id()

    id1 = write_test_signal(signal_type="rfis_overdue", source_document_id=src_id)
    id2 = write_test_signal(signal_type="rfis_overdue", source_document_id=src_id)

    passed = (id1 is not None) and (id2 is None) and (count_signals() == 1)
    results.record(
        "1. Exact duplicate rejected",
        passed,
        f"First signal: {id1}\nSecond signal: {id2}\nSignal count: {count_signals()}"
    )
    return passed


def test_2_same_source_different_type():
    """Same source_document_id + different signal_type → both accepted."""
    cleanup_test_signals()

    src_id = make_doc_id()

    id1 = write_test_signal(signal_type="rfis_overdue", source_document_id=src_id)
    id2 = write_test_signal(signal_type="submittals_overdue", source_document_id=src_id)

    passed = (id1 is not None) and (id2 is not None) and (count_signals() == 2)
    results.record(
        "2. Same source, different signal type → both accepted",
        passed,
        f"Signal 1 (rfis_overdue): {id1}\nSignal 2 (submittals_overdue): {id2}\n"
        f"Signal count: {count_signals()}"
    )
    return passed


def test_3_different_source_same_type():
    """Different source_document_id + same signal_type → both accepted."""
    cleanup_test_signals()

    id1 = write_test_signal(signal_type="rfis_overdue", source_document_id=make_doc_id())
    id2 = write_test_signal(signal_type="rfis_overdue", source_document_id=make_doc_id())

    passed = (id1 is not None) and (id2 is not None) and (count_signals() == 2)
    results.record(
        "3. Different source, same signal type → both accepted",
        passed,
        f"Signal 1: {id1}\nSignal 2: {id2}\nSignal count: {count_signals()}"
    )
    return passed


def test_4_time_window_boundary():
    """Same source + type, but second signal arrives at 61+ minutes → accepted.

    We simulate this by backdating the first signal's created_at to 61 minutes ago.
    """
    cleanup_test_signals()

    src_id = make_doc_id()

    # Write first signal
    id1 = write_test_signal(signal_type="rfis_overdue", source_document_id=src_id)

    # Backdate the first signal to 61 minutes ago
    with get_cursor() as cur:
        cur.execute("""
            UPDATE signals SET created_at = NOW() - INTERVAL '61 minutes'
            WHERE id = %s
        """, (id1,))

    # Write second signal — should now be accepted (outside 1-hour window)
    id2 = write_test_signal(signal_type="rfis_overdue", source_document_id=src_id)

    passed = (id1 is not None) and (id2 is not None) and (count_signals() == 2)
    results.record(
        "4. Time window boundary (61 min) → second signal accepted",
        passed,
        f"Signal 1 (backdated 61min): {id1}\nSignal 2 (current): {id2}\n"
        f"Signal count: {count_signals()}"
    )
    return passed


def test_5_cross_project_isolation():
    """Same source + type + time window, different project_id → both accepted.

    NOTE: The current dedup implementation does NOT filter by project_id.
    The dedup query only checks source_document_id + signal_type + time window.
    This means cross-project signals with the same source_document_id WILL be
    deduped — this test documents the actual behavior.
    """
    cleanup_test_signals()

    src_id = make_doc_id()
    project_b = "bbc9c07a-5ab8-419c-b39a-87ff4d3cd828"  # Standard Project Template

    id1 = write_test_signal(
        signal_type="rfis_overdue",
        source_document_id=src_id,
        project_id=TEST_PROJECT_ID,
    )
    id2 = write_test_signal(
        signal_type="rfis_overdue",
        source_document_id=src_id,
        project_id=project_b,
    )

    count_a = count_signals(TEST_PROJECT_ID)
    count_b = count_signals(project_b)

    # Per spec, both should be accepted (cross-project isolation).
    # Actual behavior: dedup catches it because the query has no project_id filter.
    if id1 is not None and id2 is not None:
        passed = True
        detail = (f"Signal 1 (project A): {id1}\nSignal 2 (project B): {id2}\n"
                  f"Count A: {count_a}, Count B: {count_b}\n"
                  f"Cross-project isolation: WORKING")
    else:
        passed = False
        detail = (f"Signal 1 (project A): {id1}\nSignal 2 (project B): {id2}\n"
                  f"Count A: {count_a}, Count B: {count_b}\n"
                  f"BUG: Dedup query lacks project_id filter — cross-project signals "
                  f"with same source_document_id are incorrectly deduped.")

    results.record("5. Cross-project isolation", passed, detail)

    # Cleanup project B test signals only
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM signals WHERE project_id = %s AND entity_value = %s",
            (project_b, TEST_MARKER),
        )

    return passed


def test_6_path_a_vs_path_b_dedup():
    """Procore webhook signal, then document pipeline signal for same event → deduped.

    Both paths should produce a signal with the same source_document_id (the Procore
    entity ID). The dedup logic should catch the second one regardless of source_type,
    since dedup checks source_document_id + signal_type only.
    """
    cleanup_test_signals()

    # Same Procore entity triggers both paths
    procore_entity_id = make_doc_id()

    # Path A: webhook fires first
    id1 = SignalWriter.write(
        project_id=TEST_PROJECT_ID,
        source_type="procore_webhook",
        signal_type="rfis_overdue",
        signal_category="status_change",
        summary="RFI #42 is now 5 days overdue",
        confidence=0.95,
        source_document_id=procore_entity_id,
        supporting_context={"path": "webhook", "days_overdue": 5},
        entity_type="test",
        entity_value=TEST_MARKER,
    )

    # Path B: document pipeline processes the same entity
    id2 = SignalWriter.write(
        project_id=TEST_PROJECT_ID,
        source_type="document_pipeline",
        signal_type="rfis_overdue",
        signal_category="status_change",
        summary="RFI #42 is overdue per document analysis",
        confidence=0.85,
        source_document_id=procore_entity_id,
        supporting_context={"path": "document_pipeline", "analysis": "overdue"},
        entity_type="test",
        entity_value=TEST_MARKER,
    )

    # Verify: second signal should be deduped (returns existing ID with merged context)
    # OR returns None if no new context keys
    signal_count = count_signals()

    if signal_count == 1:
        # Check if context was merged
        signal = get_signal(id1)
        ctx = signal["supporting_context_json"]
        if isinstance(ctx, str):
            ctx = json.loads(ctx)
        has_merged = "path" in ctx and "analysis" in ctx
        passed = True
        detail = (f"Path A signal: {id1}\nPath B result: {id2}\n"
                  f"Signal count: {signal_count} (correctly deduped)\n"
                  f"Context merged: {has_merged}\n"
                  f"Final context keys: {list(ctx.keys()) if ctx else 'none'}")
    else:
        passed = False
        detail = (f"Path A signal: {id1}\nPath B signal: {id2}\n"
                  f"Signal count: {signal_count} (expected 1)")

    results.record(
        "6. Path A vs Path B dedup (webhook then document pipeline)",
        passed,
        detail,
    )
    return passed


def test_6b_context_merge():
    """Verify that dedup merges new context keys from the duplicate signal."""
    cleanup_test_signals()

    src_id = make_doc_id()

    id1 = write_test_signal(
        signal_type="rfis_overdue",
        source_document_id=src_id,
        supporting_context={"source": "webhook", "rfi_number": 42},
    )

    # Write duplicate with additional context
    id2 = write_test_signal(
        signal_type="rfis_overdue",
        source_document_id=src_id,
        supporting_context={"source": "webhook", "rfi_number": 42, "assignee": "Smith"},
    )

    signal = get_signal(id1)
    ctx = signal["supporting_context_json"]
    if isinstance(ctx, str):
        ctx = json.loads(ctx)

    has_assignee = ctx.get("assignee") == "Smith"
    passed = (id2 == id1) and has_assignee and (count_signals() == 1)

    results.record(
        "6b. Context merge on dedup (bonus test)",
        passed,
        f"Original signal: {id1}\nDedup returned: {id2}\n"
        f"Context after merge: {json.dumps(ctx, indent=2)}\n"
        f"Signal count: {count_signals()}"
    )
    return passed


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    """Execute all tests and produce formatted results."""
    print("Running CC-2.6 Signal Deduplication Tests...")
    print()

    test_1_exact_duplicate()
    test_2_same_source_different_type()
    test_3_different_source_same_type()
    test_4_time_window_boundary()
    test_5_cross_project_isolation()
    test_6_path_a_vs_path_b_dedup()
    test_6b_context_merge()

    # Final cleanup
    cleanup_test_signals()

    report = results.report()
    print(report)

    # Write results to file
    results_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "CC-2.6_Test_Results.md"
    )
    with open(results_path, "w") as f:
        f.write("# CC-2.6 Signal Deduplication — Test Results\n\n")
        f.write("```\n")
        f.write(report)
        f.write("\n```\n")

    print(f"\nResults written to: {results_path}")
    return results.failed == 0


# pytest compatibility
def test_exact_duplicate():
    cleanup_test_signals()
    assert test_1_exact_duplicate()

def test_same_source_different_type():
    cleanup_test_signals()
    assert test_2_same_source_different_type()

def test_different_source_same_type():
    cleanup_test_signals()
    assert test_3_different_source_same_type()

def test_time_window_boundary():
    cleanup_test_signals()
    assert test_4_time_window_boundary()

def test_cross_project_isolation():
    cleanup_test_signals()
    assert test_5_cross_project_isolation()

def test_path_a_vs_path_b_dedup():
    cleanup_test_signals()
    assert test_6_path_a_vs_path_b_dedup()

def test_context_merge():
    cleanup_test_signals()
    assert test_6b_context_merge()


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
