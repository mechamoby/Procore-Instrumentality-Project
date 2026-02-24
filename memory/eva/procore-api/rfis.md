# RFIs API — Deep Dive
> Status: **FULLY EXPLORED** — Live sandbox tested 2026-02-19
> Sandbox: 134 RFIs total (all status: "open")

## Overview

RFIs (Requests for Information) are fully functional. The API supports listing, creating, updating, and detailed retrieval including questions, responses, attachments, and linked records.

---

## Endpoints

### List RFIs
```
GET /rest/v1.1/projects/{project_id}/rfis
```

**Query Parameters:**
| Param | Description |
|---|---|
| `page` | Page number (default: 1) |
| `per_page` | Records per page (default varies; 100 confirmed working) |
| `filters[status][]` | Filter by status: `open`, `draft`, `closed` |
| `search` | Full-text search across subjects and bodies |
| `sort` | Sort field |

**Pagination:**
- Response header `total` contains total count
- `Link` header provides next/last page URLs
- Pattern: `Link: <URL>; rel="next", <URL>; rel="last"`
- Example: 134 total → page 1 has 100, page 2 has 34

**Versions:** v1.0 and v1.1 return same fields. v2.0 returns 404.

---

### Get Single RFI
```
GET /rest/v1.1/projects/{project_id}/rfis/{rfi_id}
```

Returns **significantly more fields** than the list endpoint, including full question body, responses with attachments, distribution list, linked change events, linked drawings.

---

## Field Inventory

### List Response Fields
```
assignee              Ball-in-court user (single)
assignees             Array of assignee objects (with response_required flag)
ball_in_court         Ball-in-court user (single, legacy)
ball_in_courts        Array of BIC users
cost_code             Linked cost code object
cost_impact           {status, value}
created_at            ISO timestamp
created_by            {id, login, name}
current_revision      bool
custom_fields         obj (project-defined)
due_date              YYYY-MM-DD
full_number           String (e.g., "186")
has_revisions         bool
id                    int
initiated_at          ISO timestamp
link                  Web URL to RFI in Procore UI
location              Location object or null
location_id           int or null
number                String (same as full_number when no prefix)
prefix                String or null
priority              {name, value}
private               bool
project_stage         Project stage or null
proposed_solution     Text or null
questions             Array of question objects (abbreviated in list view)
received_from         User object or null
reference             String or null
responsible_contractor Vendor object or null
revision              String (e.g., "0", "1")
rfi_manager           {id, login, name}
schedule_impact       {status, value}
source_rfi_header_id  int (same as id for original revision)
specification_section_id int or null
status                "open" | "draft" | "closed"
sub_job               Sub-job object or null
subject               String (RFI title)
time_resolved         ISO timestamp or null
translated_status     "Open" | "Draft" | "Closed"
updated_at            ISO timestamp
```

### Additional Fields in Single-RFI View
```
ball_in_court_role    String or null
change_events         Array of linked change events
coordination_issues   Array
correspondences       Array
custom_textfield_1    String or null
custom_textfield_2    String or null
distribution_list     Array of {id, login, name}
draft                 bool
drawing_ids           Array of int
drawing_number        String or null
guid                  UUID string
linked_connected_rfis Array
linked_external_rfis  Array
question              Full question object (see below)
responses             Array of response objects (see below)
specification_section Full spec section object (vs just ID in list)
title                 String (same as subject)
```

---

## Question Object Schema

```json
{
  "id": 90983,
  "body": "<HTML or text content>",
  "plain_text_body": "Plain text version of body",
  "created_at": "2026-02-19T02:25:25Z",
  "created_by": "Nicholas Stula",
  "download_all_attachments_url": "https://sandbox.procore.com/rest/v1.1/projects/316469/rfis/{rfi_id}/question_download_all_attachments/{question_id}",
  "attachments": []
}
```

**Note:** In list view, `questions` is an array. In single view, `question` is a single object.

---

## Response Object Schema

```json
{
  "id": 29663,
  "body": "<HTML or text content>",
  "plain_text_body": "Plain text version of body",
  "created_at": "2026-02-19T02:35:36Z",
  "updated_at": "2026-02-19T02:35:36Z",
  "created_by": {"id": 174986, "name": "Nicholas Stula", "login": "mecha.moby@gmail.com"},
  "created_by_id": 174986,
  "official": false,
  "attachments": [],
  "attachments_count": 0,
  "question_id": 90983,
  "download_all_attachments_url": "https://sandbox.procore.com/rest/v1.0/projects/316469/rfis/{rfi_id}/replies/{response_id}/download_all_attachments"
}
```

**Key fields:**
- `official` — Whether this is an official/formal response
- `question_id` — Links response to the question it answers

---

## Status Values

| Status | Count in Sandbox | API Filter |
|---|---|---|
| `open` | 134 | `filters[status][]=open` |
| `draft` | 0 | `filters[status][]=draft` |
| `closed` | 0 | `filters[status][]=closed` |

**Note:** The simpler `filters[status]=open` (without `[]`) returns 400.
Always use array syntax: `filters[status][]=open`

---

## Search & Filtering

### Full-Text Search
```
GET /rest/v1.1/projects/{id}/rfis?search=ADA
```
Returns RFIs where subject or question body matches. Example: "ADA" found 16 of 134 RFIs.

### Filter Combinations
```
GET /rest/v1.1/projects/{id}/rfis
  ?filters[status][]=open
  &filters[created_at][]=2026-01-01T00:00:00Z...2026-02-19T23:59:59Z
  &search=concrete
  &sort=created_at
  &page=1
  &per_page=100
```

---

## Create RFI

```
POST /rest/v1.1/projects/{project_id}/rfis
```

```json
{
  "rfi": {
    "subject": "Clarification needed on foundation waterproofing spec",
    "question_body": "Please clarify which waterproofing membrane is required per Section 07130.",
    "assignees": [{"id": 100299}],
    "rfi_manager_id": 99519,
    "due_date": "2026-03-01",
    "priority": "high",
    "private": false,
    "specification_section_id": 77,
    "cost_code_id": null,
    "reference": "Spec Section 07130"
  }
}
```

---

## Add Response to RFI

```
POST /rest/v1.1/projects/{project_id}/rfis/{rfi_id}/responses
```

```json
{
  "rfi_response": {
    "body": "Use Tremco Paraseal LG. See attached detail sheet.",
    "official": true
  }
}
```

---

## Sandbox Data Notes

- **Total:** 134 RFIs (Nick's import of BTV5 project data)
- **All status:** Open — no closed or draft RFIs in sandbox
- **Pagination confirmed:** 134 = page 1 (100) + page 2 (34)
- **Question about 134 vs "more expected":** Nick mentioned expecting more. The 134 count is what the API returns with no filters. If there are revisions, they may show under different revision numbers. The `current_revision` field (bool) may filter to show only latest revisions.

---

## EVA Integration Plan

### Full Sync Strategy
```python
def sync_all_rfis(project_id):
    all_rfis = []
    page = 1
    while True:
        r = api.get(f'/rest/v1.1/projects/{project_id}/rfis',
                    params={'page': page, 'per_page': 100})
        data = r.json()
        all_rfis.extend(data)
        total = int(r.headers.get('total', 0))
        if len(all_rfis) >= total or not data:
            break
        page += 1
    return all_rfis
```

### For Individual RFI Detail (with responses)
```python
rfi_detail = api.get(f'/rest/v1.1/projects/{project_id}/rfis/{rfi_id}').json()
# rfi_detail['question'] - the question text
# rfi_detail['responses'] - list of responses
# rfi_detail['distribution_list'] - who gets notified
# rfi_detail['change_events'] - linked change events
# rfi_detail['drawing_ids'] - linked drawings
```

### Key Cross-Reference Fields
- `specification_section` → Link to submittal log (same spec sections)
- `responsible_contractor.id` → Vendor/subcontractor record
- `drawing_ids` → Cross-reference with drawing revisions
- `change_events` → Link to cost/schedule impacts
- `due_date` vs `time_resolved` → Track response timeliness
- `ball_in_courts` → Who needs to take action right now

---

## Known Limitations

| Issue | Impact |
|---|---|
| No `v2.0` endpoint | Use v1.1 |
| `filters[status]=X` (no brackets) returns 400 | Use `filters[status][]=X` |
| List view has abbreviated question object | Must fetch individual RFI for full details |
| Attachments in sandbox appear empty | Sandbox may not retain file binaries |
| Revision system complex | `current_revision: true` + `source_rfi_header_id` tracks lineage |
