# Procore API Knowledge Base
> Maintained by MAGI. Last updated: 2026-02-19 (Sprint 1 complete)

## Authentication
- OAuth2 with auto-refresh tokens
- Token stored: `.credentials/procore_token.json`
- Redirect URI: `http://localhost:9876/callback`
- Always pass `?company_id=4281379` as query param AND `Procore-Company-Id: 4281379` header
- Rate limit: `X-Rate-Limit-Limit: 100` requests per ~60s window
- Token expires in 5400 seconds (~90 min); refresh token works indefinitely

## Sandbox IDs
- Company ID: 4281379
- Project ID: 316469 (Sandbox Test Project)
- My user ID: 174986 (mecha.moby@gmail.com, Nicholas Stula)
- Sandbox demo user: 99519 (API Support, implementation+demo@procore.com)
- Test architect: 100299 (implementation+arch@procore.com)
- Test subcontractor: 100298 (implementation+sub@procore.com)

---

## Gotchas (Hard-Won — Saves Hours of Debugging)

### Auth & URLs
- Always pass BOTH `company_id` query param AND `Procore-Company-Id` header
- `drawings` endpoint 404s — use `drawing_revisions` instead
- `note_logs` (singular) 404s — use `notes_logs` (plural)

### Daily Logs
- Date range is REQUIRED: `filters[start_date]` + `filters[end_date]`
- Max range = 13 weeks (91 days) per request — chunk for full history
- Single date (`filters[date]`) returns 400 "must be a range"
- Weather log `wind` field uses unknown enum — omit it to avoid 422
- Visitor/delivery/accident/waste/safety_violation logs REQUIRE time fields

### RFIs
- Use v1.1 (NOT v1.0 or v2.0)
- Status filter MUST use array syntax: `filters[status][]=open` (not `filters[status]=open`)
- List endpoint has abbreviated question; single endpoint has full question + responses

### Meetings
- Use v1.1 (v1.0 returns 404)
- List returns GROUPED format: `[{group_title, meetings: [...]}]` — must flatten
- Topics POST returns 403 (permissions issue with our user)

### Submittals
- `filters[status]=X` doesn't filter as expected — returns all 146 regardless
- File attachments silently fail (no error, but file not attached)
- API-created users CAN'T be submittal managers/reviewers
- No submittal_types, submittal_statuses, or submittal_workflow_templates endpoints

### Vendors
- Creation body: `{"vendor": {...}}` NOT `{"company": {...}}`

### Cost Codes
- NOT at `/rest/v1.0/projects/{id}/cost_codes` (404)
- Correct: `/rest/v1.0/cost_codes?project_id={id}&company_id={id}`

### Documents
- No separate `/folders` or `/files` endpoints — all use `/documents`
- Returns flat list; use `parent_id` to reconstruct tree

### Checklist/Inspections
- NOT at `/rest/v1.0/projects/{id}/checklists` (404)
- Correct: `/rest/v1.0/projects/{id}/checklist/list_templates` and `/checklist/lists`

---

## Working Endpoints (Tested & Confirmed)

### Daily Logs
- `GET /rest/v1.0/projects/{id}/daily_logs` — umbrella (18 sub-types) [req. date range]
- `GET/POST /rest/v1.0/projects/{id}/weather_logs`
- `GET/POST /rest/v1.0/projects/{id}/manpower_logs`
- `GET/POST /rest/v1.0/projects/{id}/notes_logs` (plural!)
- `GET/POST /rest/v1.0/projects/{id}/timecard_entries`
- `GET/POST /rest/v1.0/projects/{id}/equipment_logs`
- `GET/POST /rest/v1.0/projects/{id}/visitor_logs`
- `GET/POST /rest/v1.0/projects/{id}/call_logs`
- `GET/POST /rest/v1.0/projects/{id}/delivery_logs`
- `GET/POST /rest/v1.0/projects/{id}/accident_logs`
- `GET/POST /rest/v1.0/projects/{id}/quantity_logs`
- `GET/POST /rest/v1.0/projects/{id}/work_logs`
- `GET/POST /rest/v1.0/projects/{id}/delay_logs`
- `GET/POST /rest/v1.0/projects/{id}/dumpster_logs`

### RFIs
- `GET /rest/v1.1/projects/{id}/rfis` — list (134 total, paginated 100/page)
- `GET /rest/v1.1/projects/{id}/rfis/{id}` — detail with responses

### Submittals
- `GET /rest/v1.0/projects/{id}/submittals` — 146 total
- `GET /rest/v1.0/projects/{id}/submittals/{id}` — detail

### Documents
- `GET /rest/v1.0/projects/{id}/documents` — 25 total (folders + files)

### Meetings
- `GET /rest/v1.1/projects/{id}/meetings` — grouped list
- `POST /rest/v1.1/projects/{id}/meetings` — create
- `GET /rest/v1.1/projects/{id}/meetings/{id}` — detail
- `GET /rest/v1.1/projects/{id}/meeting_topics` — list topics (read-only)

### Financial
- `GET /rest/v1.0/cost_codes?project_id={id}` — 304 cost codes
- `GET /rest/v1.0/line_item_types?project_id={id}` — 7 types
- `GET /rest/v1.0/projects/{id}/budget` — budget lock status
- `GET /rest/v1.0/prime_contracts?project_id={id}` — prime contracts (empty)
- `GET /rest/v1.0/projects/{id}/commitment_change_orders` — (empty)

### Observations
- `GET /rest/v1.0/projects/{id}/observations/items` — list (0 records)
- `GET /rest/v1.0/observations/types?project_id={id}` — 22 types
- `GET /rest/v1.0/projects/{id}/observation_types` — same 22 types

### Checklists
- `GET/POST /rest/v1.0/projects/{id}/checklist/list_templates` — templates
- `GET /rest/v1.0/projects/{id}/checklist/lists` — instances (empty, creation broken)

### Project Management
- `GET /rest/v1.0/vendors` — 118 vendors
- `GET /rest/v1.0/projects/{id}/users` — 554 users
- `GET /rest/v1.0/projects/{id}/timesheets` — empty
- `GET /rest/v1.0/webhooks/hooks` — webhook list
- `POST /rest/v1.0/webhooks/hooks` — create webhook

---

## Module Status in Sandbox

| Module | Enabled? | Evidence |
|---|---|---|
| Daily Logs | ✅ Yes | All sub-types work |
| RFIs | ✅ Yes | 134 records |
| Submittals | ✅ Yes | 146 records |
| Documents | ✅ Yes | 25 records |
| Meetings | ✅ Yes | Created test meeting |
| Observations | ✅ Yes (read-only) | GET works, POST 404 |
| Checklists | ✅ Yes (partial) | Templates work, lists broken |
| Timesheets | ✅ Yes (empty) | GET works |
| Change Events | ❌ No | All paths 404 |
| Punch Lists | ❌ No | All paths 404 |
| Budget | ⚠️ Partial | Only lock status visible |
| Prime Contracts | ⚠️ Partial | Endpoint works, empty |
| Webhooks | ✅ Yes | Created test hook |

---

## Pagination Patterns

| Endpoint | How to Paginate |
|---|---|
| Daily logs | No pagination — date range only (max 90 days) |
| RFIs | `page` + `per_page`, check `total` header and `Link` header |
| Submittals | `page` + `per_page`, check `total` header |
| Documents | `per_page`, check `total` header |
| Meetings | `per_page`, check `total` header |
| Cost codes | `per_page`, check `total` header (304 total) |

---

## Record Counts in Sandbox

| Resource | Count |
|---|---|
| RFIs | 134 (all open) |
| Submittals | 146 |
| Documents | 25 (23 folders + 2 files) |
| Drawing Revisions | 230 (from previous sprint) |
| Cost Codes | 304 |
| Vendors | 118 |
| Project Users | 554 |
| Observation Types | 22 |
| Line Item Types | 7 |

---

## Token Refresh Code

```python
import json, requests
creds_dir = "/home/moby/.openclaw/workspace/.credentials"
token = json.load(open(f"{creds_dir}/procore_token.json"))
env = {}
for line in open(f"{creds_dir}/procore.env"):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        env[k] = v
r = requests.post("https://login-sandbox.procore.com/oauth/token", data={
    "grant_type": "refresh_token",
    "refresh_token": token["refresh_token"],
    "client_id": env["PROCORE_CLIENT_ID"],
    "client_secret": env["PROCORE_CLIENT_SECRET"],
})
if r.status_code == 200:
    new_token = r.json()
    json.dump(new_token, open(f"{creds_dir}/procore_token.json", "w"), indent=2)
    print("Token refreshed!")
```

---

## Upcoming Sprint 2 Focus

1. Drawings deep dive (drawing_revisions with full field schema)
2. Drawing areas and sets
3. Cost code hierarchy (parent/child structure)
4. Enable and test Change Events module
5. Enable and test Punch Lists module
6. Observations — investigate POST body structure
7. Checklist/Inspection template sections and items
8. Photo/image upload testing
9. Webhook delivery and signature verification
