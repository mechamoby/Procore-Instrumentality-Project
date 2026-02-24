# EVA-00: Query Patterns & API Design

## Query API Overview

EVA-00 exposes a REST API on port 8400 that all EVA agents use to query the knowledge base. No agent has direct database access.

**Base URL:** `http://localhost:8400/api/v1`
**Auth:** `Authorization: Bearer <agent-api-key>`

---

## Core Query Types

### 1. Semantic Search (Vector Similarity)

The most powerful query — find conceptually similar content across all projects.

**Endpoint:** `POST /search/semantic`

```json
{
  "query": "concrete mix design for post-tensioned slabs",
  "filters": {
    "project_ids": ["uuid1", "uuid2"],
    "doc_types": ["submittal", "rfi", "spec_section"],
    "spec_sections": ["03 30 00"],
    "date_range": { "from": "2020-01-01", "to": "2025-12-31" }
  },
  "limit": 20,
  "min_similarity": 0.7
}
```

**SQL behind it:**
```sql
-- Query embedding generated from user's search text
WITH query_embedding AS (
    SELECT $1::vector(768) AS embedding
)
SELECT
    dc.id, dc.source_type, dc.source_id, dc.content,
    dc.project_id, p.name AS project_name,
    dc.doc_type, dc.spec_section,
    1 - (dc.embedding <=> qe.embedding) AS similarity
FROM document_chunks dc
CROSS JOIN query_embedding qe
JOIN projects p ON p.id = dc.project_id
WHERE dc.project_id = ANY($2::uuid[])
  AND dc.doc_type = ANY($3::document_type[])
  AND 1 - (dc.embedding <=> qe.embedding) > $4
ORDER BY dc.embedding <=> qe.embedding
LIMIT $5;
```

### 2. Full-Text Search (Keyword)

Traditional keyword search with ranking. Good for exact terms, document numbers, company names.

**Endpoint:** `POST /search/text`

```json
{
  "query": "waterproofing membrane Sika",
  "tables": ["submittals", "rfis", "spec_sections"],
  "project_ids": ["uuid1"],
  "limit": 20
}
```

**SQL behind it:**
```sql
SELECT id, number, title, description,
       ts_rank(search_vector, websearch_to_tsquery('english', $1)) AS rank
FROM submittals
WHERE project_id = ANY($2::uuid[])
  AND search_vector @@ websearch_to_tsquery('english', $1)
ORDER BY rank DESC
LIMIT $3;
```

### 3. Hybrid Search (Semantic + Keyword)

Combines vector similarity with full-text relevance using Reciprocal Rank Fusion (RRF).

**Endpoint:** `POST /search/hybrid`

```json
{
  "query": "reinforcing steel shop drawings",
  "filters": { "doc_types": ["submittal"] },
  "limit": 20,
  "semantic_weight": 0.6,
  "text_weight": 0.4
}
```

**Implementation:**
```sql
-- RRF: score = Σ 1/(k + rank_i) for each result across both methods
WITH semantic_results AS (
    SELECT source_id, ROW_NUMBER() OVER (ORDER BY embedding <=> $1) AS rank
    FROM document_chunks WHERE doc_type = 'submittal'
    LIMIT 50
),
text_results AS (
    SELECT id AS source_id, ROW_NUMBER() OVER (ORDER BY ts_rank(search_vector, q) DESC) AS rank
    FROM submittals, websearch_to_tsquery('english', $2) q
    WHERE search_vector @@ q
    LIMIT 50
),
combined AS (
    SELECT
        COALESCE(s.source_id, t.source_id) AS id,
        COALESCE(0.6 / (60.0 + s.rank), 0) + COALESCE(0.4 / (60.0 + t.rank), 0) AS rrf_score
    FROM semantic_results s
    FULL OUTER JOIN text_results t ON s.source_id = t.source_id
)
SELECT * FROM combined ORDER BY rrf_score DESC LIMIT 20;
```

### 4. Structured Queries (Filters + Lookups)

Direct entity lookups and filtered lists.

**Endpoints:**
- `GET /projects` — list projects
- `GET /projects/{id}/submittals?status=open&spec_section=03+30+00`
- `GET /projects/{id}/rfis?status=open&assigned_to={company_id}`
- `GET /projects/{id}/drawings?discipline=structural&current=true`
- `GET /projects/{id}/daily-reports?from=2024-01-01&to=2024-01-31`
- `GET /submittals/{id}` — full detail with workflow history
- `GET /rfis/{id}` — full detail with all responses

---

## Common Agent Query Patterns

### EVA-01: Submittal Agent

**"Find similar submittals from past projects"**
```json
POST /search/semantic
{
  "query": "hollow metal door frames 16 gauge galvanized",
  "filters": {
    "doc_types": ["submittal"],
    "spec_sections": ["08 11 00", "08 11 13"]
  },
  "limit": 10
}
```
Returns past submittals for similar products — the agent uses these as templates and learns from review comments.

**"What review comments were made on previous concrete mix designs?"**
```json
POST /submittals/search-with-history
{
  "query": "concrete mix design",
  "include_workflow_history": true,
  "status_filter": ["approved_as_noted", "revise_and_resubmit"],
  "limit": 10
}
```
Returns submittals + their workflow history entries — particularly the reviewer comments that explain what was wrong.

**"Which spec section governs this submittal?"**
```json
GET /projects/{id}/spec-sections?number=09+91+23
```

**"What's the typical lead time for structural steel shop drawings?"**
```json
POST /analytics/submittals
{
  "query_type": "lead_time",
  "spec_sections": ["05 12 00"],
  "project_ids": ["all"]
}
```
Aggregates `lead_time_days` and turnaround data across past projects.

---

### EVA-02: RFI Agent

**"Have we asked a similar question before?"**
```json
POST /search/semantic
{
  "query": "curtain wall anchor spacing at concrete spandrel beam",
  "filters": { "doc_types": ["rfi"] },
  "limit": 10
}
```
Finds semantically similar past RFIs — helps avoid duplicate questions and provides prior answers as reference.

**"What's the architect's track record on response time for structural RFIs?"**
```json
POST /analytics/rfis
{
  "query_type": "response_time",
  "assigned_to_company_id": "uuid",
  "spec_divisions": [3, 5],
  "project_ids": ["all"]
}
```

**"Get all open RFIs that reference drawing S-201"**
```json
GET /projects/{id}/rfis?status=open&drawing_number=S-201
```

---

### EVA-03: Schedule Agent

**"What submittals and RFIs are blocking the schedule?"**
```json
POST /schedule/blockers
{
  "project_id": "uuid",
  "open_submittals": true,
  "open_rfis": true,
  "critical_path_only": true
}
```
Cross-references open submittals/RFIs with schedule activities to identify blockers.

---

### Cross-Cutting Queries

**"Everything related to spec section 03 30 00 on this project"**
```json
POST /search/by-spec-section
{
  "project_id": "uuid",
  "spec_section": "03 30 00",
  "include": ["spec_text", "submittals", "rfis", "drawings", "meeting_items"]
}
```
Returns the spec section content, all submittals against it, all RFIs referencing it, related drawings, and meeting minute items that discussed it.

**"What happened on this project in January 2024?"**
```json
POST /projects/{id}/timeline
{
  "from": "2024-01-01",
  "to": "2024-01-31",
  "include": ["daily_reports", "rfis", "submittals", "meetings", "change_orders", "photos"]
}
```
Returns a chronological timeline of all project activity.

---

## Caching Strategy (Redis)

| Query Type | Cache Key Pattern | TTL |
|---|---|---|
| Project list | `eva00:projects:list` | 15 min |
| Entity by ID | `eva00:{type}:{id}` | 5 min |
| Filtered list (submittals by status) | `eva00:{project}:submittals:{hash(filters)}` | 5 min |
| Semantic search results | `eva00:semantic:{hash(query+filters)}` | 10 min |
| Analytics/aggregations | `eva00:analytics:{hash(params)}` | 30 min |

Cache invalidation: On any write/sync to an entity, delete all cache keys matching that project + entity type.

---

## Response Format

All responses follow:

```json
{
  "data": [...],
  "meta": {
    "total": 47,
    "limit": 20,
    "offset": 0,
    "query_ms": 12,
    "search_type": "hybrid"
  }
}
```

For semantic search, each result includes a `similarity` score (0-1).

---

## Rate Limits

| Agent | Requests/min | Burst |
|---|---|---|
| EVA-01 (Submittal) | 120 | 30 |
| EVA-02 (RFI) | 120 | 30 |
| EVA-03 (Schedule) | 60 | 15 |
| Admin/Dashboard | 300 | 60 |

Enforced via Redis token bucket.
