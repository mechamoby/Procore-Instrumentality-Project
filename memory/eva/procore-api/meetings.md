# Meetings API
> Status: **EXPLORED** — v1.1 working, topics creation blocked by permissions
> Tested: 2026-02-19

## Overview

The Meetings API allows creating and managing meeting records. The list endpoint returns a **grouped structure** (by meeting title/series). Meeting topics (agenda items) can be listed but not created with our current user permissions.

---

## Key Discovery: v1.1 Required

- `GET /rest/v1.0/projects/{id}/meetings` → **404**
- `GET /rest/v1.1/projects/{id}/meetings` → **200** ✅
- Must use **v1.1**

---

## Endpoints

### List Meetings
```
GET /rest/v1.1/projects/{project_id}/meetings
?company_id=4281379
&per_page=100
```

**⚠️ Quirk:** Returns a **grouped array**, not a flat list:
```json
[
  {
    "group_title": "OAC Meeting",
    "meetings": [
      {
        "id": 7134,
        "created_at": "2026-02-19T23:58:43Z",
        "created_by_id": 174986,
        "description": "",
        "distributed_at": null,
        "distributed_by": null,
        "ends_at": null,
        "is_private": true,
        "last_distributed_event": null,
        "location": null,
        "meeting_template_id": null,
        "meeting_topics_count": 0,
        "mode": "agenda",
        "occurred": false,
        "parent_id": null,
        "position": 1,
        "starts_at": null,
        "title": "OAC Meeting",
        "updated_at": "2026-02-19T23:58:43Z"
      }
    ]
  }
]
```

**List-level meeting fields:**
```
id, created_at, created_by_id, description, distributed_at, distributed_by,
ends_at, is_private, last_distributed_event, location, meeting_template_id,
meeting_topics_count, mode, occurred, parent_id, position, starts_at, title,
updated_at
```

---

### Get Single Meeting
```
GET /rest/v1.1/projects/{project_id}/meetings/{meeting_id}
```

**Full meeting fields (adds beyond list):**
```
attachments, attendees, conclusion, is_draft, meeting_categories,
remote_meeting_url, time_zone
```

**Complete schema:**
```json
{
  "id": 7134,
  "title": "Test Meeting - MAGI API Exploration",
  "position": 1,
  "location": null,
  "occurred": false,
  "time_zone": "US/Pacific",
  "is_private": true,
  "is_draft": false,
  "mode": "agenda",
  "remote_meeting_url": null,
  "meeting_template_id": null,
  "created_by_id": 174986,
  "created_at": "2026-02-19T23:58:43Z",
  "updated_at": "2026-02-19T23:58:43Z",
  "starts_at": null,
  "ends_at": null,
  "description": "",
  "conclusion": "",
  "attachments": [],
  "attendees": [],
  "meeting_categories": []
}
```

**Fields explained:**
| Field | Description |
|---|---|
| `mode` | `"agenda"` or `"minutes"` — lifecycle stage |
| `occurred` | bool — has the meeting happened |
| `is_draft` | bool — draft vs published |
| `is_private` | bool — visibility |
| `meeting_template_id` | Templates for recurring meetings |
| `meeting_topics_count` | How many agenda items |
| `parent_id` | Recurring meeting parent |
| `attendees` | Array of attendee objects |
| `meeting_categories` | Array of categories/tags |
| `conclusion` | HTML — meeting notes/minutes |
| `distributed_at` | When minutes were sent out |

---

### Create Meeting
```
POST /rest/v1.1/projects/{project_id}/meetings
```

```json
{
  "meeting": {
    "title": "OAC Meeting - Week 8",
    "meeting_date": "2026-02-20",
    "meeting_type": "general",
    "location": "Main Conference Room",
    "starts_at": "2026-02-20T09:00:00-08:00",
    "ends_at": "2026-02-20T10:00:00-08:00",
    "is_private": false
  }
}
```

**Returns 201** with full meeting object.

---

### Meeting Topics (Agenda Items)
```
GET /rest/v1.1/projects/{project_id}/meeting_topics
?company_id=4281379
```

**Note:** Topics are NOT nested under the meeting URL. Use the flat endpoint.

**Returns:** 0 records in sandbox (meeting was just created with no topics)

**Create Meeting Topic:**
```
POST /rest/v1.1/projects/{project_id}/meeting_topics
```
→ **403 Forbidden** with our current user

This means our API user (mecha.moby@gmail.com) doesn't have permission to add meeting topics. Likely requires "Editor" or higher role on meetings.

---

## Status Workflow

```
Draft (is_draft: true) → Published (is_draft: false)
                            ↓
                    Occurred (occurred: true)
                            ↓
                    Minutes Distributed (distributed_at set)
```

**mode** field progression:
- `"agenda"` — Before meeting occurs
- `"minutes"` — After meeting occurs (generating minutes)

---

## Key Relationships

- **Recurring meetings:** `parent_id` links child meetings to recurring series
- **Templates:** `meeting_template_id` for standardized agenda templates
- **Distribution:** `distributed_at` + `distributed_by` track when minutes sent
- **Topics:** Separate endpoint `/meeting_topics` (not nested)

---

## EVA Integration Plan

### Sync Strategy
```python
def sync_meetings(project_id):
    # List returns grouped format
    r = api.get(f'/rest/v1.1/projects/{project_id}/meetings', 
                params={'per_page': 100})
    groups = r.json()
    meetings = []
    for group in groups:
        meetings.extend(group['meetings'])
    
    # Fetch full details for each (includes attendees, conclusion)
    details = []
    for m in meetings:
        r = api.get(f'/rest/v1.1/projects/{project_id}/meetings/{m["id"]}')
        details.append(r.json())
    return details
```

### Meeting Topics
```python
# Get all topics (flat, across all meetings)
topics = api.get(f'/rest/v1.1/projects/{project_id}/meeting_topics').json()
# Filter by meeting_id from each topic's data
```

### Cross-References
- `attendees` → Link to project users
- `meeting_template_id` → Recurring pattern
- `is_private` → Access control for EVA
- `occurred` → Filter to past/future meetings

---

## Known Limitations

| Issue | Impact |
|---|---|
| v1.0 returns 404, must use v1.1 | Remember version |
| List is grouped format, not flat | Must flatten for EVA's DB |
| Meeting topics POST returns 403 | Can't create agenda items via API |
| No `meeting_categories` create endpoint found | Categories may be preset |
| `meeting_topics_count` in list but topics need separate call | N+1 query risk |
