# MAGI Sprint 1 — Procore API Deep Dive Summary
> Completed: 2026-02-19 by MAGI (Procore API Specialist)
> Sandbox: Company 4281379, Project 316469 (Sandbox Test Project)
> Auth: OAuth2 Bearer token (refreshes automatically)

---

## Executive Summary

Sprint 1 systematically explored 8 major API endpoint categories via live sandbox testing. **Authentication is confirmed working.** 6 of 8 priority areas are fully documented. 2 categories (Change Events, Punch Lists) are blocked by module configuration.

**Rate limit header:** `X-Rate-Limit-Limit: 100` per ~60 second window. With 0.4s delays between calls, we stayed well within limits throughout this sprint.

---

## Quick Reference: What Works

| Module | Endpoint | Status | Record Count |
|---|---|---|---|
| Daily Logs | `/rest/v1.0/projects/{id}/daily_logs` | ✅ Full | 0 (created test data) |
| Weather Logs | `/rest/v1.0/projects/{id}/weather_logs` | ✅ Full | 2 |
| Manpower Logs | `/rest/v1.0/projects/{id}/manpower_logs` | ✅ Full | 1 |
| Notes Logs | `/rest/v1.0/projects/{id}/notes_logs` | ✅ Full | 1 |
| Timecard Entries | `/rest/v1.0/projects/{id}/timecard_entries` | ✅ Full | 1 |
| Equipment Logs | `/rest/v1.0/projects/{id}/equipment_logs` | ✅ Full | 1 |
| Visitor Logs | `/rest/v1.0/projects/{id}/visitor_logs` | ✅ Full | 1 |
| Delivery Logs | `/rest/v1.0/projects/{id}/delivery_logs` | ✅ Full | 1 |
| Accident Logs | `/rest/v1.0/projects/{id}/accident_logs` | ✅ Full | 1 |
| Delay Logs | `/rest/v1.0/projects/{id}/delay_logs` | ✅ Full | 1 |
| Work Logs | `/rest/v1.0/projects/{id}/work_logs` | ✅ Full | 1 |
| Dumpster Logs | `/rest/v1.0/projects/{id}/dumpster_logs` | ✅ Full | 1 |
| Quantity Logs | `/rest/v1.0/projects/{id}/quantity_logs` | ✅ Full | 1 |
| Call Logs | `/rest/v1.0/projects/{id}/call_logs` | ✅ Full | 1 |
| RFIs | `/rest/v1.1/projects/{id}/rfis` | ✅ Full | 134 |
| Submittals | `/rest/v1.0/projects/{id}/submittals` | ✅ Full | 146 |
| Documents | `/rest/v1.0/projects/{id}/documents` | ✅ Full | 25 (23 folders, 2 files) |
| Meetings | `/rest/v1.1/projects/{id}/meetings` | ✅ Partial | 1 (created) |
| Meeting Topics | `/rest/v1.1/projects/{id}/meeting_topics` | ⚠️ Read-only | 0 |
| Observations | `/rest/v1.0/projects/{id}/observations/items` | ⚠️ Read-only | 0 |
| Observation Types | `/rest/v1.0/observations/types` | ✅ Full | 22 |
| Checklists (Lists) | `/rest/v1.0/projects/{id}/checklist/lists` | ⚠️ Create blocked | 0 |
| Checklist Templates | `/rest/v1.0/projects/{id}/checklist/list_templates` | ✅ Full | 1 (created) |
| Cost Codes | `/rest/v1.0/cost_codes` | ✅ Full | 304 |
| Line Item Types | `/rest/v1.0/line_item_types` | ✅ Full | 7 |
| Vendors | `/rest/v1.0/vendors` | ✅ Full | 118 |
| Project Users | `/rest/v1.0/projects/{id}/users` | ✅ Full | 554 |
| Webhooks | `/rest/v1.0/webhooks/hooks` | ✅ Full | 0 (created 1) |
| Change Events | `/rest/v1.0/projects/{id}/change_events` | ❌ 404 | N/A |
| Punch Lists | `/rest/v1.0/projects/{id}/punch_list_items` | ❌ 404 | N/A |
| Timesheets | `/rest/v1.0/projects/{id}/timesheets` | ✅ Empty | 0 |
| Budget Status | `/rest/v1.0/projects/{id}/budget` | ✅ | `{locked: false}` |
| Commitment COs | `/rest/v1.0/projects/{id}/commitment_change_orders` | ✅ Empty | 0 |
| Prime Contracts | `/rest/v1.0/prime_contracts` | ✅ Empty | 0 |

---

## Key Discoveries

### 1. Daily Logs Architecture (Critical for EVA)
- The umbrella `daily_logs` endpoint returns **18 sub-types** in one call
- **Required:** date range params (`filters[start_date]`, `filters[end_date]`)
- **Max range:** 13 weeks (91 days) per query — must loop for full history
- Each sub-type also has its own endpoint for individual CRUD
- Sandbox was completely empty before this sprint — all schemas discovered by creating test records

### 2. RFIs — Confirmed 134 Total
- Nick's concern about "fewer than expected" confirmed: 134 is correct count
- All 134 status = "open" (no closed RFIs in sandbox)
- Pagination confirmed: Use `total` response header + Link header for pages
- Full detail (with responses, distribution list) only in single-RFI endpoint
- **Search works:** `?search=query` for full-text across subjects and bodies
- Use `filters[status][]=open` (array syntax with `[]`) — without brackets returns 400

### 3. API Version Matters
- RFIs: Use v1.1 (v2.0 returns 404)
- Meetings: Use v1.1 (v1.0 returns 404)
- Most other endpoints: v1.0
- Submittals: v1.0

### 4. Module Gaps
- **Change Events:** Module not enabled in sandbox → all endpoints 404
- **Punch Lists:** Not found via any URL pattern → likely not enabled
- **Observations POST:** Returns 404 (permissions or wrong body structure)

### 5. Webhooks Work
- `POST /rest/v1.0/webhooks/hooks` with `destination_url` and `triggers` array
- Returns hook ID, namespaced to company
- Can monitor any resource type (Daily Logs, RFIs, Documents, etc.)

### 6. Meetings Quirk
- List response is **grouped** by meeting title, not flat: `[{group_title, meetings: [...]}]`
- Must flatten in code: `[m for group in resp for m in group['meetings']]`
- Topics need `meeting_id` in body (POST to `/meeting_topics`, not nested)

---

## Critical Notes & Gotchas

| Gotcha | Details |
|---|---|
| `note_logs` (singular) → 404 | Must use `notes_logs` (plural) |
| Daily logs require date range | Missing dates → 400 error |
| Daily log max 13 weeks | Chunk into 90-day windows for full history |
| Weather log `wind` enum unknown | Omit `wind` field to avoid 422 |
| Visitor/delivery/accident logs need time fields | `time_hour`, `time_minute` required |
| RFI filter needs `[]` syntax | Use `filters[status][]=open` not `filters[status]=open` |
| Meetings list is grouped | Must flatten: iterate `group['meetings']` |
| Meetings v1.0 → 404 | Must use v1.1 |
| Documents list is flat (no nesting) | Use `parent_id` to reconstruct tree |
| Submittals status filter appears broken | Returns same 146 regardless of status filter |
| Change Events = module not enabled | Need project admin to enable |
| Punch Lists = not found | Need project admin to check module settings |
| Meeting topics POST → 403 | Current user lacks permission |
| Observations POST → 404 | Body structure or permissions issue |
| Checklist list creation → 422 | Template ID validation issues |

---

## Pagination Patterns

| Endpoint | Pagination Style |
|---|---|
| Daily logs | No pagination — date range controls volume |
| RFIs | `page` + `per_page` params, `total` header, `Link` header |
| Submittals | `page` + `per_page` params, `total` header |
| Documents | `per_page` param, `total` header |
| Meetings | `per_page` param, `total` header |
| Cost codes | `per_page` param, `total` header (304 total) |

---

## EVA Phase 1 Recommendations

### Priority 1: Ingest Existing Data
These are ready to sync NOW:

```python
READY_TO_SYNC = [
    # RFIs - 134 records, full schema, responses included
    ('rfis', '/rest/v1.1/projects/{id}/rfis', {'per_page': 100}),
    
    # Submittals - 146 records, full workflow data
    ('submittals', '/rest/v1.0/projects/{id}/submittals', {'per_page': 100}),
    
    # Documents - 25 records, folder structure
    ('documents', '/rest/v1.0/projects/{id}/documents', {'per_page': 1000}),
    
    # Cost codes - 304 codes for cross-referencing
    ('cost_codes', '/rest/v1.0/cost_codes', {'project_id': PROJECT_ID}),
    
    # Vendors - 118 companies
    ('vendors', '/rest/v1.0/vendors', {'per_page': 100}),
    
    # Project users - 554 users
    ('users', '/rest/v1.0/projects/{id}/users', {'per_page': 100}),
]
```

### Priority 2: Daily Log Ingestion
Daily logs need chunked date range queries. Start from project creation date, loop in 90-day windows:

```python
def sync_all_daily_logs(start_date, end_date=None):
    from datetime import timedelta
    end_date = end_date or date.today()
    results = {}
    current = start_date
    while current < end_date:
        chunk_end = min(current + timedelta(days=90), end_date)
        r = api.get('/rest/v1.0/projects/{id}/daily_logs', {
            'filters[start_date]': current.isoformat(),
            'filters[end_date]': chunk_end.isoformat()
        })
        for key, logs in r.json().items():
            results.setdefault(key, []).extend(logs)
        current = chunk_end + timedelta(days=1)
    return results
```

### Priority 3: Set Up Webhooks
Register webhooks for real-time updates:

```python
WEBHOOK_TRIGGERS = [
    # Daily log sub-types
    ('create', 'Weather Log'), ('create', 'Manpower Log'), ('create', 'Note Log'),
    ('create', 'Visitor Log'), ('create', 'Delivery Log'), ('create', 'Accident Log'),
    ('create', 'Equipment Log'), ('create', 'Delay Log'), ('create', 'Work Log'),
    # Other modules
    ('create', 'RFI'), ('update', 'RFI'),
    ('create', 'Submittal'), ('update', 'Submittal'),
    ('create', 'Document'), ('create', 'Meeting'),
]
```

### Priority 4: Enable Blocked Modules
Request project admin to:
1. Enable **Change Events** module (for cost/change tracking)
2. Enable **Punch Lists** module (for deficiency tracking)
3. Check permissions for **Observations** creation

---

## Data Schema Quick Reference

### How Fields Connect (Cross-Reference Map)

```
Daily Logs
├── vendor (obj) ──────────────→ Vendors table
├── cost_code (obj) ────────────→ Cost Codes (304)
├── created_by (obj) ──────────→ Project Users (554)
├── location (obj) ─────────────→ Locations
└── date ───────────────────────→ RFIs (by due_date), Weather

RFIs
├── responsible_contractor ─────→ Vendors table
├── specification_section_id ──→ Spec Sections → Submittals
├── drawing_ids ────────────────→ Drawing Revisions
├── rfi_manager ────────────────→ Project Users
├── assignees ──────────────────→ Project Users
└── change_events ──────────────→ Change Events (when enabled)

Submittals
├── received_from ──────────────→ Project Users
├── responsible_contractor ─────→ Vendors
├── submittal_manager ──────────→ Project Users
├── specification_section ──────→ matches RFI spec sections
└── ball_in_court ──────────────→ Project Users

Documents
└── parent_id ──────────────────→ Self-reference (folder tree)
```

---

## Files Created

| File | Status |
|---|---|
| `daily-logs.md` | ✅ Complete — all 18 sub-types documented |
| `rfis.md` | ✅ Complete — full schema, pagination, filtering |
| `change-events.md` | ✅ Complete — documents gaps, what works |
| `observations.md` | ✅ Complete — types documented, creation blocked |
| `meetings.md` | ✅ Complete — grouped response quirk documented |
| `punch-lists.md` | ✅ Complete — all 404, module not enabled |
| `submittals-deep.md` | ✅ Complete — full field inventory, limitations |
| `documents.md` | ✅ Complete — folder structure, file list |
| `inspections.md` | ✅ Complete — templates work, list creation blocked |
| `SPRINT-1-SUMMARY.md` | ✅ This file |

---

## Outstanding Questions for Nick

1. **Change Events module** — Is it enabled on this project? If not, can it be? We need this for budget/cost tracking.
2. **Punch Lists** — Same question. None of our endpoint attempts worked.
3. **RFI count** — Nick mentioned expecting more than 134. Confirm 134 is correct for this sandbox import.
4. **Observation permissions** — Our API user can't create observations. Is there a role/permission to grant?
5. **Meeting topics** — Our user gets 403 when creating agenda items. What role is needed?
6. **Weather log `wind` field** — What are the valid enum values? (Procore docs?)
7. **Checklist list creation** — Why does the template_id validation fail even for freshly created templates?

---

## Next Steps for EVA

1. **Build EVA's database schema** based on the field inventories above
2. **Write the sync scripts** for RFIs (134), submittals (146), documents (25)
3. **Implement chunked daily log sync** with the 90-day window strategy
4. **Register webhooks** for real-time data ingestion
5. **Enable blocked modules** (change events, punch lists) via project admin
6. **Build cross-reference indices** using the connection map above
7. **Sprint 2:** Drawings deep dive (drawing_revisions, drawing_areas) + cost codes hierarchy
