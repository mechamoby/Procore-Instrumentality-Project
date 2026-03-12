# SteelSync Intelligence Pipeline — End-to-End Walkthrough

**Version:** 1.0 — Draft
**Date:** March 12, 2026
**Audience:** Construction executives evaluating SteelSync for pilot deployment
**Status:** Screenshot placeholders to be filled after frontend finalization

---

## What You're About to See

SteelSync monitors your Procore projects 24/7. When something changes — an RFI goes overdue, a submittal gets rejected, a subcontractor sends a contradictory email — SteelSync detects it, analyzes it in context, and surfaces only what matters.

This walkthrough follows a single event through the entire pipeline: **an RFI goes overdue, and a subcontractor emails promising a response that contradicts their track record.**

---

## Step 1: A Procore Event Fires

**What happens:** A subcontractor misses an RFI deadline. Procore marks RFI #127 as overdue and fires a webhook to SteelSync.

**Under the hood:**

The webhook lands at SteelSync's webhook receiver service (`nerv-webhook-receiver`, port 8090). The receiver:

1. Logs the raw event to the `webhook_events` table with status `pending`
2. Pulls the full RFI record from Procore's API (not just the webhook payload — the complete document with all metadata)
3. Screens the content through the security gateway for sensitive data
4. Writes the updated RFI to SteelSync's `rfis` table
5. Marks the webhook event as `completed`

At this point, the data is in the system. But data isn't intelligence — that's what comes next.

**Service:** `webhook-receiver/processor.py` → `process_event()` → `_handle_rfi()`
**Tables written:** `webhook_events`, `rfis`

---

## Step 2: Signal Detection

**What happens:** Immediately after the webhook writes to the database, SteelSync scans for anything worth flagging.

**Under the hood:**

The webhook receiver fires an async HTTP call to the intelligence engine:

```
POST /api/synthesis/sweep?project_id={project_uuid}
```

This triggers six automated detectors that scan the project data:

| Detector | What It Checks |
|----------|---------------|
| **RFIs Overdue** | Any RFI past its due date that isn't closed or answered |
| **Submittals Rejected** | Submittals rejected in the last 72 hours |
| **Submittals Overdue** | Submittals past their required date |
| **Daily Log Missing** | Whether yesterday's daily log was submitted (weekdays only) |
| **Schedule Milestones** | Milestones approaching within 14 days |
| **Change Order Status** | Change orders with status changes in the last 72 hours |

For RFI #127, the **RFIs Overdue** detector fires. It creates a **signal** — a structured record of what changed and why it matters:

```
Signal: rfis_overdue
Category: status_change
Summary: "RFI #127 (Foundation Reinforcement) is 12 days overdue —
          assigned to Marco's Concrete LLC. Originally due Feb 28."
Confidence: 0.95
```

The signal is written to the `signals` table. Before writing, the system checks for duplicates: if the same source document already generated the same signal type within the last hour, the duplicate is rejected and any new context is merged into the existing signal.

**Service:** `signal_generation.py` → `run_deterministic_sweep()` → `detect_rfis_overdue()`
**Table written:** `signals`
**Dedup logic:** `SignalWriter.write()` — checks `source_document_id` + `signal_type` + `project_id` within 1-hour window

[SCREENSHOT: Signal list in Command Center showing the newly created rfis_overdue signal with confidence score and timestamp]

---

## Step 3: The Contradiction Arrives

**What happens:** Later that morning, an email comes in from the subcontractor. SteelSync's document pipeline ingests it and generates a second signal.

**Under the hood:**

The email from Marco's Concrete LLC says: *"We will have all outstanding RFI responses to you by end of week."*

The document pipeline processes this email and creates a **document_significance** signal:

```
Signal: document_significance
Category: document_significance
Summary: "Email from Marco's Concrete LLC (Mar 11): 'We will have all
          outstanding RFI responses to you by end of week.' — contradicts
          12-day overdue status."
Confidence: 0.85
```

Now SteelSync has two signals from different sources pointing at the same subcontractor — with conflicting information. A human PM might catch this eventually. SteelSync catches it immediately.

**Service:** `signal_generation.py` → `SignalGenerationService.evaluate_document()`
**Table written:** `signals`

---

## Step 4: Synthesis — Where Intelligence Happens

**What happens:** SteelSync's synthesis engine assembles all recent signals, the current project state, and previous intelligence — then asks Claude Opus to analyze the situation like a Senior Project Manager would.

**Under the hood:**

The synthesis cycle (`SynthesisEngine.run_cycle()`) follows these steps:

**4a. Assemble the context**

The engine gathers everything Opus needs to make a judgment:

- **New signals** since the last cycle (up to 100, diversified across signal types, ranked by weight)
- **Active intelligence items** — what SteelSync has already flagged and is tracking
- **Project snapshot** — current RFI counts, submittal status, schedule milestones, daily log compliance
- **User feedback** — any items the PM has confirmed or dismissed (more on this in Step 6)
- **Radar watch items** — specific concerns the PM has asked SteelSync to monitor (Step 7)

**4b. Build the prompt**

For a morning briefing, the system prompt tells Opus:

> *"You are a Senior Project Manager reviewing overnight activity. Your job is to identify what changed, what's getting worse, what contradicts prior information, and what needs immediate attention. Do not fabricate concerns. If the data is quiet, say so."*

The prompt includes the 5-point analytical mandate:
1. What changed overnight?
2. What's getting worse?
3. Are there contradictions between what people say and what the data shows?
4. What deserves immediate attention vs. end-of-week follow-up?
5. Are there patterns across multiple signals pointing at the same issue?

**4c. Call Opus**

The assembled prompt goes to Claude Opus (`claude-opus-4-20250514`) via the Anthropic API. Opus analyzes the signals in context and returns structured JSON with its findings.

For our scenario, Opus identifies the contradiction:

> **"Marco's Concrete Promise vs Reality — RFIs Still Overdue"**
> *Email from Marco's Concrete LLC promises 'all outstanding RFI responses by end of week', but they have RFI #127 (Foundation Reinforcement) 12 days overdue and RFI #134 (Slab Thickness) 8 days overdue. Track record suggests this promise should be verified — two RFIs from the same sub, both significantly past due, with a verbal commitment but no documented action.*

This isn't a reformatted alert. It's a judgment call — the kind a good PM makes when they know the history.

**4d. Fallback**

If the Anthropic API is unavailable, the system falls back to a local algorithmic engine that groups signals by type and entity, detects obvious patterns (convergence, contradiction), and produces basic intelligence items. The output is less nuanced but keeps the pipeline running.

**Service:** `synthesis_engine.py` → `SynthesisEngine.run_cycle()`
**Model:** Claude Opus (`SYNTHESIS_MODEL` env var)
**Timeout:** 180 seconds
**Tables read:** `signals`, `intelligence_items`, `working_memory_state`, `intelligence_item_feedback`
**Tables written:** `synthesis_cycles`, `intelligence_items`, `intelligence_item_evidence`, `working_memory_state`

---

## Step 5: Intelligence Items Appear in the Command Center

**What happens:** The synthesis output becomes intelligence items — first-class objects in the Command Center that PMs see, track, and act on.

**Under the hood:**

`ItemManager.create_item()` takes each finding from Opus and writes it to the `intelligence_items` table:

| Field | Value |
|-------|-------|
| **Title** | Marco's Concrete Promise vs Reality — RFIs Still Overdue |
| **Type** | contradiction |
| **Severity** | high |
| **Confidence** | 0.85 |
| **Status** | new |
| **Attention Level** | today |
| **Evidence Count** | 3 (linked to the 3 source signals) |

Each item is linked to its source signals through the `intelligence_item_evidence` table. This creates a traceable evidence chain — you can always see exactly what data drove the finding.

**In the Command Center:**

The dashboard shows the project health card turning from yellow to red. The intelligence feed shows the new item with a severity badge, confidence score, and attention level.

[SCREENSHOT: Command Center dashboard showing project health card with red status indicator and updated intelligence item count]

[SCREENSHOT: Intelligence feed showing the "Marco's Concrete Promise vs Reality" item with HIGH severity badge, confidence score 0.85, and "today" attention level]

[SCREENSHOT: Intelligence item detail view showing the evidence chain — three linked signals (two overdue RFIs and one email) with their individual confidence scores]

**Service:** `synthesis_engine.py` → `ItemManager.create_item()`
**API endpoint:** `GET /api/projects/{project_id}/intelligence-items`
**Tables written:** `intelligence_items`, `intelligence_item_evidence`
**Frontend:** `command-center.html` → `renderIntelligenceFeed()`

---

## Step 6: PM Feedback — Confirm or Dismiss

**What happens:** The PM reviews the intelligence item and provides feedback. This feedback shapes future synthesis cycles.

**Under the hood:**

The Command Center provides two actions for each intelligence item:

- **Confirm** — "Yes, this is a real concern. Keep tracking it."
- **Dismiss** — "No, this isn't relevant." (with optional reason: false_positive, already_resolved, not_actionable, duplicate, other)

When the PM confirms the Marco's Concrete item:

```
POST /api/intelligence-items/{item_id}/feedback
{
    "feedback_type": "confirmed"
}
```

The system:
1. Records the feedback in the `intelligence_item_feedback` table
2. Boosts the item's confidence by 0.1 (0.85 → 0.95)
3. Transitions the item's status from `new` to `active`

If instead the PM dismisses it:
1. Records the feedback with the reason
2. Transitions the item to `dismissed` status
3. In the next synthesis cycle, Opus sees this feedback and avoids producing similar items unless new, strong evidence emerges

The key insight: **feedback compounds over time.** Each cycle's output is informed by every previous confirm and dismiss. SteelSync learns what matters to this PM on this project.

[SCREENSHOT: Intelligence item with confirm and dismiss buttons visible]

[SCREENSHOT: Dismiss dialog showing reason dropdown (false_positive, already_resolved, not_actionable, duplicate, other) and optional comment field]

**API endpoint:** `POST /api/intelligence-items/{item_id}/feedback`
**Table written:** `intelligence_item_feedback`
**Integration:** Feedback loaded into synthesis prompt context via `_get_dismissed_items_context()`

---

## Step 7: Radar — Directed Monitoring

**What happens:** The PM has been worried about concrete work on this project. They set up a Radar item to monitor it specifically.

**Under the hood:**

Radar is SteelSync's directed monitoring system. While the synthesis engine analyzes everything broadly, Radar lets PMs say: *"Watch this specific thing for me."*

The PM creates a Radar item:

```
POST /api/radar/items
{
    "project_id": "...",
    "title": "RFI Response Backlog Risk",
    "description": "Track the growing backlog of unanswered RFIs and
                    potential impacts on project schedule",
    "priority": "critical",
    "monitoring_scope_json": {
        "keywords": ["overdue", "response", "delay", "architect"],
        "entity_types": ["rfi"],
        "signal_categories": ["status_change", "timeline"]
    }
}
```

Every time new signals are generated, the Radar pipeline evaluates them against active Radar items using a 3-stage filter:

| Stage | Purpose | Method |
|-------|---------|--------|
| **1. Metadata** | Does the signal match the Radar item's project, entity type, and trade? | Exact match |
| **2. Keywords** | Does the signal text contain relevant keywords from the Radar item? | Keyword scoring (0.0–1.0) |
| **3. Relevance** | Is this match significant enough to flag? | Heuristic with priority weighting |

When a match is found, the system:
1. Creates a `radar_match` signal linking the Radar item to the triggering signal
2. Logs a `radar_activity` entry for the activity timeline
3. Links any relevant documents via `radar_document_links`

During synthesis, Opus also receives a **Radar Monitoring Mandate** — a section of the prompt listing all active Radar items with their monitoring scope. Opus can report back on Radar-relevant findings, which get recorded as additional Radar activity.

[SCREENSHOT: Radar panel showing the "RFI Response Backlog Risk" item with critical priority, activity count, and creation date]

[SCREENSHOT: Radar detail view showing the activity timeline — system detections and synthesis observations, with timestamps and relevance scores]

**Service:** `radar_monitor.py` → `evaluate_signals_against_radar()`
**Tables:** `radar_items`, `radar_activity`, `radar_document_links`
**API endpoints:** `POST /api/radar/items`, `GET /api/radar/items/{item_id}`
**Synthesis integration:** `build_radar_mandate()` injects Radar context into synthesis prompt

---

## The Next Cycle: It All Compounds

**What happens:** The next synthesis cycle — whether it's the midday checkpoint or the next morning briefing — sees everything that came before.

The midday checkpoint prompt includes:
- The morning briefing summary
- Any new signals since morning
- Updated intelligence items (including the confirmed Marco's Concrete item)
- Dismissed items (to avoid repeating)
- Radar activity

Opus can now say things like:

> *"Morning's concern about Marco's Concrete deepens. The PM confirmed the contradiction item, and since the morning briefing, no RFI responses have been submitted by this sub. The 'end of week' promise is now 2 business days away with no visible progress."*

This is **institutional memory at work.** Each cycle builds on the last. Patterns that develop over hours, days, or weeks get surfaced automatically — the kind of thing that falls through the cracks when a PM is juggling 5 projects.

---

## Four Synthesis Cycle Types

SteelSync runs four types of analysis throughout the day:

| Cycle | When | Focus |
|-------|------|-------|
| **Morning Briefing** | Start of day | What changed overnight? New risks? Overnight signals? |
| **Midday Checkpoint** | Midday | What's developed since morning? Any escalations? |
| **End-of-Day** | End of day | Day's full picture. What to flag for tomorrow? |
| **Escalation Review** | On demand | Deep dive into a specific intelligence item — full evidence chain analysis |

Each cycle type uses a tailored prompt template that tells Opus what to prioritize and what format to use.

---

## Technical Architecture Summary

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Procore    │────→│ Webhook Receiver │────→│  Signal Generation  │
│   Webhook    │     │   (port 8090)    │     │  6 detectors + LLM  │
└──────────────┘     └──────────────────┘     └─────────┬───────────┘
                                                        │
                                                        ▼
                     ┌──────────────────┐     ┌─────────────────────┐
                     │   Claude Opus    │←────│  Synthesis Engine   │
                     │ (Anthropic API)  │     │  4 prompt templates │
                     └────────┬─────────┘     └─────────┬───────────┘
                              │                         │
                              ▼                         ▼
                     ┌──────────────────┐     ┌─────────────────────┐
                     │  Intelligence    │     │   Radar Monitor     │
                     │  Items + Evidence│     │   3-stage pipeline  │
                     └────────┬─────────┘     └─────────────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │ Command Center   │
                     │  (port 8080)     │
                     └──────────────────┘
```

**Database:** PostgreSQL (`nerv_eva00`) with 44 tables
**Key tables:** `signals`, `intelligence_items`, `intelligence_item_evidence`, `synthesis_cycles`, `radar_items`, `radar_activity`, `intelligence_item_feedback`, `working_memory_state`
**Services:** 15 Docker containers on the `nerv-network` bridge
**Model:** Claude Opus for synthesis, deterministic detectors for signal generation

---

## What Makes This Different

SteelSync doesn't just surface data. Your existing tools already do that — Procore shows you overdue RFIs, SmartSheet shows you submittal logs.

SteelSync does what a great PM does:
- **Connects the dots** across RFIs, submittals, change orders, daily logs, and emails
- **Spots contradictions** between what people say and what the data shows
- **Remembers everything** — every cycle builds on the last, every confirmation sharpens the next output
- **Prioritizes** — not everything that changes matters, and SteelSync knows the difference

The result: you open the Command Center in the morning, and in 10 seconds you know what needs your attention today.
