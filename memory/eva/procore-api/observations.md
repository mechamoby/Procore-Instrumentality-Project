# Observations API
> Status: **PARTIALLY EXPLORED** — Read works, Write blocked
> Tested: 2026-02-19

## Overview

Observations are quality/safety issues logged on site. The module is enabled (GET returns 200) but creating observations returns 404, suggesting a permissions or module configuration issue.

---

## Working Endpoints

### List Observations
```
GET /rest/v1.0/projects/{project_id}/observations/items
?company_id=4281379
&per_page=100
```

**Status:** Returns 200, 0 records in sandbox (module enabled but no data)

**Expected fields based on observation types and Procore patterns:**
```
id, type_id, type (obj), name, status, priority, trade, assignees,
description, location, due_date, resolved_at, created_at, updated_at,
created_by, attachments, custom_fields
```

---

### Observation Types
```
GET /rest/v1.0/observations/types
?project_id=316469
&company_id=4281379
```

OR equivalently:
```
GET /rest/v1.0/projects/{project_id}/observation_types
?company_id=4281379
```

**Returns:** 22 observation types

**Fields:**
```json
{
  "id": 10804239,
  "name": "Deficiency",
  "localized_name": "Deficiency",
  "category": "Quality",
  "category_key": "quality",
  "company_active": true,
  "active": true,
  "kind": "company",
  "parent_inactive": false,
  "in_use": false,
  "name_translations": null,
  "observations_category": {
    "id": 631933,
    "name": "quality",
    "grouping": null,
    "updated_at": "2026-02-17T01:15:02Z"
  }
}
```

---

### All 22 Observation Types in Sandbox

| Category | Types |
|---|---|
| **Quality** | Deficiency |
| **Commissioning** | Commissioning |
| **Environmental** | Air Quality, Cultural Heritage, Hazardous Materials, Noise, Vibration |
| **Safety** | Electrical, Emergency Management, Ergonomics, Fall Protection, Fire Safety, First Aid, General Safety, Heavy Equipment, Material Storage, PPE, Work Zones |
| **Compliance** | (various compliance types) |

---

## 404 Endpoints (Permission/Config Issue)

| Endpoint | Status | Note |
|---|---|---|
| `POST /rest/v1.0/projects/{id}/observations/items` | 404 | Can't create |
| `GET /rest/v1.0/projects/{id}/observations` | 404 | Wrong path |
| `GET /rest/v1.1/projects/{id}/observations` | 404 | Wrong path |
| `GET /rest/v1.0/projects/{id}/observation_items` | 404 | Wrong path |

**Correct listing path:** `/rest/v1.0/projects/{id}/observations/items` (nested `items`)

---

## Create Observation (When Fixed)

The POST body structure is expected to be:
```json
{
  "observation": {
    "type_id": 10804239,
    "name": "Missing guardrail on east scaffolding",
    "status": "initiated",
    "priority": "high",
    "description": "Guardrail missing on east side of scaffold level 3",
    "due_date": "2026-02-21",
    "trade": {"id": 12345},
    "location": null,
    "assignees": [{"id": 174986}]
  }
}
```

**Status values (expected):** `initiated`, `ready_for_review`, `closed`, `not_accepted`

---

## Status Workflow

```
initiated → ready_for_review → closed
                ↓
           not_accepted → initiated (cycle back)
```

---

## Integration Opportunities

### Daily Log ↔ Observation Linking
When an accident or safety violation is logged in daily logs, EVA should:
1. Auto-suggest creating a Safety observation
2. Link the observation ID back to the daily log record
3. Track resolution timeline

### Photo Analysis
Inspections and quality walks often generate photos. EVA can:
1. Receive photos via webhook when observation created
2. AI-analyze for additional deficiencies
3. Suggest observation type based on image content

---

## EVA Integration Plan

### Sync Strategy
```python
# List all observations (when data exists)
observations = paginate('/rest/v1.0/projects/{id}/observations/items')

# Create observation (when POST fixed)
new_obs = api.post('/rest/v1.0/projects/{id}/observations/items', {
    'observation': {
        'type_id': type_id,
        'name': name,
        'status': 'initiated',
        'priority': priority
    }
})
```

### Cross-References
- `type_id` → Observation types (pre-load 22 types)
- Link to daily log `accident_log` or `safety_violation_log` entries
- Link to `checklist/lists` inspection items that failed

---

## Known Limitations

| Issue | Impact |
|---|---|
| POST returns 404 | Can't create observations via API (permissions?) |
| 0 records in sandbox | No sample data to inspect field schema |
| Correct base path is `/observations/items` not `/observations` | Easy to get wrong |
| Type IDs are company-specific | Must fetch types fresh for each company |
