# Change Events & Financial Management API
> Status: **PARTIALLY EXPLORED** — Module limitations in sandbox
> Tested: 2026-02-19

## Summary

The Change Events module appears to be **not enabled** for this sandbox project. Most standard endpoints return 404. However, several financial/budget-adjacent endpoints DO work and are documented below.

---

## Working Endpoints

### Cost Codes
```
GET /rest/v1.0/cost_codes?project_id=316469&company_id=4281379
```

**Returns:** 304 cost codes for the project

**Fields:**
```json
{
  "id": 11747411,
  "name": "General Requirements",
  "full_code": "01",
  "code": "01",
  "origin_id": null,
  "origin_data": null,
  "standard_cost_code_id": null,
  "biller": "Sandbox Test Project",
  "biller_id": 316469,
  "biller_type": "Project",
  "biller_origin_id": null,
  "budgeted": false,
  "parent": {"id": null},
  "sortable_code": "01",
  "line_item_types": [],
  "created_at": "2026-02-17T01:15:28Z",
  "deleted_at": null,
  "position": null,
  "updated_at": "2026-02-17T01:15:28Z"
}
```

**Key notes:**
- `biller_type`: "Project" (project-level codes) or "Company" (company-level)
- `budgeted`: Whether this code has budget allocated
- `line_item_types`: Array of line item types linked to this code
- Hierarchical via `parent.id`

---

### Line Item Types
```
GET /rest/v1.0/line_item_types?project_id=316469&company_id=4281379
```

**Returns:** 7 line item types

```json
[
  {"id": 3522609, "base_type": "labor",     "code": "L", "name": "Labor"},
  {"id": 3522610, "base_type": "material",  "code": "M", "name": "Materials"},
  {"id": 3522611, "base_type": "equipment", "code": "E", "name": "Equipment"},
  {"id": 3522612, "base_type": "other",     "code": "O", "name": "Other"},
  {"id": 3522613, "base_type": "subcontract","code":"S", "name": "Subcontract"},
  {"id": 3522614, "base_type": "overhead",  "code": "OH","name": "Overhead"},
  {"id": 3522615, "base_type": "markup",    "code": "MU","name": "Markup"}
]
```

**Fields:** `id`, `base_type`, `code`, `name`, `origin_data`, `origin_id`

---

### Budget Status
```
GET /rest/v1.0/projects/{project_id}/budget
```

**Returns:** `{"locked": false}`

Simple endpoint to check if budget is locked. When locked, no modifications allowed.

---

### Budget Modifications
```
GET /rest/v1.0/projects/{project_id}/budget_modifications
```

Returns 0 records in sandbox but endpoint is active. Fields unknown (no data to inspect).

---

### Commitment Change Orders
```
GET /rest/v1.0/projects/{project_id}/commitment_change_orders
```

Returns 0 records in sandbox. This tracks changes to subcontracts/commitments.

---

### Prime Contracts
```
GET /rest/v1.0/prime_contracts?project_id={id}&company_id={id}
```

Returns 0 records in sandbox. Prime contract is the owner-GC contract.

---

## 404 Endpoints (Module Not Enabled)

These all return 404 in this sandbox:

| Endpoint | Expected Purpose |
|---|---|
| `/rest/v1.0/projects/{id}/change_events` | Change Event log |
| `/rest/v1.1/projects/{id}/change_events` | Change Events v1.1 |
| `/rest/v1.0/projects/{id}/change_order_packages` | PCO packages |
| `/rest/v1.0/projects/{id}/prime_contract_change_orders` | Prime CO |
| `/rest/v1.0/projects/{id}/potential_change_orders` | PCOs |
| `/rest/v1.0/projects/{id}/change_order_requests` | COR |
| `/rest/v1.0/projects/{id}/budget_line_items` | Budget lines |
| `/rest/v1.0/projects/{id}/cost_codes` | Project cost codes (use flat endpoint) |
| `/rest/v1.0/companies/{id}/cost_codes` | Company cost codes |
| `/rest/v1.0/projects/{id}/commitments` | Subcontracts |
| `/rest/v1.0/projects/{id}/subcontracts` | Subcontracts |
| `/rest/v1.0/projects/{id}/purchase_orders` | POs |

---

## Expected Schema (When Module Enabled)

Based on Procore's API documentation and typical patterns:

### Change Event
```json
{
  "id": 12345,
  "number": "CE-001",
  "title": "Owner-requested scope addition",
  "status": "pending",
  "event_type": "Owner Requested Change",
  "reason": "Scope Addition",
  "description": "Add concrete sidewalk on north side",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-20T14:30:00Z",
  "created_by": {"id": 174986, "name": "Nick Stula"},
  "cost_codes": [{"id": 11747411, "code": "01", "name": "General Requirements"}],
  "line_items": [],
  "rfis": [],
  "potential_change_orders": []
}
```

---

## How to Enable Change Events

To enable the Change Events module in Procore:
1. Project Settings → Modules → Change Management
2. Enable "Change Events" module
3. Configure: approval workflow, numbering, types

This is a project-level setting, not API-controllable.

---

## EVA Integration Plan

### What's Available Now:
1. **Cost codes** — Store the 304 codes for cross-referencing with daily logs
2. **Line item types** — 7 types (Labor, Materials, Equipment, Other, Subcontract, Overhead, Markup)
3. **Budget locked status** — Check before any budget write operations

### When Change Events Module Enabled:
```python
# Full change event sync
change_events = paginate('/rest/v1.0/projects/{id}/change_events')
for ce in change_events:
    # Cross-reference with RFIs: ce['rfis']
    # Link to cost codes: ce['cost_codes']
    # Track PCOs: ce['potential_change_orders']
```

### Cost Code Sync (Works Now)
```python
# Get all 304 cost codes
cost_codes = api.get('/rest/v1.0/cost_codes', 
                     params={'project_id': PROJECT_ID}).json()
# Store for lookup when processing daily log entries
```
