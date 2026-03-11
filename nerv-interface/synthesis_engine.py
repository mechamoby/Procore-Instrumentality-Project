"""SteelSync Synthesis Engine — CC-3.1 + CC-3.2 + CC-3.3

The analytical brain of SteelSync. Consumes signals, combines them with project
state, and produces structured intelligence items via Claude Opus.

Implements:
- SynthesisEngine: orchestrates the synthesis cycle
- Prompt templates (Morning Briefing, Midday Checkpoint, EOD, Escalation)
- ItemManager: CRUD for intelligence items with evidence chains
- Project state snapshot builder
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional
from uuid import uuid4

from steelsync_db import get_cursor, serialize_row, serialize_rows

logger = logging.getLogger("steelsync.synthesis")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SYNTHESIS_MODEL = os.environ.get("SYNTHESIS_MODEL", "claude-sonnet-4-20250514")


# =============================================================================
# PROMPT TEMPLATES (CC-3.2)
# =============================================================================

SYSTEM_PROMPT_BASE = """You are a Senior Project Manager intelligence analyst for a construction general contractor. You analyze project data signals and produce actionable intelligence items.

ANALYTICAL MANDATE:
1. What changed since the last cycle that matters operationally
2. Convergences: multiple signals pointing to the same concern
3. Contradictions: signals that conflict with each other or with stated project status
4. Emerging signals: early-stage patterns that could become significant
5. Item status updates: which existing intelligence items should be reinforced, downgraded, or resolved

ANTI-NOISE RULES:
- Do NOT create intelligence items for routine status updates that require no action
- Do NOT create items that merely restate the data without adding analytical insight
- Every item must have an operational "so what" — what should the PM do about this?
- If confidence is below 0.5, note it as an emerging signal, not an active item
- Maximum {{max_items}} new items per cycle. Quality over quantity.

STATE YOUR ASSUMPTIONS:
- If you infer something not directly stated in the data, state your assumption explicitly
- If you lack data to make a determination, say so. Do not guess.

OUTPUT FORMAT:
Return ONLY valid JSON matching this schema:
{
    "cycle_summary": "2-3 sentence summary of this cycle's findings",
    "overall_health": "green|yellow|red",
    "intelligence_items": [
        {
            "action": "create|update|reinforce|downgrade|resolve|merge",
            "existing_item_id": "UUID (required for update/reinforce/downgrade/resolve/merge)",
            "merge_source_ids": ["UUIDs (only for merge action)"],
            "item_type": "convergence|contradiction|pattern_match|decay_detection|cross_project_correlation|emerging_risk|watch_item",
            "title": "Short title (max 100 chars)",
            "summary": "Detailed finding with operational context",
            "severity": "critical|high|medium|low",
            "confidence": 0.0-1.0,
            "recommended_attention_level": "immediate|today|tomorrow_morning|this_week|monitor",
            "source_signal_ids": ["UUIDs of signals supporting this item"],
            "evidence_weights": ["primary|supporting|circumstantial (parallel to source_signal_ids)"]
        }
    ],
    "working_memory_actions": [
        {
            "action": "downgrade|resolve|archive",
            "item_id": "UUID",
            "reason": "Why this item should change status"
        }
    ]
}"""

TEMPLATE_A_MORNING = """{{system_base}}

CYCLE TYPE: Morning Briefing
TIME CONTEXT: Start of business day. The PM needs to know what happened overnight and what to focus on today.
MAX NEW ITEMS: 5

Focus on: What's different from yesterday? What needs attention today?"""

TEMPLATE_B_MIDDAY = """{{system_base}}

CYCLE TYPE: Midday Checkpoint
TIME CONTEXT: Midday update. The PM has been working all morning. Focus on DELTA from morning briefing only.
MAX NEW ITEMS: 3

PREVIOUS MORNING SUMMARY:
{{morning_summary}}

Focus on: What changed since morning? Any new developments that alter this morning's assessment?
Do NOT re-analyze items already covered in the morning briefing unless new data invalidates them."""

TEMPLATE_C_EOD = """{{system_base}}

CYCLE TYPE: End-of-Day Consolidation
TIME CONTEXT: End of business day. Full-day view. Consolidate and clean up for tomorrow.
MAX NEW ITEMS: 7 (including merged items)

MORNING SUMMARY: {{morning_summary}}
MIDDAY SUMMARY: {{midday_summary}}

Focus on:
- Consolidate related items (use merge action)
- Evaluate EVERY active item — does it persist, downgrade, or resolve?
- Produce a clean state for tomorrow morning
- Include "tomorrow_watch_list" (max 3 items) in working_memory_actions

Additional output field:
"tomorrow_watch_list": ["item 1 to watch", "item 2 to watch", "item 3 to watch"]"""

TEMPLATE_D_ESCALATION = """{{system_base}}

CYCLE TYPE: Escalation Review (on-demand deep-dive)
TIME CONTEXT: A specific intelligence item has been flagged for escalation. Provide deep analysis.

ESCALATION ITEM:
{{escalation_item}}

RELATED ITEMS:
{{related_items}}

SUPPORTING SIGNALS:
{{supporting_signals}}

CROSS-PROJECT CONTEXT:
{{cross_project_context}}

Provide an in-depth assessment including:
- Is the escalation justified? (confidence + evidence quality evaluation)
- What is the actual operational impact?
- What specific actions should the PM take?
- What assumptions are you making?

Output schema:
{
    "escalation_assessment": {
        "justified": true/false,
        "confidence": 0.0-1.0,
        "evidence_quality": "strong|moderate|weak",
        "impact_summary": "string",
        "recommended_actions": ["action 1", "action 2"],
        "assumptions": ["assumption 1"]
    },
    "updated_intelligence_item": { ... same schema as above with action: "update" ... }
}"""


# =============================================================================
# PROJECT STATE SNAPSHOT BUILDER
# =============================================================================

def build_project_snapshot(project_id: str) -> Dict:
    """Build a concise project state snapshot for synthesis context.

    Target: 800-1200 tokens worth of content.
    """
    with get_cursor() as cur:
        # Project basics
        cur.execute("""
            SELECT name, number, status, project_type, start_date,
                   estimated_completion, contract_value
            FROM projects WHERE id = %s
        """, (project_id,))
        project = cur.fetchone()
        if not project:
            return {"error": "Project not found"}

        snapshot = {
            "project": serialize_row(project),
        }

        # Open RFI summary
        cur.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN due_date < CURRENT_DATE AND status NOT IN ('closed','answered','void') THEN 1 ELSE 0 END) as overdue,
                   SUM(CASE WHEN status NOT IN ('closed','answered','void') THEN 1 ELSE 0 END) as open
            FROM rfis WHERE project_id = %s AND is_deleted = FALSE
        """, (project_id,))
        snapshot["rfis"] = serialize_row(cur.fetchone())

        # Open submittal summary
        cur.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN required_date < CURRENT_DATE AND status NOT IN ('approved','approved_as_noted','closed','void') THEN 1 ELSE 0 END) as overdue,
                   SUM(CASE WHEN status NOT IN ('approved','approved_as_noted','closed','void') THEN 1 ELSE 0 END) as open,
                   SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
            FROM submittals WHERE project_id = %s AND is_deleted = FALSE
        """, (project_id,))
        snapshot["submittals"] = serialize_row(cur.fetchone())

        # Upcoming milestones (next 30 days)
        cur.execute("""
            SELECT sa.name, sa.finish_date, sa.percent_complete, sa.is_critical
            FROM schedule_activities sa
            JOIN schedules sch ON sch.id = sa.schedule_id
            WHERE sch.project_id = %s AND sch.is_current = TRUE AND sch.is_deleted = FALSE
              AND sa.is_milestone = TRUE AND sa.actual_finish IS NULL
              AND sa.finish_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 30
            ORDER BY sa.finish_date
            LIMIT 5
        """, (project_id,))
        snapshot["upcoming_milestones"] = serialize_rows(cur.fetchall())

        # Pending change orders
        cur.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total_amount
            FROM change_orders
            WHERE project_id = %s AND is_deleted = FALSE AND status = 'pending'
        """, (project_id,))
        snapshot["pending_change_orders"] = serialize_row(cur.fetchone())

        # Recent daily log status
        cur.execute("""
            SELECT report_date, total_workers,
                   CASE WHEN delays IS NOT NULL AND delays != '' THEN TRUE ELSE FALSE END as had_delays
            FROM daily_reports
            WHERE project_id = %s AND is_deleted = FALSE
            ORDER BY report_date DESC LIMIT 3
        """, (project_id,))
        snapshot["recent_daily_logs"] = serialize_rows(cur.fetchall())

        return snapshot


# =============================================================================
# ITEM MANAGER (CC-3.3)
# =============================================================================

class ItemManager:
    """Manages intelligence item lifecycle: create, update, reinforce,
    downgrade, resolve, merge, archive."""

    @staticmethod
    def create_item(
        project_id: str,
        synthesis_output: Dict,
        synthesis_cycle_id: str,
    ) -> Optional[str]:
        """Create a new intelligence item from synthesis output."""
        item_id = str(uuid4())

        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO intelligence_items (
                    id, project_id, item_type, title, summary,
                    severity, confidence, status,
                    synthesis_cycle_id, recommended_attention_level,
                    source_evidence_count
                ) VALUES (
                    %s, %s, %s::intelligence_item_type, %s, %s,
                    %s::intelligence_severity, %s, 'new'::intelligence_status,
                    %s, %s::attention_level,
                    %s
                )
            """, (
                item_id, project_id,
                synthesis_output.get("item_type", "watch_item"),
                synthesis_output.get("title", "Untitled"),
                synthesis_output.get("summary", ""),
                synthesis_output.get("severity", "medium"),
                synthesis_output.get("confidence", 0.5),
                synthesis_cycle_id,
                synthesis_output.get("recommended_attention_level", "this_week"),
                len(synthesis_output.get("source_signal_ids", [])),
            ))

            # Write evidence chain
            signal_ids = synthesis_output.get("source_signal_ids", [])
            weights = synthesis_output.get("evidence_weights", [])
            for i, sig_id in enumerate(signal_ids):
                weight = weights[i] if i < len(weights) else "supporting"
                try:
                    cur.execute("""
                        INSERT INTO intelligence_item_evidence
                            (id, intelligence_item_id, signal_id, evidence_weight_level)
                        VALUES (%s, %s, %s, %s::evidence_weight)
                    """, (str(uuid4()), item_id, sig_id, weight))
                except Exception as e:
                    logger.warning(f"Failed to link signal {sig_id} to item {item_id}: {e}")

        logger.info(f"Created intelligence item: {item_id} [{synthesis_output.get('title')}]")
        return item_id

    @staticmethod
    def get_item(item_id: str) -> Optional[Dict]:
        """Fetch a single intelligence item by ID."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT id, project_id, item_type, title, summary,
                       severity, confidence, status,
                       recommended_attention_level, source_evidence_count,
                       synthesis_cycle_id, created_at, updated_at
                FROM intelligence_items WHERE id = %s
            """, (item_id,))
            row = cur.fetchone()
            return serialize_row(row) if row else None

    @staticmethod
    def update_item(
        item_id: str,
        synthesis_output: Dict,
        synthesis_cycle_id: str,
    ) -> bool:
        """Update an existing intelligence item."""
        with get_cursor() as cur:
            cur.execute("SELECT id, project_id FROM intelligence_items WHERE id = %s", (item_id,))
            existing = cur.fetchone()
            if not existing:
                logger.warning(f"Update: item {item_id} not found, skipping")
                return False

            cur.execute("""
                UPDATE intelligence_items SET
                    title = COALESCE(%s, title),
                    summary = COALESCE(%s, summary),
                    severity = COALESCE(%s::intelligence_severity, severity),
                    confidence = COALESCE(%s, confidence),
                    recommended_attention_level = COALESCE(%s::attention_level, recommended_attention_level),
                    synthesis_cycle_id = %s,
                    status = CASE WHEN status = 'new' THEN 'active'::intelligence_status ELSE status END
                WHERE id = %s
            """, (
                synthesis_output.get("title"),
                synthesis_output.get("summary"),
                synthesis_output.get("severity"),
                synthesis_output.get("confidence"),
                synthesis_output.get("recommended_attention_level"),
                synthesis_cycle_id,
                item_id,
            ))

            # Add new evidence
            for sig_id in synthesis_output.get("source_signal_ids", []):
                try:
                    cur.execute("""
                        INSERT INTO intelligence_item_evidence
                            (id, intelligence_item_id, signal_id, evidence_weight_level)
                        VALUES (%s, %s, %s, 'supporting'::evidence_weight)
                    """, (str(uuid4()), item_id, sig_id))
                except Exception:
                    pass

            # Update evidence count
            cur.execute("""
                UPDATE intelligence_items SET source_evidence_count = (
                    SELECT COUNT(*) FROM intelligence_item_evidence WHERE intelligence_item_id = %s
                ) WHERE id = %s
            """, (item_id, item_id))

        logger.info(f"Updated intelligence item: {item_id}")
        return True

    @staticmethod
    def reinforce_item(item_id: str, signal_ids: List[str]) -> bool:
        """Reinforce an existing item with new evidence."""
        with get_cursor() as cur:
            cur.execute("SELECT id FROM intelligence_items WHERE id = %s", (item_id,))
            if not cur.fetchone():
                logger.warning(f"Reinforce: item {item_id} not found")
                return False

            cur.execute("""
                UPDATE intelligence_items SET
                    last_reinforced_at = NOW(),
                    status = CASE WHEN status = 'new' THEN 'active'::intelligence_status ELSE status END
                WHERE id = %s
            """, (item_id,))

            for sig_id in signal_ids:
                try:
                    cur.execute("""
                        INSERT INTO intelligence_item_evidence
                            (id, intelligence_item_id, signal_id, evidence_weight_level)
                        VALUES (%s, %s, %s, 'supporting'::evidence_weight)
                    """, (str(uuid4()), item_id, sig_id))
                except Exception:
                    pass

            cur.execute("""
                UPDATE intelligence_items SET source_evidence_count = (
                    SELECT COUNT(*) FROM intelligence_item_evidence WHERE intelligence_item_id = %s
                ) WHERE id = %s
            """, (item_id, item_id))

        logger.info(f"Reinforced intelligence item: {item_id}")
        return True

    @staticmethod
    def downgrade_item(item_id: str, reason: str) -> bool:
        """Downgrade item from active to watch."""
        with get_cursor() as cur:
            cur.execute("""
                UPDATE intelligence_items SET
                    status = 'watch'::intelligence_status
                WHERE id = %s AND status IN ('new', 'active')
            """, (item_id,))
            affected = cur.rowcount
        if affected:
            logger.info(f"Downgraded item {item_id}: {reason}")
        return affected > 0

    @staticmethod
    def resolve_item(item_id: str, reason: str) -> bool:
        """Resolve an intelligence item."""
        with get_cursor() as cur:
            cur.execute("""
                UPDATE intelligence_items SET
                    status = 'resolved'::intelligence_status,
                    resolved_at = NOW()
                WHERE id = %s AND status NOT IN ('resolved', 'archived')
            """, (item_id,))
            affected = cur.rowcount
        if affected:
            logger.info(f"Resolved item {item_id}: {reason}")
        return affected > 0

    @staticmethod
    def archive_item(item_id: str, reason: str) -> bool:
        """Archive an intelligence item."""
        with get_cursor() as cur:
            cur.execute("""
                UPDATE intelligence_items SET
                    status = 'archived'::intelligence_status,
                    archived_at = NOW()
                WHERE id = %s AND status != 'archived'
            """, (item_id,))
            affected = cur.rowcount
        if affected:
            logger.info(f"Archived item {item_id}: {reason}")
        return affected > 0

    @staticmethod
    def merge_items(surviving_id: str, source_ids: List[str], synthesis_output: Dict, cycle_id: str) -> bool:
        """Merge source items into surviving item. Archive sources."""
        with get_cursor() as cur:
            # Verify surviving item exists
            cur.execute("SELECT id FROM intelligence_items WHERE id = %s", (surviving_id,))
            if not cur.fetchone():
                logger.warning(f"Merge: surviving item {surviving_id} not found")
                return False

            # Transfer evidence chains
            for source_id in source_ids:
                cur.execute("""
                    UPDATE intelligence_item_evidence
                    SET intelligence_item_id = %s
                    WHERE intelligence_item_id = %s
                """, (surviving_id, source_id))

                # Archive the source item
                cur.execute("""
                    UPDATE intelligence_items SET
                        status = 'archived'::intelligence_status,
                        archived_at = NOW()
                    WHERE id = %s
                """, (source_id,))

            # Update surviving item
            if synthesis_output.get("summary"):
                cur.execute("""
                    UPDATE intelligence_items SET
                        summary = %s,
                        synthesis_cycle_id = %s,
                        source_evidence_count = (
                            SELECT COUNT(*) FROM intelligence_item_evidence WHERE intelligence_item_id = %s
                        )
                    WHERE id = %s
                """, (synthesis_output["summary"], cycle_id, surviving_id, surviving_id))

        logger.info(f"Merged items {source_ids} into {surviving_id}")
        return True


# =============================================================================
# SYNTHESIS ENGINE (CC-3.1)
# =============================================================================

class SynthesisEngine:
    """Orchestrates the periodic intelligence synthesis cycle."""

    @staticmethod
    def _get_template(cycle_type: str, **kwargs) -> str:
        """Get the appropriate prompt template for the cycle type."""
        base = SYSTEM_PROMPT_BASE.replace("{{max_items}}", {
            "morning_briefing": "5",
            "midday_checkpoint": "3",
            "end_of_day": "7",
            "escalation_review": "1",
        }.get(cycle_type, "5"))

        templates = {
            "morning_briefing": TEMPLATE_A_MORNING,
            "midday_checkpoint": TEMPLATE_B_MIDDAY,
            "end_of_day": TEMPLATE_C_EOD,
            "escalation_review": TEMPLATE_D_ESCALATION,
        }

        template = templates.get(cycle_type, TEMPLATE_A_MORNING)
        template = template.replace("{{system_base}}", base)

        for key, value in kwargs.items():
            template = template.replace("{{" + key + "}}", str(value))

        return template

    @staticmethod
    def _get_signals_for_cycle(project_id: str, since_hours: int = 24) -> List[Dict]:
        """Get new signals since last cycle.

        Uses a type-diverse query: up to 10 signals per signal_type,
        ordered by weight within each type, capped at 100 total.
        """
        with get_cursor() as cur:
            cur.execute("""
                WITH ranked AS (
                    SELECT id, signal_type, signal_category, summary, confidence,
                           strength, effective_weight, entity_type, entity_value,
                           supporting_context_json, created_at,
                           ROW_NUMBER() OVER (PARTITION BY signal_type ORDER BY effective_weight DESC) as rn
                    FROM signals
                    WHERE project_id = %s
                      AND archived_at IS NULL
                      AND created_at > NOW() - INTERVAL '%s hours'
                )
                SELECT id, signal_type, signal_category, summary, confidence,
                       strength, effective_weight, entity_type, entity_value,
                       supporting_context_json, created_at
                FROM ranked
                WHERE rn <= 10
                ORDER BY effective_weight DESC
                LIMIT 100
            """, (project_id, since_hours))
            return serialize_rows(cur.fetchall())

    @staticmethod
    def _get_active_intelligence_items(project_id: str) -> List[Dict]:
        """Get active and watch intelligence items."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT id, item_type, title, summary, severity, confidence,
                       status, first_created_at, last_updated_at, last_reinforced_at,
                       source_evidence_count, recommended_attention_level
                FROM intelligence_items
                WHERE project_id = %s AND status IN ('new', 'active', 'watch')
                ORDER BY severity DESC, last_updated_at DESC
            """, (project_id,))
            return serialize_rows(cur.fetchall())

    @staticmethod
    def _get_pending_reinforcement_candidates(project_id: str) -> List[Dict]:
        """Get pending reinforcement candidates for synthesis evaluation."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT rc.id, rc.target_signal_id, rc.source_signal_id,
                       rc.reason, rc.confidence,
                       ts.signal_type as target_type, ts.summary as target_summary,
                       ts.entity_type as target_entity_type, ts.entity_value as target_entity_value,
                       ss.signal_type as source_type, ss.summary as source_summary
                FROM reinforcement_candidates rc
                JOIN signals ts ON ts.id = rc.target_signal_id
                JOIN signals ss ON ss.id = rc.source_signal_id
                WHERE ts.project_id = %s
                  AND rc.status = 'pending'
                ORDER BY rc.confidence DESC
                LIMIT 20
            """, (project_id,))
            return serialize_rows(cur.fetchall())

    @staticmethod
    def _promote_reinforcement_candidate(candidate_id: str) -> bool:
        """Promote a reinforcement candidate: update target signal and linked items."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT target_signal_id FROM reinforcement_candidates
                WHERE id = %s AND status = 'pending'
            """, (candidate_id,))
            row = cur.fetchone()
            if not row:
                return False

            target_signal_id = str(row["target_signal_id"])

            cur.execute("""
                UPDATE reinforcement_candidates SET
                    status = 'promoted'::reinforcement_status,
                    evaluated_at = NOW()
                WHERE id = %s
            """, (candidate_id,))

            cur.execute("""
                UPDATE signals SET last_reinforced_at = NOW()
                WHERE id = %s
            """, (target_signal_id,))

            cur.execute("""
                UPDATE intelligence_items SET
                    last_reinforced_at = NOW(),
                    source_evidence_count = source_evidence_count + 1
                WHERE id IN (
                    SELECT intelligence_item_id FROM intelligence_item_evidence
                    WHERE signal_id = %s
                )
            """, (target_signal_id,))

        return True

    @staticmethod
    def _discard_reinforcement_candidate(candidate_id: str) -> bool:
        """Discard a reinforcement candidate."""
        with get_cursor() as cur:
            cur.execute("""
                UPDATE reinforcement_candidates SET
                    status = 'discarded'::reinforcement_status,
                    evaluated_at = NOW()
                WHERE id = %s AND status = 'pending'
            """, (candidate_id,))
            return cur.rowcount > 0

    @staticmethod
    def _get_dismissed_feedback(project_id: str) -> List[Dict]:
        """Get recently dismissed items with feedback for synthesis context."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT ii.title, ii.item_type, f.dismiss_reason, f.dismiss_comment
                FROM intelligence_item_feedback f
                JOIN intelligence_items ii ON ii.id = f.intelligence_item_id
                WHERE ii.project_id = %s
                  AND f.feedback_type = 'dismissed'
                  AND f.created_at > NOW() - INTERVAL '7 days'
                ORDER BY f.created_at DESC
                LIMIT 10
            """, (project_id,))
            return serialize_rows(cur.fetchall())

    @staticmethod
    def _get_last_cycle_summary(project_id: str, cycle_type: str) -> Optional[str]:
        """Get the summary from the most recent cycle of a given type."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT cycle_summary FROM synthesis_cycles
                WHERE project_id = %s AND cycle_type = %s::synthesis_cycle_type
                  AND completed_at IS NOT NULL
                ORDER BY completed_at DESC LIMIT 1
            """, (project_id, cycle_type))
            row = cur.fetchone()
            return row["cycle_summary"] if row else "No previous cycle data."

    @staticmethod
    def _call_anthropic(system_prompt: str, user_prompt: str) -> Optional[Dict]:
        """Call Anthropic API for synthesis with retry on 5xx errors.

        Uses a 60-second timeout and retries once on server errors (5xx).
        """
        import httpx

        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY not set")
            return None

        ANTHROPIC_TIMEOUT = 60.0
        MAX_RETRIES = 1

        request_body = {
            "model": SYNTHESIS_MODEL,
            "max_tokens": 4096,
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
        }
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=request_body,
                    timeout=ANTHROPIC_TIMEOUT,
                )

                # Retry on 5xx server errors
                if response.status_code >= 500 and attempt < MAX_RETRIES:
                    logger.warning(
                        f"Anthropic API returned {response.status_code}, "
                        f"retrying ({attempt + 1}/{MAX_RETRIES})..."
                    )
                    import time
                    time.sleep(2 ** attempt)
                    continue

                response.raise_for_status()
                data = response.json()

                # Extract token usage
                usage = data.get("usage", {})
                tokens = {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "cache_read": usage.get("cache_read_input_tokens", 0),
                    "cache_creation": usage.get("cache_creation_input_tokens", 0),
                }
                logger.info(f"Anthropic API tokens: {tokens}")

                # Parse response content
                content = data.get("content", [])
                text = ""
                for block in content:
                    if block.get("type") == "text":
                        text += block.get("text", "")

                # Parse JSON from response
                text = text.strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:])
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()

                try:
                    result = json.loads(text)
                    result["_token_usage"] = tokens
                    return result
                except json.JSONDecodeError:
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        result = json.loads(text[start:end])
                        result["_token_usage"] = tokens
                        return result
                    logger.error(f"Failed to parse Opus response: {text[:500]}")
                    return None

            except httpx.TimeoutException:
                last_error = "Request timed out"
                if attempt < MAX_RETRIES:
                    logger.warning(f"Anthropic API timed out after {ANTHROPIC_TIMEOUT}s, retrying...")
                    continue
                logger.error(f"Anthropic API timed out after {MAX_RETRIES + 1} attempts")
                return None

            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    logger.warning(f"Anthropic API error: {e}, retrying...")
                    import time
                    time.sleep(2 ** attempt)
                    continue
                logger.error(f"Anthropic API call failed after {MAX_RETRIES + 1} attempts: {e}", exc_info=True)
                return None

        logger.error(f"Anthropic API call exhausted retries. Last error: {last_error}")
        return None

    @staticmethod
    def _run_local_synthesis(
        project_id: str,
        signals: List[Dict],
        snapshot: Dict,
        active_items: List[Dict],
        sweep_results: Dict,
    ) -> Dict:
        """Algorithmic synthesis fallback — no LLM required.

        Groups signals by type/entity, detects patterns, and produces
        intelligence items deterministically. Used when ANTHROPIC_API_KEY
        is not set, enabling full pipeline validation and demo mode.
        """
        intelligence_items = []
        overall_health = "green"

        # ── Group signals by type ──────────────────────────────────
        by_type: Dict[str, List[Dict]] = defaultdict(list)
        by_entity: Dict[str, List[Dict]] = defaultdict(list)
        for s in signals:
            by_type[s.get("signal_type", "unknown")].append(s)
            entity_key = f"{s.get('entity_type', '')}:{s.get('entity_value', '')}"
            if entity_key != ":":
                by_entity[entity_key].append(s)

        # ── RFI overdue cluster (convergence / emerging risk) ──────
        overdue_rfis = by_type.get("rfi_became_overdue", [])
        if len(overdue_rfis) >= 10:
            overall_health = "red"
            # Find the worst offenders
            worst = sorted(
                overdue_rfis,
                key=lambda s: s.get("effective_weight", 0),
                reverse=True,
            )[:5]
            days_list = []
            for s in overdue_rfis:
                ctx = s.get("supporting_context_json") or s.get("supporting_context") or {}
                if isinstance(ctx, str):
                    try:
                        ctx = json.loads(ctx)
                    except (json.JSONDecodeError, TypeError):
                        ctx = {}
                days_list.append(ctx.get("days_overdue", 0))
            avg_days = sum(days_list) / len(days_list) if days_list else 0
            max_days = max(days_list) if days_list else 0

            intelligence_items.append({
                "action": "create",
                "item_type": "convergence",
                "title": f"Systemic RFI Response Failure — {len(overdue_rfis)} RFIs overdue",
                "summary": (
                    f"{len(overdue_rfis)} RFIs are past their due date with an average of "
                    f"{avg_days:.0f} days overdue (worst: {max_days} days). This volume "
                    f"indicates a systemic breakdown in the RFI response process, not "
                    f"isolated delays. Recommend escalating to project leadership and "
                    f"scheduling a dedicated RFI resolution session with all responsible parties."
                ),
                "severity": "critical" if len(overdue_rfis) >= 50 else "high",
                "confidence": 0.95,
                "recommended_attention_level": "immediate",
                "source_signal_ids": [s["id"] for s in worst],
                "evidence_weights": ["primary"] * len(worst),
            })
        elif len(overdue_rfis) >= 3:
            overall_health = "yellow" if overall_health == "green" else overall_health
            intelligence_items.append({
                "action": "create",
                "item_type": "emerging_risk",
                "title": f"RFI Response Delays — {len(overdue_rfis)} overdue",
                "summary": (
                    f"{len(overdue_rfis)} RFIs are overdue. Monitor for escalation. "
                    f"Consider follow-up with assignees to prevent cascade."
                ),
                "severity": "medium",
                "confidence": 0.90,
                "recommended_attention_level": "today",
                "source_signal_ids": [s["id"] for s in overdue_rfis[:3]],
                "evidence_weights": ["primary", "supporting", "supporting"],
            })

        # ── Submittal overdue cluster ──────────────────────────────
        overdue_subs = by_type.get("submittal_overdue", [])
        if len(overdue_subs) >= 3:
            overall_health = "yellow" if overall_health == "green" else overall_health
            intelligence_items.append({
                "action": "create",
                "item_type": "emerging_risk",
                "title": f"Submittal Delays — {len(overdue_subs)} past required date",
                "summary": (
                    f"{len(overdue_subs)} submittals are past their required date. "
                    f"Delayed submittals can cascade into procurement and installation "
                    f"delays. Review with project coordinator."
                ),
                "severity": "medium",
                "confidence": 0.90,
                "recommended_attention_level": "today",
                "source_signal_ids": [s["id"] for s in overdue_subs[:3]],
                "evidence_weights": ["primary"] * min(3, len(overdue_subs)),
            })

        # ── Rejected submittals ────────────────────────────────────
        rejected = by_type.get("submittal_rejected", [])
        for s in rejected:
            intelligence_items.append({
                "action": "create",
                "item_type": "pattern_match",
                "title": f"Submittal Rejected — {s.get('summary', 'unknown')[:60]}",
                "summary": (
                    f"{s.get('summary', '')}. Rejected submittals require rework and "
                    f"resubmission, adding delay to the approval chain. Verify corrective "
                    f"action is underway."
                ),
                "severity": "medium",
                "confidence": 0.95,
                "recommended_attention_level": "today",
                "source_signal_ids": [s["id"]],
                "evidence_weights": ["primary"],
            })

        # ── Change order activity ──────────────────────────────────
        cos = by_type.get("change_order_status_changed", [])
        if len(cos) >= 2:
            total_amount = 0
            for s in cos:
                ctx = s.get("supporting_context_json") or s.get("supporting_context") or {}
                if isinstance(ctx, str):
                    try:
                        ctx = json.loads(ctx)
                    except (json.JSONDecodeError, TypeError):
                        ctx = {}
                amt = ctx.get("amount", 0)
                if amt:
                    total_amount += float(amt)
            intelligence_items.append({
                "action": "create",
                "item_type": "emerging_risk",
                "title": f"Change Order Activity — {len(cos)} COs in motion",
                "summary": (
                    f"{len(cos)} change orders have status changes"
                    + (f" totaling ${total_amount:,.0f}" if total_amount else "")
                    + ". Multiple concurrent COs may signal scope creep or "
                    f"unforeseen conditions. Review aggregate budget impact."
                ),
                "severity": "high" if total_amount > 50000 else "medium",
                "confidence": 0.85,
                "recommended_attention_level": "today",
                "source_signal_ids": [s["id"] for s in cos],
                "evidence_weights": ["primary"] * len(cos),
            })

        # ── Contradiction detection (test scenario signals) ────────
        # Look for assurance signals that conflict with negative signals
        # about the same entity
        assurances = by_type.get("correspondence_assurance", [])
        declines = by_type.get("daily_log_manpower_decline", [])
        if assurances and declines:
            overall_health = "yellow" if overall_health == "green" else overall_health
            intelligence_items.append({
                "action": "create",
                "item_type": "contradiction",
                "title": "Contradiction — Manpower data conflicts with verbal assurance",
                "summary": (
                    "Daily log data shows declining manpower, but correspondence "
                    "contains verbal assurances that staffing is adequate. This "
                    "contradiction suggests either the field data or the assurances "
                    "are inaccurate. Recommend verifying actual headcount on-site."
                ),
                "severity": "high",
                "confidence": 0.80,
                "recommended_attention_level": "today",
                "source_signal_ids": [
                    assurances[0]["id"],
                    declines[0]["id"],
                ],
                "evidence_weights": ["primary", "primary"],
            })

        # ── Resubmission without revision (pattern match) ──────────
        resubmissions = by_type.get("submittal_resubmitted", [])
        for s in resubmissions:
            intelligence_items.append({
                "action": "create",
                "item_type": "pattern_match",
                "title": "Pattern — Submittal resubmitted without revision",
                "summary": (
                    f"{s.get('summary', '')}. A submittal resubmitted without a new "
                    f"revision number may indicate the rejection comments were not addressed. "
                    f"Verify the resubmission includes corrective changes."
                ),
                "severity": "medium",
                "confidence": 0.75,
                "recommended_attention_level": "tomorrow_morning",
                "source_signal_ids": [s["id"]],
                "evidence_weights": ["primary"],
            })

        # ── Missing daily logs ─────────────────────────────────────
        missing_logs = by_type.get("daily_log_missing", [])
        if missing_logs:
            intelligence_items.append({
                "action": "create",
                "item_type": "watch_item",
                "title": "Daily Log Not Submitted",
                "summary": (
                    f"Daily log for a recent workday was not submitted. "
                    f"Missing daily logs create gaps in project documentation "
                    f"and reduce SteelSync's analytical coverage."
                ),
                "severity": "low",
                "confidence": 0.95,
                "recommended_attention_level": "this_week",
                "source_signal_ids": [s["id"] for s in missing_logs],
                "evidence_weights": ["primary"] * len(missing_logs),
            })

        # ── Build cycle summary ────────────────────────────────────
        rfi_info = snapshot.get("rfis", {})
        sub_info = snapshot.get("submittals", {})
        summary_parts = []
        summary_parts.append(
            f"Processed {len(signals)} signals across {len(by_type)} signal types."
        )
        if int(rfi_info.get("overdue", 0) or 0) > 0:
            summary_parts.append(
                f"{rfi_info['overdue']} RFIs overdue out of {rfi_info.get('open', '?')} open."
            )
        if int(sub_info.get("overdue", 0) or 0) > 0:
            summary_parts.append(
                f"{sub_info['overdue']} submittals overdue, {sub_info.get('rejected', 0)} rejected."
            )
        if not intelligence_items:
            summary_parts.append("No significant findings requiring attention.")
        else:
            summary_parts.append(
                f"Generated {len(intelligence_items)} intelligence items."
            )

        # ── Generate Radar updates for active Radar items ──────
        radar_updates = []
        try:
            from radar_monitor import get_active_radar_items
            radar_items = get_active_radar_items(project_id)
            for ri in radar_items:
                # Check if any intelligence items relate to this Radar item's scope
                ri_keywords = set()
                scope = ri.get("monitoring_scope_json") or {}
                if isinstance(scope, str):
                    try:
                        scope = json.loads(scope)
                    except (json.JSONDecodeError, TypeError):
                        scope = {}
                for kw in scope.get("keywords", []):
                    ri_keywords.add(kw.lower())
                ri_entity_types = set(scope.get("entity_types", []))

                # Check if any of our new intelligence items relate
                for item in intelligence_items:
                    item_text = (item.get("title", "") + " " + item.get("summary", "")).lower()
                    keyword_hits = sum(1 for kw in ri_keywords if kw in item_text)
                    if keyword_hits >= 2 or (ri_entity_types and
                            any(et in item.get("summary", "").lower() for et in ri_entity_types)):
                        radar_updates.append({
                            "radar_item_id": str(ri["id"]),
                            "relevance_summary": (
                                f"Intelligence item '{item.get('title', '')[:60]}' "
                                f"relates to Radar tracking target."
                            ),
                            "severity": item.get("severity", "medium"),
                            "new_activity_entry": (
                                f"Synthesis detected relevant intelligence: {item.get('title', '')}"
                            ),
                        })
                        break  # One update per Radar item per cycle
        except Exception as e:
            logger.warning(f"Local Radar update generation failed: {e}")

        # ── Auto-evaluate reinforcement candidates ──────────────
        # In local mode, promote candidates where target signal type
        # matches a signal type present in this cycle's signals
        reinforcement_evals = []
        # Get pending candidates from the signals list
        signal_types_present = set(s.get("signal_type", "") for s in signals)
        with get_cursor() as cur:
            cur.execute("""
                SELECT rc.id, rc.confidence, ts.signal_type as target_type
                FROM reinforcement_candidates rc
                JOIN signals ts ON ts.id = rc.target_signal_id
                WHERE ts.project_id = (
                    SELECT project_id FROM signals WHERE id = rc.source_signal_id LIMIT 1
                )
                AND rc.status = 'pending'
                LIMIT 20
            """)
            for row in cur.fetchall():
                if row["target_type"] in signal_types_present and row["confidence"] >= 0.5:
                    reinforcement_evals.append({
                        "candidate_id": str(row["id"]),
                        "action": "promote",
                    })
                elif row["confidence"] < 0.3:
                    reinforcement_evals.append({
                        "candidate_id": str(row["id"]),
                        "action": "discard",
                    })

        return {
            "cycle_summary": " ".join(summary_parts),
            "overall_health": overall_health,
            "intelligence_items": intelligence_items,
            "radar_updates": radar_updates,
            "working_memory_actions": [],
            "reinforcement_evaluations": reinforcement_evals,
            "_token_usage": {"input_tokens": 0, "output_tokens": 0, "model": "local_algorithmic"},
        }

    @classmethod
    def run_cycle(cls, project_id: str, cycle_type: str = "morning_briefing",
                  escalation_item_id: str = None) -> Optional[str]:
        """Run a complete synthesis cycle for a project.

        For escalation_review cycles, pass escalation_item_id to focus the
        deep-dive on a specific intelligence item.

        Returns the synthesis_cycle_id.
        """
        logger.info(f"Starting {cycle_type} synthesis for project {project_id}")

        # Check onboarding phase
        with get_cursor() as cur:
            cur.execute("SELECT onboarding_phase::text FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            onboarding_phase = row["onboarding_phase"] if row else "live"

        if onboarding_phase == "historical_ingest":
            logger.info(f"Skipping synthesis for {project_id} — project in historical_ingest phase")
            return None

        # Create cycle record
        cycle_id = str(uuid4())
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO synthesis_cycles (id, project_id, cycle_type, model_used)
                VALUES (%s, %s, %s::synthesis_cycle_type, %s)
            """, (cycle_id, project_id, cycle_type, SYNTHESIS_MODEL))

        try:
            # Step 0: Run decay cycle to update signal weights
            decay_results = cls.run_decay_cycle(project_id)
            logger.info(f"Pre-synthesis decay: {decay_results}")

            # Step 1: Run deterministic signal sweep
            from signal_generation import run_deterministic_sweep
            sweep_results = run_deterministic_sweep(project_id)

            # Step 2: Gather data
            # Use wider window if no previous cycles exist (first run / baseline)
            last_summary = cls._get_last_cycle_summary(project_id, cycle_type)
            since_hours = 24
            if last_summary == "No previous cycle data.":
                since_hours = 720  # 30 days for first run
                logger.info("First synthesis cycle — using 30-day signal window")
            signals = cls._get_signals_for_cycle(project_id, since_hours=since_hours)
            active_items = cls._get_active_intelligence_items(project_id)
            snapshot = build_project_snapshot(project_id)

            # Step 3: Build prompt
            template_kwargs = {}
            if cycle_type == "midday_checkpoint":
                template_kwargs["morning_summary"] = cls._get_last_cycle_summary(
                    project_id, "morning_briefing"
                )
            elif cycle_type == "end_of_day":
                template_kwargs["morning_summary"] = cls._get_last_cycle_summary(
                    project_id, "morning_briefing"
                )
                template_kwargs["midday_summary"] = cls._get_last_cycle_summary(
                    project_id, "midday_checkpoint"
                )
            elif cycle_type == "escalation_review" and escalation_item_id:
                # Fetch the escalation item and related items for deep-dive
                escalation_item = ItemManager.get_item(escalation_item_id)
                if escalation_item:
                    template_kwargs["escalation_item"] = json.dumps(
                        escalation_item, indent=2, default=str
                    )
                    # Find related items by shared signals or same entity
                    related = []
                    for item in active_items:
                        if item.get("id") != escalation_item_id:
                            related.append(item)
                    template_kwargs["related_items"] = json.dumps(
                        related[:10], indent=2, default=str
                    )
                else:
                    template_kwargs["escalation_item"] = "Item not found"
                    template_kwargs["related_items"] = "[]"

            system_prompt = cls._get_template(cycle_type, **template_kwargs)

            # Add calibration context if in calibration phase
            if onboarding_phase == "calibration":
                system_prompt += """

CALIBRATION MODE ACTIVE:
This project is in the calibration phase of onboarding. The system is still
learning project norms and patterns. Apply these restrictions:
- SUPPRESS Category E (Actor Pattern) signals — insufficient data for reliable detection
- SUPPRESS Category G (Cross-Project Correlation) signals — baseline not established
- Mark all items with confidence < 0.7 as watch_items rather than active items
- Include a "calibrating" flag in your output metadata
"""

            # Step 3b: Run Radar passive monitoring against new signals
            try:
                from radar_monitor import evaluate_signals_against_radar, build_radar_mandate
                radar_stats = evaluate_signals_against_radar(project_id, signals)
                logger.info(f"Radar passive monitoring: {radar_stats}")

                # Build Radar mandate for synthesis prompt
                radar_mandate = build_radar_mandate(project_id)
                if radar_mandate:
                    system_prompt += "\n\n" + radar_mandate
            except Exception as e:
                logger.warning(f"Radar monitoring skipped: {e}")
                radar_mandate = None

            # Gather reinforcement candidates
            pending_candidates = cls._get_pending_reinforcement_candidates(project_id)
            reinforcement_block = ""
            if pending_candidates:
                reinforcement_block = f"""
REINFORCEMENT CANDIDATES ({len(pending_candidates)} pending evaluation):
These are entity/topic overlaps detected by the local LLM between new events and existing signals.
Evaluate each candidate: is the relationship operationally meaningful?
Include a "reinforcement_evaluations" array in your output:
[{{"candidate_id": "UUID", "action": "promote"|"discard", "reason": "why"}}]

{json.dumps(pending_candidates, indent=2, default=str)}
"""

            # Gather user feedback context
            dismissed_items = cls._get_dismissed_feedback(project_id)
            feedback_block = ""
            if dismissed_items:
                feedback_block = f"""
USER FEEDBACK (items dismissed in the past 7 days):
{json.dumps(dismissed_items, indent=2, default=str)}
NOTE: Avoid reproducing similar items unless new, strong evidence emerges.
"""

            user_prompt = f"""PROJECT SNAPSHOT:
{json.dumps(snapshot, indent=2, default=str)}

NEW SIGNALS SINCE LAST CYCLE ({len(signals)} signals):
{json.dumps(signals, indent=2, default=str)}

ACTIVE INTELLIGENCE ITEMS ({len(active_items)} items):
{json.dumps(active_items, indent=2, default=str)}
{reinforcement_block}{feedback_block}
CYCLE METADATA:
- Cycle type: {cycle_type}
- Timestamp: {datetime.now().isoformat()}
- Deterministic sweep results: {json.dumps(sweep_results)}
"""

            # Step 4: Call Anthropic API (or fall back to local synthesis)
            result = cls._call_anthropic(system_prompt, user_prompt)

            if not result:
                logger.info("Anthropic API unavailable — running local algorithmic synthesis")
                result = cls._run_local_synthesis(project_id, signals, snapshot, active_items, sweep_results)

                # Update cycle record to reflect local model
                with get_cursor() as cur:
                    cur.execute("""
                        UPDATE synthesis_cycles SET model_used = 'local_algorithmic'
                        WHERE id = %s
                    """, (cycle_id,))

            # Step 5: Process results
            token_usage = result.pop("_token_usage", {})
            items_created = 0
            items_updated = 0
            items_resolved = 0

            for item_output in result.get("intelligence_items", []):
                action = item_output.get("action", "create")

                if action == "create":
                    ItemManager.create_item(project_id, item_output, cycle_id)
                    items_created += 1
                elif action == "update":
                    existing_id = item_output.get("existing_item_id")
                    if existing_id:
                        ItemManager.update_item(existing_id, item_output, cycle_id)
                        items_updated += 1
                elif action == "reinforce":
                    existing_id = item_output.get("existing_item_id")
                    if existing_id:
                        ItemManager.reinforce_item(
                            existing_id,
                            item_output.get("source_signal_ids", [])
                        )
                        items_updated += 1
                elif action == "downgrade":
                    existing_id = item_output.get("existing_item_id")
                    if existing_id:
                        ItemManager.downgrade_item(
                            existing_id,
                            item_output.get("summary", "Downgraded by synthesis")
                        )
                elif action == "resolve":
                    existing_id = item_output.get("existing_item_id")
                    if existing_id:
                        ItemManager.resolve_item(
                            existing_id,
                            item_output.get("summary", "Resolved by synthesis")
                        )
                        items_resolved += 1
                elif action == "merge":
                    existing_id = item_output.get("existing_item_id")
                    source_ids = item_output.get("merge_source_ids", [])
                    if existing_id and source_ids:
                        ItemManager.merge_items(existing_id, source_ids, item_output, cycle_id)
                        items_updated += 1

            # Process Radar updates from synthesis output
            radar_updates = result.get("radar_updates", [])
            if radar_updates:
                try:
                    from radar_monitor import process_radar_updates
                    radar_count = process_radar_updates(radar_updates, cycle_id)
                    logger.info(f"Processed {radar_count} Radar updates from synthesis")
                except Exception as e:
                    logger.warning(f"Radar update processing failed: {e}")

            # Process reinforcement evaluations from synthesis output
            for eval_item in result.get("reinforcement_evaluations", []):
                cid = eval_item.get("candidate_id")
                action = eval_item.get("action")
                if not cid or not action:
                    continue
                if action == "promote":
                    cls._promote_reinforcement_candidate(cid)
                elif action == "discard":
                    cls._discard_reinforcement_candidate(cid)

            # Process working memory actions
            for wm_action in result.get("working_memory_actions", []):
                action = wm_action.get("action")
                item_id = wm_action.get("item_id")
                reason = wm_action.get("reason", "")

                if action == "downgrade" and item_id:
                    ItemManager.downgrade_item(item_id, reason)
                elif action == "resolve" and item_id:
                    ItemManager.resolve_item(item_id, reason)
                    items_resolved += 1
                elif action == "archive" and item_id:
                    ItemManager.archive_item(item_id, reason)

            # Step 6: Update cycle record
            with get_cursor() as cur:
                cur.execute("""
                    UPDATE synthesis_cycles SET
                        completed_at = NOW(),
                        signals_processed = %s,
                        items_created = %s,
                        items_updated = %s,
                        items_resolved = %s,
                        cycle_summary = %s,
                        overall_health = %s::project_health,
                        input_tokens = %s,
                        output_tokens = %s
                    WHERE id = %s
                """, (
                    len(signals),
                    items_created,
                    items_updated,
                    items_resolved,
                    result.get("cycle_summary", ""),
                    result.get("overall_health", "green"),
                    token_usage.get("input_tokens", 0),
                    token_usage.get("output_tokens", 0),
                    cycle_id,
                ))

            # Step 7: Write working memory snapshot with health trend
            with get_cursor() as cur:
                cur.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM intelligence_items WHERE project_id = %s AND status IN ('new', 'active')) as active_count,
                        (SELECT COUNT(*) FROM intelligence_items WHERE project_id = %s AND status = 'watch') as watch_count
                """, (project_id, project_id))
                counts = cur.fetchone()

                # Compute health_trend by comparing to previous snapshot
                health_trend = "stable"
                cur.execute("""
                    SELECT active_item_count, watch_item_count
                    FROM working_memory_state
                    WHERE project_id = %s
                    ORDER BY created_at DESC LIMIT 1
                """, (project_id,))
                prev = cur.fetchone()
                if prev:
                    prev_total = prev["active_item_count"] + prev["watch_item_count"]
                    curr_total = counts["active_count"] + counts["watch_count"]
                    if curr_total > prev_total * 1.2:
                        health_trend = "declining"
                    elif curr_total < prev_total * 0.8:
                        health_trend = "improving"

                cur.execute("""
                    INSERT INTO working_memory_state
                        (id, project_id, active_item_count, watch_item_count,
                         total_signal_count_today, state_json)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid4()), project_id,
                    counts["active_count"], counts["watch_count"],
                    len(signals),
                    json.dumps({
                        "cycle_type": cycle_type,
                        "cycle_summary": result.get("cycle_summary"),
                        "overall_health": result.get("overall_health"),
                        "health_trend": health_trend,
                        "tomorrow_watch_list": result.get("tomorrow_watch_list", []),
                    }),
                ))

            logger.info(
                f"Synthesis {cycle_type} complete for project {project_id}: "
                f"created={items_created}, updated={items_updated}, resolved={items_resolved}, "
                f"tokens={token_usage}"
            )
            return cycle_id

        except Exception as e:
            logger.error(f"Synthesis cycle failed: {e}", exc_info=True)
            with get_cursor() as cur:
                cur.execute("""
                    UPDATE synthesis_cycles SET
                        completed_at = NOW(),
                        error_log = %s
                    WHERE id = %s
                """, (str(e), cycle_id))
            return cycle_id

    @staticmethod
    def run_decay_cycle(project_id: str) -> Dict[str, int]:
        """CC-3.4: Working Memory Lifecycle — signal decay and item lifecycle.

        1. Check onboarding phase — skip decay during historical_ingest and calibration
        2. Recalculate effective_weight for all active signals based on age + decay_profile
        3. Archive signals decayed below threshold (0.1)
        4. Downgrade active items not reinforced in 7 days → watch
        5. Archive watch items not reinforced in 15 days
        6. Archive resolved items older than 14 days

        Returns counts of affected rows.
        """
        results = {"signals_decayed": 0, "signals_archived": 0,
                    "items_downgraded": 0, "items_watch_archived": 0,
                    "items_archived": 0, "skipped_reason": None}

        # Check onboarding phase — decay clocks don't run during calibration
        with get_cursor() as cur:
            cur.execute("""
                SELECT onboarding_phase FROM projects WHERE id = %s
            """, (project_id,))
            row = cur.fetchone()
            phase = row["onboarding_phase"] if row else None
            if phase in ("historical_ingest", "calibration"):
                results["skipped_reason"] = f"Decay skipped: project in {phase} phase"
                logger.info(results["skipped_reason"])
                return results

        # Decay half-life in hours for each profile
        decay_half_lives = {
            "fast_24h": 24,
            "medium_72h": 72,
            "slow_7d": 168,
            "persistent": 8760,  # 1 year — effectively no decay
        }

        ARCHIVE_THRESHOLD = 0.1  # Per spec: signals below 0.1 auto-archived

        with get_cursor() as cur:
            # Step 1: Recalculate effective_weight using exponential decay
            # effective_weight = confidence * strength * 2^(-age_hours / half_life)
            for profile, half_life in decay_half_lives.items():
                if profile == "persistent":
                    continue  # Skip persistent signals
                cur.execute("""
                    UPDATE signals SET
                        effective_weight = ROUND(
                            (confidence * strength * POWER(2.0,
                                -EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600.0 / %s
                            ))::numeric, 2
                        )
                    WHERE project_id = %s
                      AND decay_profile = %s::decay_profile
                      AND archived_at IS NULL
                      AND resolved_at IS NULL
                """, (half_life, project_id, profile))
                results["signals_decayed"] += cur.rowcount

            # Step 2: Archive signals with effective_weight below threshold
            cur.execute("""
                UPDATE signals SET archived_at = NOW()
                WHERE project_id = %s
                  AND archived_at IS NULL
                  AND resolved_at IS NULL
                  AND effective_weight < %s
                  AND decay_profile != 'persistent'
            """, (project_id, ARCHIVE_THRESHOLD))
            results["signals_archived"] = cur.rowcount

            # Step 3: Downgrade active items not reinforced in 7 days → watch
            cur.execute("""
                UPDATE intelligence_items SET
                    status = 'watch'::intelligence_status
                WHERE project_id = %s
                  AND status = 'active'
                  AND COALESCE(last_reinforced_at, first_created_at) < NOW() - INTERVAL '7 days'
            """, (project_id,))
            results["items_downgraded"] = cur.rowcount

            # Step 4: Archive watch items not reinforced in 15 days
            cur.execute("""
                UPDATE intelligence_items SET
                    status = 'archived'::intelligence_status,
                    archived_at = NOW()
                WHERE project_id = %s
                  AND status = 'watch'
                  AND COALESCE(last_reinforced_at, first_created_at) < NOW() - INTERVAL '15 days'
            """, (project_id,))
            results["items_watch_archived"] = cur.rowcount

            # Step 5: Archive resolved items older than 14 days
            cur.execute("""
                UPDATE intelligence_items SET
                    status = 'archived'::intelligence_status,
                    archived_at = NOW()
                WHERE project_id = %s
                  AND status = 'resolved'
                  AND resolved_at < NOW() - INTERVAL '14 days'
            """, (project_id,))
            results["items_archived"] = cur.rowcount

        logger.info(f"Decay cycle for {project_id}: {results}")
        return results

    @classmethod
    def run_all_projects(cls, cycle_type: str = "morning_briefing") -> Dict[str, str]:
        """Run synthesis cycle for all active projects."""
        with get_cursor() as cur:
            cur.execute("SELECT id, name FROM projects WHERE status = 'active' AND is_deleted = FALSE")
            projects = cur.fetchall()

        results = {}
        for project in projects:
            try:
                cycle_id = cls.run_cycle(str(project["id"]), cycle_type)
                results[str(project["id"])] = cycle_id
            except Exception as e:
                logger.error(f"Synthesis failed for project {project['name']}: {e}")
                results[str(project["id"])] = f"error: {e}"

        return results
