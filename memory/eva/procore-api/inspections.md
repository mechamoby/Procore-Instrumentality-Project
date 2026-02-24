# Inspections & Checklists API
> Status: **PARTIALLY EXPLORED** — Template creation works, list creation has validation issues
> Tested: 2026-02-19

## Overview

Procore calls inspections "Checklists" at the API level. The module is **enabled** in our sandbox. Templates can be created. List instances (actual inspections) require a valid template_id. The sandbox started with 0 templates and 0 checklists.

---

## Endpoint Naming Convention

| Procore UI Name | API Path |
|---|---|
| Inspection Templates | `/rest/v1.0/projects/{id}/checklist/list_templates` |
| Inspections | `/rest/v1.0/projects/{id}/checklist/lists` |
| Checklist Items | Nested within lists |

**⚠️ Common mistake:** `GET /rest/v1.0/projects/{id}/checklists` → 404. Must use full nested path `/checklist/list_templates` and `/checklist/lists`.

---

## Endpoints

### List Templates
```
GET /rest/v1.0/projects/{project_id}/checklist/list_templates
?company_id=4281379
&per_page=100
```

Returns 0 in sandbox (we only created via API during this sprint).

---

### Create Template
```
POST /rest/v1.0/projects/{project_id}/checklist/list_templates
```

```json
{
  "list_template": {
    "name": "Daily Safety Inspection",
    "description": "Standard daily safety checklist",
    "inspection_type": "Safety",
    "trade": null
  }
}
```

**Returns 201:**
```json
{
  "id": 2829300,
  "name": "Test Inspection Template",
  "synced_to": null,
  "company_description": null,
  "description": "MAGI API test template",
  "created_at": "2026-02-20T00:01:17Z",
  "updated_at": "2026-02-20T00:01:17Z",
  "alternative_response_set_id": null,
  "sections": [],
  "inspection_type": null,
  "trade": null,
  "created_by": {
    "id": 174986,
    "login": "mecha.moby@gmail.com",
    "name": "Nicholas Stula"
  },
  "company_attachments": [],
  "attachments": [],
  "response_set": {
    "conforming_response": "Pass",
    "global": true,
    "deficient_response": "Fail"
  }
}
```

**Template Fields:**
| Field | Description |
|---|---|
| `id` | Template ID |
| `name` | Template name |
| `description` | Template description |
| `sections` | Array of checklist sections (nested items) |
| `inspection_type` | Type classification (null on create) |
| `trade` | Associated trade |
| `response_set` | Pass/Fail response options |
| `alternative_response_set_id` | Custom response set |
| `synced_to` | Sync source (for imported templates) |
| `company_description` | Company-level description |
| `company_attachments` | Company-level reference docs |
| `attachments` | Project-level attachments |

---

### List Inspections (Checklist Lists)
```
GET /rest/v1.0/projects/{project_id}/checklist/lists
?company_id=4281379
&per_page=100
```

Returns 0 in sandbox.

---

### Create Inspection (Checklist List)
```
POST /rest/v1.0/projects/{project_id}/checklist/lists
```

```json
{
  "list": {
    "list_template_id": 2829300,
    "name": "Daily Safety - 2026-02-20",
    "inspected_at": "2026-02-20T08:00:00Z"
  }
}
```

**Current Issue:** Returns 422 `list_template_id: invalid` even with the newly created template. Possible reasons:
- Template needs to have sections/items added first
- Template needs to be "published" to a specific state
- Permission issue with our user

---

## Expected Checklist List Schema

Based on Procore's documentation patterns:

```json
{
  "id": 12345,
  "name": "Daily Safety - 2026-02-20",
  "status": "in_progress",
  "inspected_at": "2026-02-20T08:00:00Z",
  "inspected_by": {"id": 174986, "name": "Nick Stula"},
  "list_template": {
    "id": 2829300,
    "name": "Daily Safety Inspection"
  },
  "created_at": "2026-02-20T08:00:00Z",
  "updated_at": "2026-02-20T08:00:00Z",
  "overall_result": null,
  "failure_count": 0,
  "na_count": 0,
  "passed_count": 0,
  "sections": [
    {
      "id": 67890,
      "name": "PPE",
      "items": [
        {
          "id": 111,
          "description": "All workers wearing hard hats",
          "response": "pass",
          "notes": "",
          "attachments": []
        }
      ]
    }
  ]
}
```

---

## Related Endpoint: Inspection Logs (Daily Log Sub-Type)

There's also a **daily log sub-type** called `inspection_logs` (different from full inspections):

```
GET/POST /rest/v1.0/projects/{id}/inspection_logs
```

This is a simpler record of who inspected the site that day (name, company, time). Not the same as the full Checklists module.

**Create inspection_log:**
```json
{
  "inspection_log": {
    "date": "2026-02-19",
    "description": "City inspector on site",
    "notes": "Passed framing inspection",
    "start_hour": 9,
    "start_minute": 0,
    "end_hour": 11,
    "end_minute": 30
  }
}
```

Required fields: `start_hour`, `start_minute`, `end_hour`, `end_minute`

---

## Also: Company-Level Templates

Templates can be created at the company level and shared with projects:

```
GET /rest/v1.0/checklist/list_templates
?project_id=316469
&company_id=4281379
```

This returns company-wide templates. Project-specific: use `/rest/v1.0/projects/{id}/checklist/list_templates`.

---

## EVA Integration Plan

### Template Creation Flow
```python
# 1. Create template
template = api.post(f'/rest/v1.0/projects/{id}/checklist/list_templates', {
    'list_template': {
        'name': 'Daily Safety Checklist',
        'description': 'Standard daily safety inspection'
    }
}).json()

# 2. Add sections and items to template (endpoint TBD)
# TODO: Find endpoint for adding template items

# 3. Create inspection from template
inspection = api.post(f'/rest/v1.0/projects/{id}/checklist/lists', {
    'list': {
        'list_template_id': template['id'],
        'inspected_at': '2026-02-20T08:00:00Z'
    }
}).json()
```

### EVA Use Cases
1. **Daily inspection** — Auto-create daily safety checklist each morning
2. **Failed item → Observation** — When checklist item fails, auto-create observation
3. **Trend analysis** — Track which checklist items repeatedly fail
4. **Compliance tracking** — Ensure inspections happen on schedule

---

## Action Items for Next Sprint

1. Find endpoint to add items/sections to checklist templates
2. Investigate why `list_template_id` validation fails on list creation
3. Test creating inspections via the Procore UI to see what API calls are made (browser network tab)
4. Look for `checklist/response_sets` endpoint for custom Pass/Fail/N.A. options

---

## Known Limitations

| Issue | Impact |
|---|---|
| Template section/item creation endpoint unknown | Can't build full templates via API |
| Checklist list creation (inspection instances) validation fails | Can't create inspections |
| 0 existing inspections in sandbox | No field schema from live data |
| Daily log `inspection_logs` ≠ full Inspections module | Don't confuse these |
