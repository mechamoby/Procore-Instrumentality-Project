# Daily Logs API — Deep Dive
> Status: **FULLY EXPLORED** — Live sandbox tested 2026-02-19
> Priority: **#1** — EVA's core data source

## Overview

Procore daily logs are structured as an **umbrella endpoint** that returns 18 sub-types in a single response. Each sub-type also has its own dedicated CRUD endpoint. The sandbox had zero records before this exploration — all test records were created during this sprint.

---

## Main Endpoint

### `GET /rest/v1.0/projects/{project_id}/daily_logs`

**CRITICAL:** Date range is **required** and limited to **max 13 weeks (91 days)** per request.

```
GET /rest/v1.0/projects/316469/daily_logs
?company_id=4281379
&filters[start_date]=2026-01-01
&filters[end_date]=2026-02-19
```

**Returns a dict with 18 sub-type arrays:**

| Sub-Type Key | Sub-Type Endpoint | Status |
|---|---|---|
| `weather_logs` | `/weather_logs` | ✅ Working |
| `manpower_logs` | `/manpower_logs` | ✅ Working |
| `notes_logs` | `/notes_logs` | ✅ Working (NOT `note_logs` — 404) |
| `timecard_entries` | `/timecard_entries` | ✅ Working |
| `equipment_logs` | `/equipment_logs` | ✅ Working |
| `visitor_logs` | `/visitor_logs` | ✅ Working |
| `call_logs` | `/call_logs` | ✅ Working |
| `inspection_logs` | `/inspection_logs` | ⚠️ GET works, POST requires time fields |
| `delivery_logs` | `/delivery_logs` | ✅ Working |
| `safety_violation_logs` | `/safety_violation_logs` | ⚠️ POST requires time fields |
| `accident_logs` | `/accident_logs` | ✅ Working |
| `quantity_logs` | `/quantity_logs` | ✅ Working |
| `productivity_logs` | `/productivity_logs` | ⚠️ POST requires line_item_id |
| `dumpster_logs` | `/dumpster_logs` | ✅ Working |
| `waste_logs` | `/waste_logs` | ⚠️ POST requires time fields |
| `work_logs` | `/work_logs` | ✅ Working |
| `images` | _(part of daily log)_ | Listed but upload mechanism unknown |
| `delay_logs` | `/delay_logs` | ✅ Working |

---

## Sub-Type Endpoints & Field Schemas

All sub-types share these **common fields** (plus sub-type-specific ones):
```
id, date, datetime, status, position, daily_log_segment_id, 
created_at, updated_at, deleted_at, created_by (obj), 
created_by_collaborator, attachments (arr), permissions {can_update, can_delete},
custom_fields (obj), location (null|obj), vendor (null|obj)
```

Status: Always `"approved"` when created via API.

---

### 1. Weather Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/weather_logs`

**Filter:** `?filters[start_date]=YYYY-MM-DD&filters[end_date]=YYYY-MM-DD`

**Specific fields:**
```json
{
  "id": 289882,
  "date": "2026-02-19",
  "average": "",
  "calamity": "",
  "comments": null,
  "ground": "",
  "is_weather_delay": null,
  "precipitation": "",
  "sky": "",
  "temperature": "",
  "time": "2026-02-19T15:50:00-08:00",
  "time_hour": 15,
  "time_minute": 50,
  "wind": ""
}
```

**Create body:**
```json
{
  "weather_log": {
    "date": "2026-02-19",
    "sky_condition": "clear",
    "temperature": "65",
    "precipitation": "none"
  }
}
```

**Note:** `wind` field uses enum values — empty string is valid. Specific valid values unknown (e.g. `calm`, `light_breeze` all rejected). Do not send `wind` if unsure of enum.

---

### 2. Manpower Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/manpower_logs`

**Specific fields:**
```json
{
  "id": 90963,
  "date": "2026-02-19",
  "contact": null,
  "cost_code": null,
  "man_hours": "0.0",
  "notes": null,
  "num_hours": "0.0",
  "num_workers": 0,
  "trade": null
}
```

**Create body:**
```json
{
  "manpower_log": {
    "date": "2026-02-19",
    "headcount": 12,
    "timecard_time_type": "regular"
  }
}
```

---

### 3. Notes Logs (Daily Journal)
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/notes_logs`

**⚠️ WARNING:** `note_logs` (singular) returns 404. Must use `notes_logs`.

**Specific fields:**
```json
{
  "id": 22694,
  "date": "2026-02-19",
  "comment": null,
  "daily_log_header_id": 125922,
  "is_issue_day": null
}
```

**Create body:**
```json
{
  "notes_log": {
    "date": "2026-02-19",
    "notes": "Site walkthrough completed. No issues."
  }
}
```

---

### 4. Timecard Entries
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/timecard_entries`

**Rich schema — best for labor cost tracking:**
```json
{
  "id": 1074928,
  "approval_status": "pending",
  "approved_by": null,
  "billable": null,
  "client_local_id": null,
  "clock_in_time": null,
  "clock_out_time": null,
  "company_id": 4281379,
  "completed_by": null,
  "cost_code": null,
  "cost_code_id": null,
  "crew": null,
  "crew_id": null,
  "date": "2026-02-19",
  "description": "Test timecard",
  "hours": "8.0",
  "in_progress": false,
  "injured": null,
  "line_item_type_id": 3522609,
  "location": null,
  "login_information": null,
  "lunch_start_time": null,
  "lunch_stop_time": null,
  "lunch_time": null,
  "origin_data": null,
  "origin_id": null,
  "party": null,
  "party_id": null,
  "pay_period_id": null,
  "procore_signature_id": null,
  "project_id": 316469,
  "reviewed_by": null,
  "signature": null,
  "sub_job": null,
  "sub_job_id": null,
  "time_in": null,
  "time_out": null,
  "timecard_time_type": null,
  "timecard_time_type_id": null,
  "timesheet": null,
  "timesheet_status": null,
  "wbs_code": null,
  "wbs_code_id": null,
  "work_classification": null,
  "work_classification_id": null
}
```

---

### 5. Equipment Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/equipment_logs`

**Specific fields:**
```json
{
  "id": 101033,
  "date": "2026-02-19",
  "hours_idle": null,
  "hours_operating": null,
  "inspected": null,
  "inspection_hour": null,
  "inspection_minute": null,
  "notes": null,
  "cost_code": null,
  "equipment": null,
  "equipment_register": null
}
```

**Create body:**
```json
{
  "equipment_log": {
    "date": "2026-02-19",
    "description": "Crane #1",
    "quantity": 1
  }
}
```

---

### 6. Visitor Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/visitor_logs`

**⚠️ Time fields REQUIRED:** `begin_hour`, `begin_minute`, `end_hour`, `end_minute`

```json
{
  "id": 9890,
  "date": "2026-02-19",
  "begin_hour": 9,
  "begin_minute": 0,
  "details": null,
  "end_hour": 17,
  "end_minute": 0,
  "subject": null
}
```

**Create body:**
```json
{
  "visitor_log": {
    "date": "2026-02-19",
    "name": "John Smith",
    "company": "City Building Dept",
    "begin_hour": 9,
    "begin_minute": 0,
    "end_hour": 11,
    "end_minute": 30
  }
}
```

---

### 7. Call Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/call_logs`

```json
{
  "id": 802,
  "date": "2026-02-19",
  "description": "Called owner about schedule",
  "subject_to": null,
  "subject_from": null,
  "start_hour": 0,
  "start_minute": 0,
  "end_hour": 0,
  "end_minute": 0
}
```

---

### 8. Delivery Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/delivery_logs`

**⚠️ Time fields REQUIRED:** `time_hour`, `time_minute`

```json
{
  "id": 14611,
  "date": "2026-02-19",
  "comments": null,
  "contents": null,
  "delivery_from": null,
  "time_hour": 10,
  "time_minute": 30,
  "tracking_number": null
}
```

---

### 9. Accident Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/accident_logs`

**⚠️ Time fields REQUIRED:** `time_hour`, `time_minute`

```json
{
  "id": 1047,
  "date": "2026-02-19",
  "comments": null,
  "involved_company": null,
  "involved_name": null,
  "time_hour": 14,
  "time_minute": 15
}
```

---

### 10. Quantity Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/quantity_logs`

```json
{
  "id": 1486,
  "date": "2026-02-19",
  "description": "Concrete poured",
  "quantity": 100.0,
  "unit": null,
  "cost_code": null
}
```

---

### 11. Work Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/work_logs`

```json
{
  "id": 6385,
  "date": "2026-02-19",
  "comments": null,
  "hourly_rate": null,
  "hours": 0.0,
  "reimbursable": false,
  "resource_name": null,
  "scheduled_tasks": [],
  "showed": null,
  "workers": 0
}
```

---

### 12. Delay Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/delay_logs`

```json
{
  "id": 6304,
  "date": "2026-02-19",
  "comments": null,
  "delay_type": "",
  "duration": 0.0,
  "end_time": null,
  "end_time_hour": 0,
  "end_time_minute": 0,
  "start_time_hour": 0,
  "start_time_minute": 0
}
```

---

### 13. Dumpster Logs
**Endpoint:** `GET/POST /rest/v1.0/projects/{id}/dumpster_logs`

```json
{
  "id": 509,
  "date": "2026-02-19",
  "comments": null,
  "quantity_delivered": 0,
  "quantity_removed": 0
}
```

---

## Pagination & Filtering

### Main daily_logs endpoint:
- **Required:** `filters[start_date]` and `filters[end_date]` (YYYY-MM-DD format)
- **Max range:** 13 weeks (91 days) — API returns 400 if exceeded
- **Strategy for full history:** Loop in 90-day chunks from project start to present
- No `page`/`per_page` — returns all records for the date range

### Sub-type endpoints:
- Use `filters[start_date]` and `filters[end_date]` for date range
- Using `filters[date]` (single date) returns 400 "must be a range"

---

## EVA Integration Plan

### Ingestion Strategy
```python
# Chunk date ranges to stay within 13-week limit
def fetch_all_daily_logs(project_id, project_start, end_date=None):
    end_date = end_date or date.today()
    chunks = date_range_chunks(project_start, end_date, days=90)
    all_logs = {}
    for start, end in chunks:
        r = get('/rest/v1.0/projects/{}/daily_logs'.format(project_id), {
            'filters[start_date]': start.isoformat(),
            'filters[end_date]': end.isoformat()
        })
        for key, logs in r.json().items():
            all_logs.setdefault(key, []).extend(logs)
    return all_logs
```

### Key Fields for EVA's Cross-Reference
- `date` — Link to RFIs, change events, weather on same day
- `vendor` — Link to subcontractor/company records
- `cost_code` — Link to budget line items
- `location` — Geographic cross-referencing
- `created_by` — Who logged what, when

### Webhook Events (Daily Log triggers)
Available resource names for webhooks:
- `Weather Log`, `Manpower Log`, `Equipment Log`, `Note Log`
- `Visitor Log`, `Delivery Log`, `Accident Log`, `Quantity Log`
- `Work Log`, `Delay Log`, `Dumpster Log`, `Timecard Entry`

---

## Known Limitations

| Issue | Impact |
|---|---|
| Max 13-week date range per query | Must loop in chunks for full history |
| `wind` enum values unknown | Skip or omit wind field when writing |
| `productivity_logs` requires `line_item_id` | Need budget line items first |
| `inspection_logs` requires time fields | Include `start_hour`, `start_minute`, `end_hour`, `end_minute` |
| `safety_violation_logs` requires time fields | Include `time_hour`, `time_minute` |
| `waste_logs` requires time fields | Include `time_hour`, `time_minute` |
