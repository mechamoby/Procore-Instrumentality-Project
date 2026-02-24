# Punch Lists API
> Status: **NOT FOUND** — Module not enabled or incorrect paths
> Tested: 2026-02-19

## Summary

Despite extensive testing, no punch list endpoint was found. All attempted paths return 404. This indicates the Punch List module is likely not enabled for this sandbox project, or Procore uses a very different URL structure than expected.

---

## All Attempted Paths (All 404)

```
GET /rest/v1.0/projects/316469/punch_list_items
GET /rest/v1.1/projects/316469/punch_list_items
GET /rest/v2.0/projects/316469/punch_list_items
GET /rest/v1.0/projects/316469/punch_items
GET /rest/v1.0/projects/316469/punch_lists
GET /rest/v1.0/projects/316469/punch_list
GET /rest/v1.1/projects/316469/punch_list
GET /rest/v1.0/projects/316469/punch_list/items
GET /rest/v1.1/projects/316469/punch_list/items
GET /rest/v1.0/projects/316469/checklists
GET /rest/v1.0/projects/316469/checklist/punch_items
GET /rest/v1.0/projects/316469/checklist/items
GET /rest/v1.0/projects/316469/deficiency_items
GET /rest/v1.0/companies/4281379/punch_list_items
GET /vapid/projects/316469/punch_list_items
```

---

## Possible Reasons

1. **Module not enabled:** Punch List is a separate Procore module that may not be active for Project 316469
2. **Wrong URL pattern:** Procore sometimes uses unexpected nesting
3. **Requires separate company-level enablement:** May need admin to enable in project settings

---

## Expected Schema (Based on Procore Documentation)

When enabled, punch list items typically look like:

```json
{
  "id": 12345,
  "number": "PL-001",
  "title": "Missing light fixture in unit 204",
  "description": "The ceiling light fixture is missing in bedroom 1 of unit 204",
  "status": "open",
  "priority": "high",
  "due_date": "2026-03-01",
  "location": "Unit 204, Bedroom 1",
  "assignees": [
    {"id": 100298, "name": "Test Subcontractor"}
  ],
  "trade": {"id": 45678, "name": "Electrical"},
  "cost_code": {"id": 11747411, "code": "16", "name": "Electrical"},
  "created_by": {"id": 174986, "name": "Nick Stula"},
  "created_at": "2026-02-19T10:00:00Z",
  "updated_at": "2026-02-19T10:00:00Z",
  "closed_at": null,
  "attachments": [],
  "checklist_list_id": null,
  "inspection_id": null,
  "rfi_id": null
}
```

**Status values (expected):** `open`, `in_progress`, `resolved`, `closed`, `not_applicable`

---

## Connection to Checklists/Inspections

Procore punch lists are closely related to the **Checklist (Inspections)** module. Failed checklist items can often be promoted to punch list items. The working checklist endpoints are:

```
GET /rest/v1.0/projects/{id}/checklist/list_templates  ✅
GET /rest/v1.0/projects/{id}/checklist/lists            ✅
```

If the punch list module gets enabled, check for:
```
GET /rest/v1.0/projects/{id}/checklist/lists/{id}/items
```

---

## Action Items

1. **Enable punch list module** in Project 316469 settings (requires UI access)
2. Once enabled, test: `GET /rest/v1.0/projects/{id}/punch_list_items`
3. Alternatively, use the **Checklist/Inspections** module as a proxy for punch list tracking

---

## Alternative: Use Observations Module

The Observations module (`/rest/v1.0/projects/{id}/observations/items`) appears to serve a similar function to punch lists — tracking deficiencies, safety items, and quality issues. This is our best current alternative.

See `observations.md` for details.
