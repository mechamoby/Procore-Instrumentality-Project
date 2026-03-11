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
        """Get new signals since last cycle."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT id, signal_type, signal_category, summary, confidence,
                       strength, effective_weight, entity_type, entity_value,
                       created_at
                FROM signals
                WHERE project_id = %s
                  AND archived_at IS NULL
                  AND created_at > NOW() - INTERVAL '%s hours'
                ORDER BY effective_weight DESC
                LIMIT 50
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
        """Call Anthropic API for synthesis."""
        import httpx

        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY not set")
            return None

        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
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
                },
                timeout=120.0,
            )
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

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}", exc_info=True)
            return None

    @classmethod
    def run_cycle(cls, project_id: str, cycle_type: str = "morning_briefing") -> Optional[str]:
        """Run a complete synthesis cycle for a project.

        Returns the synthesis_cycle_id.
        """
        logger.info(f"Starting {cycle_type} synthesis for project {project_id}")

        # Create cycle record
        cycle_id = str(uuid4())
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO synthesis_cycles (id, project_id, cycle_type, model_used)
                VALUES (%s, %s, %s::synthesis_cycle_type, %s)
            """, (cycle_id, project_id, cycle_type, SYNTHESIS_MODEL))

        try:
            # Step 1: Run deterministic signal sweep
            from signal_generation import run_deterministic_sweep
            sweep_results = run_deterministic_sweep(project_id)

            # Step 2: Gather data
            signals = cls._get_signals_for_cycle(project_id)
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

            system_prompt = cls._get_template(cycle_type, **template_kwargs)

            user_prompt = f"""PROJECT SNAPSHOT:
{json.dumps(snapshot, indent=2, default=str)}

NEW SIGNALS SINCE LAST CYCLE ({len(signals)} signals):
{json.dumps(signals, indent=2, default=str)}

ACTIVE INTELLIGENCE ITEMS ({len(active_items)} items):
{json.dumps(active_items, indent=2, default=str)}

CYCLE METADATA:
- Cycle type: {cycle_type}
- Timestamp: {datetime.now().isoformat()}
- Deterministic sweep results: {json.dumps(sweep_results)}
"""

            # Step 4: Call Anthropic API
            result = cls._call_anthropic(system_prompt, user_prompt)

            if not result:
                with get_cursor() as cur:
                    cur.execute("""
                        UPDATE synthesis_cycles SET
                            completed_at = NOW(),
                            error_log = 'API call failed or returned unparseable response'
                        WHERE id = %s
                    """, (cycle_id,))
                return cycle_id

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

            # Step 7: Write working memory snapshot
            with get_cursor() as cur:
                cur.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM intelligence_items WHERE project_id = %s AND status IN ('new', 'active')) as active_count,
                        (SELECT COUNT(*) FROM intelligence_items WHERE project_id = %s AND status = 'watch') as watch_count
                """, (project_id, project_id))
                counts = cur.fetchone()

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
