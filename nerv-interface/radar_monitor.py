"""SteelSync Radar Monitoring Pipeline — CC-5.4 + CC-5.5 + CC-5.6

Implements:
- Stage 1: Metadata filtering (no LLM) — matches signals against Radar monitoring_scope
- Stage 2: Keyword/entity matching (lightweight) — checks signal content against Radar targets
- Stage 3: Relevance judgment (LLM or algorithmic) — produces radar_activity entries
- Synthesis integration: builds Radar mandate for synthesis prompts
- Signal emission: creates radar_match signals from confirmed matches
"""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from steelsync_db import get_cursor, serialize_row, serialize_rows

logger = logging.getLogger("steelsync.radar")


# =============================================================================
# RADAR ITEM LOADER
# =============================================================================

def get_active_radar_items(project_id: str) -> List[Dict]:
    """Get all active Radar items for a project with their monitoring scope."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, project_id, title, description, priority, status,
                   monitoring_scope_json, primary_target, created_at
            FROM radar_items
            WHERE project_id = %s AND status = 'active'
            ORDER BY priority ASC, created_at DESC
        """, (project_id,))
        return serialize_rows(cur.fetchall())


def get_radar_recent_activity(radar_item_id: str, limit: int = 3) -> List[Dict]:
    """Get recent activity for a Radar item."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, activity_type, content, severity, created_at
            FROM radar_activity
            WHERE radar_item_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (radar_item_id, limit))
        return serialize_rows(cur.fetchall())


# =============================================================================
# CC-5.4: PASSIVE MONITORING PIPELINE
# =============================================================================

def _parse_scope(radar_item: Dict) -> Dict:
    """Parse the monitoring_scope_json into a usable structure."""
    scope = radar_item.get("monitoring_scope_json") or {}
    if isinstance(scope, str):
        try:
            scope = json.loads(scope)
        except (json.JSONDecodeError, TypeError):
            scope = {}
    return scope


def stage1_metadata_filter(signal: Dict, radar_item: Dict) -> bool:
    """Stage 1: Fast metadata check. No LLM.

    Checks if the signal's project matches the Radar item's project,
    and if the signal's entity/type overlaps with the monitoring scope.
    Returns True if the signal PASSES the filter (potential match).
    """
    # Must be same project
    if str(signal.get("project_id", "")) != str(radar_item.get("project_id", "")):
        return False

    scope = _parse_scope(radar_item)
    if not scope:
        # No scope defined — pass everything through
        return True

    # Check entity type match
    watched_entities = scope.get("entity_types", [])
    if watched_entities:
        sig_entity = signal.get("entity_type", "")
        if sig_entity and sig_entity not in watched_entities:
            return False

    # Check trade match
    watched_trades = [t.lower() for t in scope.get("trades", [])]
    if watched_trades:
        sig_context = signal.get("supporting_context_json") or {}
        if isinstance(sig_context, str):
            try:
                sig_context = json.loads(sig_context)
            except (json.JSONDecodeError, TypeError):
                sig_context = {}
        sig_trade = str(sig_context.get("trade", "")).lower()
        sig_spec = str(sig_context.get("spec_section", "")).lower()
        # If trade info exists on the signal and doesn't match, filter out
        if sig_trade and sig_trade not in watched_trades:
            if not any(t in sig_trade for t in watched_trades):
                return False

    # Check signal category match
    watched_categories = scope.get("signal_categories", [])
    if watched_categories:
        sig_cat = signal.get("signal_category", "")
        if sig_cat and sig_cat not in watched_categories:
            return False

    return True


def stage2_keyword_match(signal: Dict, radar_item: Dict) -> float:
    """Stage 2: Keyword and entity matching. No LLM.

    Compares signal content against the Radar item's primary_target,
    title, description, and monitoring scope keywords.
    Returns a relevance score 0.0-1.0.
    """
    score = 0.0
    matches = 0
    checks = 0

    # Build keyword set from Radar item
    keywords = set()
    primary_target = (radar_item.get("primary_target") or "").lower()
    title = (radar_item.get("title") or "").lower()
    description = (radar_item.get("description") or "").lower()

    # Extract meaningful words (3+ chars)
    for text in [primary_target, title]:
        words = re.findall(r'\b[a-z]{3,}\b', text)
        keywords.update(words)

    scope = _parse_scope(radar_item)
    for kw in scope.get("keywords", []):
        keywords.add(kw.lower())

    # Remove common stop words
    stop_words = {"the", "and", "for", "are", "but", "not", "this", "that",
                  "with", "from", "have", "has", "was", "were", "been",
                  "will", "would", "could", "should", "may", "might",
                  "track", "monitor", "signs", "potential", "impacts"}
    keywords -= stop_words

    if not keywords:
        return 0.5  # No keywords to match — neutral score

    # Build signal text corpus
    sig_text = " ".join([
        (signal.get("summary") or ""),
        (signal.get("signal_type") or "").replace("_", " "),
        (signal.get("entity_type") or ""),
        (signal.get("entity_value") or ""),
        str(signal.get("supporting_context_json") or ""),
    ]).lower()

    # Check keyword matches — use partial matching for compound terms
    for kw in keywords:
        checks += 1
        if kw in sig_text:
            matches += 1
        elif len(kw) >= 4 and any(kw[:4] in word for word in sig_text.split()):
            # Stem-like partial match (e.g., "overdue" matches "overdu")
            matches += 0.5

    if checks == 0:
        return 0.5

    score = matches / checks

    # Boost if entity_value directly mentioned in target
    entity_val = (signal.get("entity_value") or "").lower()
    if entity_val and (entity_val in primary_target or entity_val in title):
        score = min(1.0, score + 0.3)

    return round(score, 2)


def stage3_relevance_judgment(
    signal: Dict,
    radar_item: Dict,
    keyword_score: float,
) -> Optional[Dict]:
    """Stage 3: Relevance judgment. Algorithmic for now, LLM when API key available.

    Returns a match result dict or None if not relevant.
    """
    # For local mode: use heuristic based on keyword score + signal strength
    threshold = 0.2  # Conservative — let more through for Radar
    if keyword_score < threshold:
        return None

    # Determine severity based on signal strength and radar priority
    priority_multiplier = {"critical": 1.5, "high": 1.2, "watch": 0.8}
    pm = priority_multiplier.get(radar_item.get("priority", "watch"), 1.0)
    effective_score = keyword_score * pm

    if effective_score < 0.3:
        return None

    severity = "low"
    if effective_score >= 0.7:
        severity = "high"
    elif effective_score >= 0.5:
        severity = "medium"

    return {
        "relevant": True,
        "relevance_score": round(effective_score, 2),
        "relevance_summary": (
            f"Signal '{signal.get('signal_type', 'unknown')}' "
            f"({signal.get('entity_type', '')}:{signal.get('entity_value', '')}) "
            f"matches Radar item '{radar_item.get('title', '')}' "
            f"with {keyword_score:.0%} keyword overlap."
        ),
        "severity": severity,
    }


# =============================================================================
# CC-5.6: SIGNAL EMISSION & ACTIVITY LOGGING
# =============================================================================

def emit_radar_match(
    project_id: str,
    signal: Dict,
    radar_item: Dict,
    match_result: Dict,
) -> Optional[str]:
    """Emit a radar_match signal and create radar_activity entry.

    Returns the new signal ID or None.
    """
    from signal_generation import SignalWriter

    # Create radar_match signal
    signal_id = SignalWriter.write(
        project_id=project_id,
        source_type="procore_webhook",
        signal_type="radar_match",
        signal_category="radar_match",
        summary=match_result["relevance_summary"],
        confidence=match_result["relevance_score"],
        strength=0.9,
        decay_profile="slow_7d",
        entity_type=signal.get("entity_type"),
        entity_value=signal.get("entity_value"),
        supporting_context={
            "radar_item_id": str(radar_item["id"]),
            "radar_title": radar_item.get("title"),
            "source_signal_id": str(signal["id"]),
            "source_signal_type": signal.get("signal_type"),
            "relevance_score": match_result["relevance_score"],
        },
    )

    # Create radar_activity entry
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO radar_activity
                (id, radar_item_id, activity_type, content, severity,
                 source_signal_id)
            VALUES (%s, %s, 'system_detection', %s, %s::intelligence_severity, %s)
        """, (
            str(uuid4()),
            str(radar_item["id"]),
            match_result["relevance_summary"],
            match_result["severity"],
            str(signal["id"]),
        ))

        # Link document if applicable
        if signal.get("source_document_id"):
            cur.execute("""
                INSERT INTO radar_document_links
                    (id, radar_item_id, document_type, document_id,
                     relevance_score, linked_by)
                VALUES (%s, %s, %s, %s, %s, 'system')
            """, (
                str(uuid4()),
                str(radar_item["id"]),
                signal.get("entity_type", "unknown"),
                signal["source_document_id"],
                match_result["relevance_score"],
            ))

    logger.info(
        f"Radar match: signal {signal['id']} → radar {radar_item['id']} "
        f"(score={match_result['relevance_score']}, severity={match_result['severity']})"
    )
    return signal_id


def evaluate_signals_against_radar(
    project_id: str,
    signals: List[Dict],
) -> Dict[str, int]:
    """Run the full 3-stage passive monitoring pipeline.

    Evaluates a batch of signals against all active Radar items for the project.
    Returns counts: {stage1_passed, stage2_passed, stage3_matched, signals_emitted}
    """
    radar_items = get_active_radar_items(project_id)
    if not radar_items:
        return {"radar_items": 0, "signals_checked": 0,
                "stage1_passed": 0, "stage2_passed": 0,
                "stage3_matched": 0, "signals_emitted": 0}

    stats = {
        "radar_items": len(radar_items),
        "signals_checked": len(signals),
        "stage1_passed": 0,
        "stage2_passed": 0,
        "stage3_matched": 0,
        "signals_emitted": 0,
    }

    # Track matches per radar item to avoid flood (max 3 per item per run)
    # Also deduplicate by signal_type per radar item
    matches_per_item: Dict[str, int] = defaultdict(int)
    type_matched_per_item: Dict[str, set] = defaultdict(set)
    MAX_MATCHES_PER_ITEM = 3

    for signal in signals:
        for radar_item in radar_items:
            rid = str(radar_item["id"])

            # Skip if already at max matches for this item
            if matches_per_item[rid] >= MAX_MATCHES_PER_ITEM:
                continue

            # Skip if this signal_type already matched this radar item
            sig_type = signal.get("signal_type", "")
            if sig_type in type_matched_per_item[rid]:
                continue

            # Stage 1: Metadata filter
            if not stage1_metadata_filter(signal, radar_item):
                continue
            stats["stage1_passed"] += 1

            # Stage 2: Keyword match
            score = stage2_keyword_match(signal, radar_item)
            if score < 0.2:
                continue
            stats["stage2_passed"] += 1

            # Stage 3: Relevance judgment
            match_result = stage3_relevance_judgment(signal, radar_item, score)
            if not match_result:
                continue
            stats["stage3_matched"] += 1

            # Emit signal + activity
            sid = emit_radar_match(project_id, signal, radar_item, match_result)
            if sid:
                stats["signals_emitted"] += 1
                matches_per_item[rid] += 1
                type_matched_per_item[rid].add(sig_type)

    logger.info(f"Radar passive monitoring for {project_id}: {stats}")
    return stats


# =============================================================================
# CC-5.5: SYNTHESIS CYCLE RADAR MANDATE
# =============================================================================

def build_radar_mandate(project_id: str) -> Optional[str]:
    """Build the Radar monitoring mandate section for the synthesis prompt.

    Returns the mandate text, or None if no active Radar items exist.
    """
    radar_items = get_active_radar_items(project_id)
    if not radar_items:
        return None

    sections = []
    sections.append("RADAR MONITORING MANDATE")
    sections.append("=" * 40)
    sections.append(
        "In addition to your core analytical mandate, evaluate whether any of "
        "today's signals or intelligence items are relevant to the following "
        "active Radar tracking items. For each relevant match, include a "
        "radar_update in your output."
    )
    sections.append("")

    for i, item in enumerate(radar_items, 1):
        priority_tag = f"[{item['priority'].upper()}]" if item.get("priority") else ""
        if item.get("priority") == "critical":
            priority_tag += " *** PAY SPECIAL ATTENTION ***"

        sections.append(f"Radar Item {i}: {item['title']} {priority_tag}")
        sections.append(f"  ID: {item['id']}")
        if item.get("description"):
            sections.append(f"  Description: {item['description']}")
        if item.get("primary_target"):
            sections.append(f"  Tracking: {item['primary_target']}")

        scope = _parse_scope(item)
        if scope:
            if scope.get("trades"):
                sections.append(f"  Trades: {', '.join(scope['trades'])}")
            if scope.get("keywords"):
                sections.append(f"  Keywords: {', '.join(scope['keywords'])}")
            if scope.get("entity_types"):
                sections.append(f"  Entity types: {', '.join(scope['entity_types'])}")

        # Recent activity
        activity = get_radar_recent_activity(str(item["id"]), limit=3)
        if activity:
            sections.append("  Recent activity:")
            for act in activity:
                sections.append(
                    f"    - [{act.get('severity', 'info')}] {act.get('content', '')[:100]} "
                    f"({act.get('created_at', '')})"
                )
        sections.append("")

    sections.append("RADAR OUTPUT SCHEMA:")
    sections.append('Add a "radar_updates" array to your output:')
    sections.append(json.dumps([{
        "radar_item_id": "UUID",
        "relevance_summary": "Why this is relevant",
        "severity": "low|medium|high",
        "recommended_status_change": "null or escalated|resolved",
        "new_activity_entry": "Activity log text",
    }], indent=2))

    return "\n".join(sections)


def process_radar_updates(
    radar_updates: List[Dict],
    cycle_id: str,
) -> int:
    """Process radar_updates from synthesis output.

    Creates radar_activity entries and updates Radar item status if recommended.
    Returns number of updates processed.
    """
    count = 0
    with get_cursor() as cur:
        for update in radar_updates:
            radar_item_id = update.get("radar_item_id")
            if not radar_item_id:
                continue

            # Verify radar item exists
            cur.execute("SELECT id, status FROM radar_items WHERE id = %s", (radar_item_id,))
            item = cur.fetchone()
            if not item:
                logger.warning(f"Radar update references unknown item: {radar_item_id}")
                continue

            # Create activity entry
            cur.execute("""
                INSERT INTO radar_activity
                    (id, radar_item_id, activity_type, content, severity)
                VALUES (%s, %s, 'system_detection', %s, %s::intelligence_severity)
            """, (
                str(uuid4()),
                radar_item_id,
                update.get("new_activity_entry") or update.get("relevance_summary", ""),
                update.get("severity", "low"),
            ))

            # Update status if recommended
            new_status = update.get("recommended_status_change")
            if new_status == "resolved":
                cur.execute("""
                    UPDATE radar_items SET
                        status = 'resolved'::radar_status,
                        resolved_at = NOW()
                    WHERE id = %s AND status = 'active'
                """, (radar_item_id,))
            elif new_status == "escalated":
                cur.execute("""
                    UPDATE radar_items SET priority = 'critical'::radar_priority
                    WHERE id = %s AND priority != 'critical'
                """, (radar_item_id,))

            count += 1
            logger.info(f"Processed Radar update for item {radar_item_id}")

    return count
