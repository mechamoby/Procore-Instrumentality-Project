"""SteelSync Signal Generation Service — CC-2.1 + CC-2.2

Implements:
- SignalWriter: validates, deduplicates, and writes signals to the database
- Deterministic signal detectors (CC-2.1): pure code, no LLM
- SignalGenerationService (CC-2.2): LLM-based signal detection via Ollama
- Sweep function to run all detectors for a project
"""

import json
import logging
import os
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from steelsync_db import get_cursor, serialize_row, serialize_rows

logger = logging.getLogger("steelsync.signals")

# Categories that only synthesis (Opus) can produce
SYNTHESIS_ONLY_CATEGORIES = {"contradiction", "actor_pattern", "cross_project"}

# Allowed signal categories for ingestion-time generation
ALLOWED_INGESTION_CATEGORIES = {
    "status_change", "reinforcement", "timeline",
    "document_significance", "radar_match"
}

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("SIGNAL_LLM_MODEL", "deepseek-r1:8b")


# =============================================================================
# SIGNAL WRITER
# =============================================================================

class SignalWriter:
    """Validates, deduplicates, and writes signals to the signals table."""

    @staticmethod
    def write(
        project_id: str,
        source_type: str,
        signal_type: str,
        signal_category: str,
        summary: str,
        confidence: float,
        strength: float = 1.0,
        decay_profile: str = "medium_72h",
        entity_type: str = None,
        entity_value: str = None,
        source_document_id: str = None,
        supporting_context: dict = None,
        source_multiplier: float = 1.0,
    ) -> Optional[str]:
        """Write a signal to the database after validation and dedup check.

        source_multiplier adjusts effective_weight for low-confidence document
        pipeline matches (e.g., 0.5 for uncertain project assignment).

        Returns signal ID if written, None if skipped (duplicate or invalid).
        """
        # Validate category
        if signal_category in SYNTHESIS_ONLY_CATEGORIES:
            logger.warning(
                f"Blocked synthesis-only category '{signal_category}' "
                f"from ingestion-time signal (type={signal_type})"
            )
            return None

        if signal_category not in ALLOWED_INGESTION_CATEGORIES:
            logger.error(f"Unknown signal category: {signal_category}")
            return None

        # Validate confidence
        if not (0.0 <= confidence <= 1.0):
            logger.error(f"Invalid confidence {confidence} for signal {signal_type}")
            return None

        # Validate required fields
        if not summary or not signal_type:
            logger.error("Missing required signal fields: summary and signal_type")
            return None

        # Compute effective_weight with source multiplier and initial decay_factor=1.0
        source_multiplier = max(0.0, min(1.0, source_multiplier))
        effective_weight = round(confidence * strength * source_multiplier, 2)

        with get_cursor() as cur:
            # Deduplication check: same source_document_id + signal_type within 1 hour
            if source_document_id:
                cur.execute("""
                    SELECT id, supporting_context_json FROM signals
                    WHERE project_id = %s
                      AND source_document_id = %s
                      AND signal_type = %s
                      AND created_at > NOW() - INTERVAL '1 hour'
                    LIMIT 1
                """, (project_id, source_document_id, signal_type))

                existing = cur.fetchone()
                if existing:
                    # Check if new signal has additional context
                    if supporting_context and existing["supporting_context_json"]:
                        existing_ctx = existing["supporting_context_json"]
                        if isinstance(existing_ctx, str):
                            existing_ctx = json.loads(existing_ctx)
                        new_keys = set(supporting_context.keys()) - set(existing_ctx.keys())
                        if new_keys:
                            # Merge new context into existing signal
                            merged = {**existing_ctx, **supporting_context}
                            cur.execute("""
                                UPDATE signals SET supporting_context_json = %s
                                WHERE id = %s
                            """, (json.dumps(merged), existing["id"]))
                            logger.info(
                                f"Merged context into existing signal {existing['id']} "
                                f"(new keys: {new_keys})"
                            )
                            return str(existing["id"])
                    logger.info(
                        f"Dedup: skipping duplicate signal {signal_type} for "
                        f"source_document_id={source_document_id}"
                    )
                    return None

            # Write the signal
            signal_id = str(uuid4())
            cur.execute("""
                INSERT INTO signals (
                    id, project_id, source_type, source_document_id,
                    signal_type, signal_category, summary,
                    confidence, strength, effective_weight,
                    decay_profile, entity_type, entity_value,
                    supporting_context_json
                ) VALUES (
                    %s, %s, %s::signal_source_type, %s,
                    %s, %s::signal_category, %s,
                    %s, %s, %s,
                    %s::decay_profile, %s, %s,
                    %s
                )
            """, (
                signal_id, project_id, source_type, source_document_id,
                signal_type, signal_category, summary,
                confidence, strength, effective_weight,
                decay_profile, entity_type, entity_value,
                json.dumps(supporting_context) if supporting_context else None,
            ))

            logger.info(
                f"Signal written: {signal_type} [{signal_category}] "
                f"project={project_id} confidence={confidence} weight={effective_weight}"
            )
            return signal_id


# =============================================================================
# CC-2.1: DETERMINISTIC SIGNAL DETECTORS
# =============================================================================

def detect_rfis_overdue(project_id: str) -> int:
    """Detect RFIs that are past their due date and still open."""
    count = 0
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, number, subject, due_date, date_initiated, status
            FROM rfis
            WHERE project_id = %s
              AND is_deleted = FALSE
              AND status NOT IN ('closed', 'answered', 'void')
              AND due_date IS NOT NULL
              AND due_date < CURRENT_DATE
        """, (project_id,))

        for rfi in cur.fetchall():
            days_overdue = (date.today() - rfi["due_date"]).days
            sid = SignalWriter.write(
                project_id=project_id,
                source_type="procore_webhook",
                signal_type="rfi_became_overdue",
                signal_category="status_change",
                summary=f"RFI #{rfi['number']} '{rfi['subject']}' is {days_overdue} days past due date ({rfi['due_date']})",
                confidence=0.98,
                strength=min(1.0, 0.5 + (days_overdue / 14)),  # Strength increases with age
                decay_profile="medium_72h",
                entity_type="rfi",
                entity_value=rfi["number"],
                source_document_id=str(rfi["id"]),
                supporting_context={
                    "rfi_number": rfi["number"],
                    "subject": rfi["subject"],
                    "due_date": str(rfi["due_date"]),
                    "days_overdue": days_overdue,
                    "status": rfi["status"],
                },
            )
            if sid:
                count += 1

    logger.info(f"detect_rfis_overdue: {count} signals for project {project_id}")
    return count


def detect_submittals_rejected(project_id: str) -> int:
    """Detect submittals that have been rejected."""
    count = 0
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, number, title, status, spec_section_number, updated_at
            FROM submittals
            WHERE project_id = %s
              AND is_deleted = FALSE
              AND status = 'rejected'
              AND updated_at > NOW() - INTERVAL '72 hours'
        """, (project_id,))

        for sub in cur.fetchall():
            sid = SignalWriter.write(
                project_id=project_id,
                source_type="procore_webhook",
                signal_type="submittal_rejected",
                signal_category="status_change",
                summary=f"Submittal #{sub['number']} '{sub['title']}' was rejected",
                confidence=1.0,
                strength=0.9,
                decay_profile="medium_72h",
                entity_type="submittal",
                entity_value=sub["number"],
                source_document_id=str(sub["id"]),
                supporting_context={
                    "submittal_number": sub["number"],
                    "title": sub["title"],
                    "spec_section": sub["spec_section_number"],
                },
            )
            if sid:
                count += 1

    logger.info(f"detect_submittals_rejected: {count} signals for project {project_id}")
    return count


def detect_daily_log_missing(project_id: str) -> int:
    """Detect if yesterday's daily log is missing."""
    count = 0
    with get_cursor() as cur:
        # Check for yesterday's log
        yesterday = date.today() - timedelta(days=1)
        # Skip weekends
        if yesterday.weekday() >= 5:
            return 0

        cur.execute("""
            SELECT id FROM daily_reports
            WHERE project_id = %s AND report_date = %s AND is_deleted = FALSE
        """, (project_id, yesterday))

        if not cur.fetchone():
            sid = SignalWriter.write(
                project_id=project_id,
                source_type="procore_webhook",
                signal_type="daily_log_missing",
                signal_category="status_change",
                summary=f"Daily log for {yesterday} has not been submitted",
                confidence=0.95,
                strength=0.7,
                decay_profile="fast_24h",
                entity_type="daily_report",
                entity_value=str(yesterday),
                supporting_context={
                    "missing_date": str(yesterday),
                    "project_id": project_id,
                },
            )
            if sid:
                count += 1

    logger.info(f"detect_daily_log_missing: {count} signals for project {project_id}")
    return count


def detect_schedule_milestones_approaching(project_id: str, days_ahead: int = 14) -> int:
    """Detect schedule milestones within N days."""
    count = 0
    with get_cursor() as cur:
        cur.execute("""
            SELECT sa.id, sa.name, sa.finish_date, sa.percent_complete, sa.is_critical,
                   sch.name as schedule_name
            FROM schedule_activities sa
            JOIN schedules sch ON sch.id = sa.schedule_id
            WHERE sch.project_id = %s
              AND sch.is_current = TRUE
              AND sch.is_deleted = FALSE
              AND sa.is_milestone = TRUE
              AND sa.actual_finish IS NULL
              AND sa.finish_date IS NOT NULL
              AND sa.finish_date BETWEEN CURRENT_DATE AND CURRENT_DATE + %s
        """, (project_id, days_ahead))

        for ms in cur.fetchall():
            days_until = (ms["finish_date"] - date.today()).days
            sid = SignalWriter.write(
                project_id=project_id,
                source_type="procore_webhook",
                signal_type="schedule_milestone_approaching",
                signal_category="timeline",
                summary=f"Milestone '{ms['name']}' due in {days_until} days ({ms['finish_date']})"
                        + (" [CRITICAL PATH]" if ms["is_critical"] else ""),
                confidence=0.98,
                strength=min(1.0, 1.0 - (days_until / days_ahead * 0.5)),
                decay_profile="slow_7d",
                entity_type="schedule_activity",
                entity_value=ms["name"],
                source_document_id=str(ms["id"]),
                supporting_context={
                    "milestone_name": ms["name"],
                    "finish_date": str(ms["finish_date"]),
                    "days_until": days_until,
                    "percent_complete": float(ms["percent_complete"]) if ms["percent_complete"] else 0,
                    "is_critical": ms["is_critical"],
                },
            )
            if sid:
                count += 1

    logger.info(f"detect_schedule_milestones: {count} signals for project {project_id}")
    return count


def detect_change_order_status_changed(project_id: str) -> int:
    """Detect change orders with recent status changes."""
    count = 0
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, number, title, status, amount, schedule_impact_days, updated_at
            FROM change_orders
            WHERE project_id = %s
              AND is_deleted = FALSE
              AND updated_at > NOW() - INTERVAL '72 hours'
        """, (project_id,))

        for co in cur.fetchall():
            sid = SignalWriter.write(
                project_id=project_id,
                source_type="procore_webhook",
                signal_type="change_order_status_changed",
                signal_category="status_change",
                summary=f"Change Order #{co['number']} '{co['title']}' is now '{co['status']}'"
                        + (f" (${float(co['amount']):,.0f})" if co["amount"] else ""),
                confidence=0.98,
                strength=0.8,
                decay_profile="medium_72h",
                entity_type="change_order",
                entity_value=co["number"],
                source_document_id=str(co["id"]),
                supporting_context={
                    "co_number": co["number"],
                    "title": co["title"],
                    "status": co["status"],
                    "amount": float(co["amount"]) if co["amount"] else None,
                    "schedule_impact_days": co["schedule_impact_days"],
                },
            )
            if sid:
                count += 1

    logger.info(f"detect_change_order_status: {count} signals for project {project_id}")
    return count


def detect_submittals_overdue(project_id: str) -> int:
    """Detect submittals past their required date."""
    count = 0
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, number, title, required_date, submitted_date, status, spec_section_number
            FROM submittals
            WHERE project_id = %s
              AND is_deleted = FALSE
              AND status NOT IN ('approved', 'approved_as_noted', 'closed', 'void')
              AND required_date IS NOT NULL
              AND required_date < CURRENT_DATE
        """, (project_id,))

        for sub in cur.fetchall():
            days_overdue = (date.today() - sub["required_date"]).days
            sid = SignalWriter.write(
                project_id=project_id,
                source_type="procore_webhook",
                signal_type="submittal_overdue",
                signal_category="timeline",
                summary=f"Submittal #{sub['number']} '{sub['title']}' is {days_overdue} days past required date ({sub['required_date']})",
                confidence=0.98,
                strength=min(1.0, 0.5 + (days_overdue / 14)),
                decay_profile="medium_72h",
                entity_type="submittal",
                entity_value=sub["number"],
                source_document_id=str(sub["id"]),
                supporting_context={
                    "submittal_number": sub["number"],
                    "title": sub["title"],
                    "required_date": str(sub["required_date"]),
                    "days_overdue": days_overdue,
                    "status": sub["status"],
                    "spec_section": sub["spec_section_number"],
                },
            )
            if sid:
                count += 1

    logger.info(f"detect_submittals_overdue: {count} signals for project {project_id}")
    return count


def _get_onboarding_phase(project_id: str) -> str:
    """Get the onboarding phase for a project."""
    with get_cursor() as cur:
        cur.execute("SELECT onboarding_phase::text FROM projects WHERE id = %s", (project_id,))
        row = cur.fetchone()
        return row["onboarding_phase"] if row else "live"


def run_deterministic_sweep(project_id: str) -> Dict[str, int]:
    """Run all deterministic detectors for a project.

    Returns dict of detector_name -> signal_count.
    Respects onboarding phase: skips during historical_ingest.
    """
    # Check onboarding phase
    phase = _get_onboarding_phase(project_id)
    if phase == "historical_ingest":
        logger.info(f"Skipping signal sweep for {project_id} — project in historical_ingest phase")
        return {"skipped": True, "reason": "historical_ingest"}

    is_calibration = (phase == "calibration")
    logger.info(f"Running deterministic signal sweep for project {project_id} (phase={phase})")
    results = {}

    detectors = [
        ("rfis_overdue", detect_rfis_overdue),
        ("submittals_rejected", detect_submittals_rejected),
        ("submittals_overdue", detect_submittals_overdue),
        ("daily_log_missing", detect_daily_log_missing),
        ("schedule_milestones_approaching", detect_schedule_milestones_approaching),
        ("change_order_status_changed", detect_change_order_status_changed),
    ]

    for name, detector in detectors:
        try:
            count = detector(project_id)
            results[name] = count
        except Exception as e:
            logger.error(f"Detector {name} failed: {e}", exc_info=True)
            results[name] = -1

    # Tag signals as calibration signals during calibration phase
    if is_calibration:
        total_written = sum(v for v in results.values() if isinstance(v, int) and v > 0)
        if total_written > 0:
            with get_cursor() as cur:
                cur.execute("""
                    UPDATE signals SET
                        supporting_context_json = COALESCE(supporting_context_json, '{}'::jsonb)
                            || '{"is_calibration_signal": true}'::jsonb
                    WHERE project_id = %s
                      AND created_at > NOW() - INTERVAL '5 minutes'
                      AND (supporting_context_json->>'is_calibration_signal') IS NULL
                """, (project_id,))
                logger.info(f"Tagged {cur.rowcount} signals as calibration signals")

    total = sum(v for v in results.values() if v > 0)
    logger.info(f"Sweep complete: {total} total signals generated. Details: {results}")
    return results


# =============================================================================
# CC-2.2: LLM-BASED SIGNAL GENERATION SERVICE
# =============================================================================

class SignalGenerationService:
    """Processes data items through LLM-based signal detection."""

    SIGNAL_PROMPT_TEMPLATE = """You are a construction project intelligence signal detector. Analyze the following project event data and identify any signals that warrant tracking.

PROJECT CONTEXT:
Project ID: {{project_id}}

ACTIVE SIGNALS (for context, do not duplicate):
{{active_signals}}

EVENT DATA:
{{event_data}}

ALLOWED SIGNAL TYPES for this source:
- status_change: Status transitions on RFIs, submittals, change orders
- timeline: Date-related concerns, schedule impacts, deadline approaches
- document_significance: Notable document events (new revision, key submittal)
- reinforcement: Event confirms an existing signal pattern

DO NOT generate signals of these types (reserved for synthesis):
- contradiction
- actor_pattern
- cross_project

Analyze the event data. If it contains a notable signal, return a JSON object. If the event is routine with no signal value, return {"signals": []}.

Return ONLY valid JSON in this format:
{
    "signals": [
        {
            "signal_type": "string",
            "signal_category": "status_change|timeline|document_significance|reinforcement",
            "summary": "Brief description of what was detected",
            "confidence": 0.0-1.0,
            "strength": 0.0-1.0,
            "decay_profile": "fast_24h|medium_72h|slow_7d|persistent",
            "entity_type": "rfi|submittal|daily_report|drawing|change_order|meeting|other",
            "entity_value": "Entity identifier"
        }
    ],
    "reinforcement_candidates": [
        {
            "target_signal_id": "UUID of existing signal this event reinforces",
            "reason": "Why this event reinforces the existing signal",
            "confidence": 0.5-0.7
        }
    ]
}"""

    @staticmethod
    def _get_active_signal_summary(project_id: str, limit: int = 50) -> str:
        """Build summary of active signals for LLM context."""
        with get_cursor() as cur:
            cur.execute("""
                SELECT id, signal_type, signal_category, summary, effective_weight,
                       entity_type, entity_value, created_at
                FROM signals
                WHERE project_id = %s
                  AND archived_at IS NULL
                  AND resolved_at IS NULL
                ORDER BY effective_weight DESC
                LIMIT %s
            """, (project_id, limit))

            signals = cur.fetchall()
            if not signals:
                return "No active signals."

            lines = []
            for s in signals:
                lines.append(
                    f"- [{s['signal_category']}] {s['signal_type']}: {s['summary']} "
                    f"(weight={s['effective_weight']}, entity={s['entity_type']}:{s['entity_value']})"
                )
            return "\n".join(lines)

    @staticmethod
    def _call_ollama(prompt: str) -> Optional[str]:
        """Call local Ollama LLM."""
        import httpx

        try:
            response = httpx.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1024,
                    },
                },
                timeout=120.0,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return None

    @staticmethod
    def _parse_llm_response(response_text: str) -> Optional[Dict]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        if not response_text:
            return None

        text = response_text.strip()
        # Strip markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse LLM response as JSON: {text[:200]}")
            return None

    @classmethod
    def evaluate_webhook_event(cls, event_data: Dict, project_id: str) -> List[str]:
        """Process a webhook event through LLM-based signal detection.

        Returns list of signal IDs created.
        """
        active_summary = cls._get_active_signal_summary(project_id)

        prompt = cls.SIGNAL_PROMPT_TEMPLATE.replace(
            "{{project_id}}", project_id
        ).replace(
            "{{active_signals}}", active_summary
        ).replace(
            "{{event_data}}", json.dumps(event_data, indent=2, default=str)
        )

        response_text = cls._call_ollama(prompt)
        if not response_text:
            logger.warning(f"No LLM response for webhook event in project {project_id}")
            return []

        parsed = cls._parse_llm_response(response_text)
        if not parsed:
            return []

        signal_ids = []

        # Process signals
        for sig in parsed.get("signals", []):
            try:
                sid = SignalWriter.write(
                    project_id=project_id,
                    source_type="procore_webhook",
                    signal_type=sig.get("signal_type", "unknown"),
                    signal_category=sig.get("signal_category", "status_change"),
                    summary=sig.get("summary", ""),
                    confidence=float(sig.get("confidence", 0.6)),
                    strength=float(sig.get("strength", 0.7)),
                    decay_profile=sig.get("decay_profile", "medium_72h"),
                    entity_type=sig.get("entity_type"),
                    entity_value=sig.get("entity_value"),
                    supporting_context=event_data,
                )
                if sid:
                    signal_ids.append(sid)
            except Exception as e:
                logger.error(f"Failed to write LLM signal: {e}", exc_info=True)

        # Process reinforcement candidates
        for candidate in parsed.get("reinforcement_candidates", []):
            try:
                _write_reinforcement_candidate(
                    project_id=project_id,
                    target_signal_id=candidate.get("target_signal_id"),
                    source_signal_ids=signal_ids,
                    reason=candidate.get("reason", ""),
                    confidence=float(candidate.get("confidence", 0.5)),
                )
            except Exception as e:
                logger.error(f"Failed to write reinforcement candidate: {e}", exc_info=True)

        return signal_ids

    @classmethod
    def evaluate_document(
        cls,
        classification_data: Dict,
        extraction_data: Dict,
        project_id: str,
        signal_hints: Optional[Dict] = None,
    ) -> List[str]:
        """Process a document classification through signal detection.

        If signal_hints are provided (from classifier), use them directly
        instead of calling the LLM again.
        """
        signal_ids = []

        # Compute source_multiplier from project match confidence
        # Low-confidence matches get reduced weight
        project_match_confidence = float(classification_data.get("project_match_confidence", 1.0))
        source_multiplier = 1.0 if project_match_confidence >= 0.8 else project_match_confidence

        # If signal_hints present, write directly (no LLM call needed)
        if signal_hints:
            for hint in signal_hints.get("signals", []):
                try:
                    sid = SignalWriter.write(
                        project_id=project_id,
                        source_type="document_pipeline",
                        signal_type=hint.get("signal_type", "document_significance"),
                        signal_category=hint.get("signal_category", "document_significance"),
                        summary=hint.get("summary", ""),
                        confidence=float(hint.get("confidence", 0.7)),
                        strength=float(hint.get("strength", 0.7)),
                        decay_profile=hint.get("decay_profile", "medium_72h"),
                        entity_type=hint.get("entity_type", "document"),
                        entity_value=hint.get("entity_value"),
                        source_document_id=classification_data.get("document_id"),
                        supporting_context={
                            "document_class": classification_data.get("document_class"),
                            "workflow_status": classification_data.get("workflow_status"),
                        },
                        source_multiplier=source_multiplier,
                    )
                    if sid:
                        signal_ids.append(sid)
                except Exception as e:
                    logger.error(f"Failed to write signal from hint: {e}", exc_info=True)
            return signal_ids

        # No hints — fall back to LLM evaluation
        event_data = {
            "source": "document_pipeline",
            "classification": classification_data,
            "extraction_summary": {
                k: v for k, v in extraction_data.items()
                if k in ("title", "summary", "key_findings", "document_class")
            },
        }
        return cls.evaluate_webhook_event(event_data, project_id)


def refire_signals_for_document(
    document_id: str,
    confirmed_project_id: str,
    classification_data: Dict,
    extraction_data: Optional[Dict] = None,
) -> Dict:
    """CC-2.4: Re-fire signal generation after PM confirms project assignment.

    1. Archive any prior signals for this document (they had low confidence)
    2. Re-run evaluation with confirmed project_id and full source_multiplier
    """
    archived = 0
    with get_cursor() as cur:
        # Archive prior low-confidence signals for this document
        cur.execute("""
            UPDATE signals SET archived_at = NOW()
            WHERE source_document_id = %s
              AND archived_at IS NULL
        """, (document_id,))
        archived = cur.rowcount

    # Re-run with confirmed project and full confidence
    classification_data["project_match_confidence"] = 1.0
    signal_ids = SignalGenerationService.evaluate_document(
        classification_data=classification_data,
        extraction_data=extraction_data or {},
        project_id=confirmed_project_id,
    )

    logger.info(
        f"Refire for document {document_id}: archived {archived} old signals, "
        f"generated {len(signal_ids)} new signals for project {confirmed_project_id}"
    )
    return {
        "document_id": document_id,
        "project_id": confirmed_project_id,
        "archived_old_signals": archived,
        "new_signal_ids": signal_ids,
    }


def _write_reinforcement_candidate(
    project_id: str,
    target_signal_id: str,
    source_signal_ids: List[str],
    reason: str,
    confidence: float,
):
    """Write a reinforcement candidate to the reinforcement_candidates table."""
    if not target_signal_id or not source_signal_ids:
        return

    with get_cursor() as cur:
        # Verify target signal exists
        cur.execute("SELECT id FROM signals WHERE id = %s", (target_signal_id,))
        if not cur.fetchone():
            logger.warning(f"Reinforcement target signal {target_signal_id} not found")
            return

        for source_id in source_signal_ids:
            cur.execute("""
                INSERT INTO reinforcement_candidates
                    (id, target_signal_id, source_signal_id, reason, confidence)
                VALUES (%s, %s, %s, %s, %s)
            """, (str(uuid4()), target_signal_id, source_id, reason, confidence))

        logger.info(
            f"Reinforcement candidate written: target={target_signal_id}, "
            f"sources={source_signal_ids}, confidence={confidence}"
        )
