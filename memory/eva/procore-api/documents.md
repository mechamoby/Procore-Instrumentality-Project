# Documents & File Management API
> Status: **FULLY EXPLORED** — 25 documents in sandbox
> Tested: 2026-02-19

## Overview

Procore's document management uses a **flat list with parent_id** approach rather than nested endpoints. Both folders and files are returned together, differentiated by `document_type`. The sandbox has a pre-structured folder hierarchy.

---

## Endpoints

### List Documents (Flat)
```
GET /rest/v1.0/projects/{project_id}/documents
?company_id=4281379
&per_page=100
```

**Returns:** All documents and folders as a flat array
**Total in sandbox:** 25 (23 folders + 2 files)

---

### Filter by Type
```
GET /rest/v1.0/projects/{id}/documents
?filters[document_type]=file       # Only files
?filters[document_type]=folder     # Only folders
?parent_id=14475454                # Children of specific folder
```

---

### Create Folder
```
POST /rest/v1.0/projects/{project_id}/documents
```

```json
{
  "document": {
    "name": "Field Reports",
    "document_type": "folder",
    "parent_id": 14475454,
    "private": false
  }
}
```

---

## Complete Field Inventory

```json
{
  "id": 14475561,
  "created_at": "2026-02-17T01:15:34Z",
  "created_by": {
    "id": 2,
    "company_name": null,
    "locale": null,
    "login": "internal@procore.com",
    "name": " "
  },
  "custom_fields": {},
  "document_type": "folder|file",
  "is_deleted": false,
  "is_recycle_bin": false,
  "name": "11-30-20 at 04-38 PM - Sandbox Test Project.mpp",
  "name_with_path": "Sandbox Test Project/Schedules/11-30-20 at 04-38 PM - Sandbox Test Project.mpp",
  "parent_id": 14475555,
  "private": false,
  "read_only": true,
  "updated_at": "2026-02-17T01:15:34Z"
}
```

**Fields:**
| Field | Description |
|---|---|
| `document_type` | `"folder"` or `"file"` |
| `name` | Display name |
| `name_with_path` | Full path from root |
| `parent_id` | Parent folder ID (null for root) |
| `is_deleted` | Soft delete flag |
| `is_recycle_bin` | Whether this is the recycle bin system folder |
| `private` | Visibility restriction |
| `read_only` | Cannot be modified |
| `custom_fields` | Project-defined metadata |

---

## Sandbox Folder Structure

```
📁 Sandbox Test Project (id=14475454, root)
├── 📁 Recycle Bin (id=14475455, system)
├── 📁 Schedules (id=14475555)
│   └── 📄 11-30-20 at 04-38 PM - Sandbox Test Project.mpp
├── 📁 01 Design Files (id=14475568)
│   ├── 📁 01 Bulletins & Addenda (id=14475571)
│   │   └── 📄 férias 10.PDF (id=14475660)
│   ├── 📁 02 Design CAD Files (id=14475574)
│   ├── 📁 03 PDF Drawings (id=14475577)
│   ├── 📁 04 Specifications (id=14475580)
│   └── 📁 05 BIM Files (id=14475583)
├── 📁 02 Bid Packages (id=14475585)
├── 📁 03 Safety (id=14475590)
├── 📁 04 Subcontractor Files (id=14475593)
│   ├── 📁 01 Inbound (id=14475597)
│   └── 📁 02 Outbound (id=14475601)
└── 📁 05 INTERNAL DOCUMENTS (id=14475606)
    ├── 📁 01 Construction Estimates (id=14475611)
    ├── 📁 02 Permits (id=14475616)
    ├── 📁 03 Testing and Quality Control (id=14475621)
    ├── 📁 04 Closeout and Preconstruction (id=14475626)
    ├── 📁 05 Subcontractors (id=14475631)
    ├── 📁 06 Warranty Documentation (id=14475636)
    ├── 📁 07 Post Project Documentation (id=14475640)
    └── 📁 08 Safety (id=14475643)
```

---

## Key Observations

1. **No separate file/folder endpoints** — `GET /rest/v1.0/projects/{id}/folders/{id}` returns 404. Use documents endpoint with filters.

2. **Recycle bin** — `is_recycle_bin: true` marks the system recycle bin. Include `is_deleted=false` filter to exclude deleted items.

3. **name_with_path** — Pre-computed full path string, useful for display without rebuilding tree.

4. **read_only** — System-created files (like the schedule) may be read-only.

5. **No direct download URL** in document list — File download likely requires separate auth step or follows Procore's document viewer URL pattern.

---

## File Upload

File upload requires multipart form data (different from JSON API):

```
POST /rest/v1.0/projects/{project_id}/documents
Content-Type: multipart/form-data

document[name] = "Field Report 2026-02-19.pdf"
document[document_type] = "file"
document[parent_id] = 14475590
document[data] = <file binary>
```

**Note:** File upload was not tested in this sprint. Binary upload handling in sandbox may have quirks (similar to submittal attachments silently failing).

---

## 404 Endpoints

| Endpoint | Status |
|---|---|
| `GET /rest/v1.0/projects/{id}/folders` | 404 |
| `GET /rest/v1.0/projects/{id}/folders/{id}` | 404 |
| `GET /rest/v1.0/projects/{id}/files/{id}` | 404 |

---

## EVA Integration Plan

### Build Document Tree
```python
def build_document_tree(project_id):
    r = api.get(f'/rest/v1.0/projects/{project_id}/documents',
                params={'per_page': 10000})
    docs = r.json()
    
    # Build parent lookup
    by_id = {d['id']: d for d in docs}
    children = {}
    for d in docs:
        pid = d.get('parent_id')
        if pid:
            children.setdefault(pid, []).append(d['id'])
    
    return by_id, children

# Filter out recycle bin and deleted items
active_docs = [d for d in docs 
               if not d['is_deleted'] and not d['is_recycle_bin']]
```

### EVA Use Cases
1. **Smart filing** — When receiving a document, AI suggests correct folder
2. **Document indexing** — Index all documents for semantic search
3. **Compliance check** — Verify required documents exist in required folders
4. **Folder monitoring** — Webhook on new documents to trigger AI analysis

### Key Cross-References
- Documents in `03 Safety` → Link to safety_violation_logs, accident_logs
- Documents in `04 Specifications` → Link to submittals by spec section
- Documents in `Schedules` → Link to project schedule/milestones
- `created_by` → Who uploaded this document

---

## Webhook Integration

Subscribe to document events:
```json
{
  "hook": {
    "api_version": "v1.0",
    "destination_url": "https://eva.example.com/procore-webhook",
    "triggers": [
      {"api_version": "v1.0", "event_type": "create", "resource_name": "Document"},
      {"api_version": "v1.0", "event_type": "update", "resource_name": "Document"}
    ]
  }
}
```

---

## Known Limitations

| Issue | Impact |
|---|---|
| No separate file/folder endpoints | Must use flat list with filters |
| No direct file download URL in response | Need additional auth for downloads |
| File upload not tested | Binary upload may have sandbox quirks |
| `per_page` maximum unknown | Test to find ceiling |
| Recycle bin items included by default | Must filter `is_deleted` and `is_recycle_bin` |
