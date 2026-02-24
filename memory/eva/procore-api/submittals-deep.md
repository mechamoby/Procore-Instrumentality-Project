# Submittals API — Deep Dive
> Status: **FULLY EXPLORED** — 146 submittals in sandbox
> Tested: 2026-02-19

## Overview

Submittals are one of the most complete Procore APIs we've tested. The sandbox has 146 submittals from the BTV5 project import. Full CRUD is available. Key limitations: workflow/approver management not possible via API, and file attachments silently drop.

---

## Endpoints

### List Submittals
```
GET /rest/v1.0/projects/{project_id}/submittals
?company_id=4281379
&per_page=100
&page=1
```

**Pagination:** Standard Link header + `total` header
**Total in sandbox:** 146

---

### Get Single Submittal
```
GET /rest/v1.0/projects/{project_id}/submittals/{submittal_id}
```

Same fields as list (no additional fields in detail view for submittals).

---

### Create Submittal
```
POST /rest/v1.0/projects/{project_id}/submittals
```

```json
{
  "submittal": {
    "title": "Concrete Mix Design",
    "number": "03-0001",
    "revision": "0",
    "specification_section_id": 77,
    "type_id": 66509,
    "received_from_id": 100298,
    "submittal_manager_id": 99519,
    "issue_date": "2026-02-19",
    "received_date": "2026-02-18",
    "submit_by": "2026-03-01",
    "required_on_site_date": "2026-04-01",
    "private": false,
    "for_record_only": false
  }
}
```

---

### Update Submittal
```
PATCH /rest/v1.0/projects/{project_id}/submittals/{submittal_id}
```

---

## Complete Field Inventory

```
approvers                     Array of approver objects
attachments_count             int — number of attachments (not attachment objects)
ball_in_court                 Array of {id, name, locale, login} — who has it
buffer_time                   int or null — days buffer added to workflow
closed_at                     ISO timestamp or null
created_at                    ISO timestamp
created_by                    {id, name, locale, login}
current_revision              bool
custom_fields                 obj — project-defined custom fields
distributed_at                ISO timestamp or null
due_date                      YYYY-MM-DD or null
for_record_only               bool
formatted_number              String — e.g., "033000-16-0502-1" (spec-number-revision)
id                            int
is_rejected                   bool
issue_date                    YYYY-MM-DD or null
location                      Location obj or null
number                        String — submittal number within spec section
open_date                     YYYY-MM-DD or null — when opened for review
operation_item_errors         Array — any workflow errors
private                       bool
received_date                 YYYY-MM-DD or null
received_from                 {id, name, locale, login} — who submitted
rejected_submittal_log_approver_id  int or null
required_on_site_date         YYYY-MM-DD or null
responsible_contractor        {id, name, login} or null
revision                      String — "0", "1", "A", etc.
scheduled_task                Schedule task obj or null
specification_section         Full spec section obj (see below)
status                        String — see status values
sub_job                       Sub-job obj or null
submit_by                     YYYY-MM-DD or null — deadline to submit
submittal_manager             {id, name, locale, login}
submittal_package             Package obj or null
submittal_workflow_template   Workflow template obj or null
submittal_workflow_template_applied_at  ISO timestamp or null
title                         String
type                          {id, name, translated_name} — submittal type
updated_at                    ISO timestamp
```

---

## Specification Section Object

```json
{
  "id": 77,
  "current_revision_id": 78,
  "description": "CAST-IN-PLACE CONCRETE",
  "label": "033000 - CAST-IN-PLACE CONCRETE",
  "number": "033000",
  "specification_area_id": null,
  "specification_area_name": null,
  "viewable_document_id": 456
}
```

---

## Status Values

| Status | Meaning |
|---|---|
| `pending` | Awaiting action (default) |
| `approved` | Approved, no revisions needed |
| `approved_as_noted` | Approved with comments/revisions |
| `revise_and_resubmit` | Must be resubmitted with changes |
| `rejected` | Rejected |
| `void` | Void/cancelled |
| `closed` | Closed/complete |

**Note:** `filters[status]` parameter doesn't appear to filter correctly — returned same 146 records regardless of status value. Bug or different param format needed.

---

## Submittal Type Object

```json
{
  "id": 66509,
  "name": "Shop Drawing",
  "translated_name": "Shop Drawing"
}
```

**Common types:** Shop Drawing, Product Data, Samples, Warranties, O&M Manuals, Calculations, RFI Response, Coordination Drawing

---

## Working Queries

### Get by specification section
```
GET /rest/v1.0/projects/{id}/submittals
?filters[specification_section_id]=77
```

### Get all for current revision only
```
GET /rest/v1.0/projects/{id}/submittals
?filters[current_revision]=true
```

### Get all awaiting action
```
GET /rest/v1.0/projects/{id}/submittals
?filters[ball_in_court_id]={user_id}
```

---

## Known Limitations

| Limitation | Detail |
|---|---|
| No workflow/approver management | Can't add approvers or change workflow via API |
| No submittal_types endpoint | Types are preconfigured; can't list via API |
| No submittal_statuses endpoint | Status values must be hardcoded |
| No submittal_workflow_templates endpoint | Templates set up in UI only |
| File attachments silently fail | API returns 200 but file isn't attached |
| API-created users can't be managers/reviewers | Only built-in sandbox users work |
| `attachments_count` not attachment objects | Must use separate calls for actual files |
| Status filter doesn't work as expected | Returns all 146 regardless of filter |

---

## Submittal Packages
```
GET /rest/v1.0/projects/{project_id}/submittal_packages
```

Returns 0 records in sandbox. Packages group multiple submittals into a single transmittal.

---

## EVA Integration Plan

### Full Sync
```python
def sync_submittals(project_id):
    submittals = []
    page = 1
    while True:
        r = api.get(f'/rest/v1.0/projects/{project_id}/submittals',
                    params={'page': page, 'per_page': 100})
        batch = r.json()
        submittals.extend(batch)
        total = int(r.headers.get('total', 0))
        if len(submittals) >= total or not batch:
            break
        page += 1
    return submittals
```

### Key Cross-References
- `specification_section.id` → Link to RFIs with same spec section
- `responsible_contractor.id` → Vendor/subcontractor records
- `submittal_manager.id` → Project user responsible
- `ball_in_court` → Who needs to take action NOW
- `required_on_site_date` → Schedule integration (material delivery)
- `submit_by` → Deadline tracking and alerts

### EVA Automation Opportunities
1. **Due date alerts** — Notify when `submit_by` approaching
2. **Ball-in-court tracking** — Who is holding up submittals?
3. **Spec section cross-ref** — When RFI opened for same spec section, auto-link
4. **Status trend analysis** — Track approval/rejection rates by trade
5. **Cover sheet** — Generate PDF summary of all submittals by status
