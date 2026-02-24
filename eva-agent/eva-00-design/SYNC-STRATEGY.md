# EVA-00: Procore Data Synchronization Strategy

## Overview

EVA-00 maintains a local replica of project data from Procore. Data flows **one direction: Procore → Local**. EVA-00 is read-only; it never writes back to Procore. (Future EVA agents that create submittals/RFIs will write to Procore via their own API integration, not through EVA-00.)

---

## Sync Architecture

```
┌──────────────────┐          ┌──────────────────────────────────┐
│   Procore Cloud  │          │        EVA-00 Local Server       │
│                  │          │                                  │
│  REST API v1.1   │◀─poll──▶│  ┌────────────────────────────┐  │
│                  │          │  │      Sync Agent             │  │
│  Webhooks ───────┼────────▶│  │  - Poll scheduler           │  │
│  (optional)      │          │  │  - Webhook receiver         │  │
│                  │          │  │  - Diff engine              │  │
│                  │          │  │  - Rate limiter             │  │
│                  │          │  └─────────────┬──────────────┘  │
│                  │          │                │                  │
│                  │          │                ▼                  │
│                  │          │  ┌────────────────────────────┐  │
│                  │          │  │   Ingestion Queue (Redis)  │  │
│                  │          │  └────────────────────────────┘  │
└──────────────────┘          └──────────────────────────────────┘
```

---

## Sync Method: Polling with Webhook Acceleration

### Why Not Pure Webhooks?

- Procore webhooks are **not guaranteed delivery** — they can drop events
- Webhooks require a publicly reachable endpoint (our server is behind NAT on a local network)
- Webhooks don't give you initial data — you still need a full pull

### Why Not Pure Polling?

- Procore rate limits: **100 requests per ~60 second window** (confirmed from testing)
- Polling every entity every minute would burn through rate limits
- Unnecessary load for data that changes infrequently

### Hybrid Approach

1. **Scheduled polling** as the reliable backbone (catches everything)
2. **Webhooks** (via Procore → cloudflare tunnel or ngrok) as optional accelerator for near-real-time updates when available
3. **Polling always wins** — if webhook and poll disagree, poll data is authoritative

---

## Polling Schedule

| Entity Type | Poll Interval | Priority | Notes |
|---|---|---|---|
| Projects (list) | 1 hour | Low | Rarely changes |
| Submittals | 5 minutes | **High** | Active workflow, time-sensitive |
| RFIs | 5 minutes | **High** | Active workflow, time-sensitive |
| Drawings | 30 minutes | Medium | New sets issued periodically |
| Daily Reports | 15 minutes | Medium | Typically entered once/day but may be edited |
| Meetings | 30 minutes | Low | Usually entered after meeting |
| Change Orders | 15 minutes | Medium | Financial, important to track |
| Photos | 30 minutes | Low | Bulk uploaded periodically |
| Documents | 30 minutes | Low | Ad-hoc uploads |
| Companies/Contacts | 1 hour | Low | Rarely changes |
| Spec Sections | 1 hour | Low | Changes only with ASIs |
| Schedules | 1 hour | Low | Updated weekly typically |

### Incremental Polling

Each entity type tracks its sync position in `sync_cursors`:

```
1. Read last_synced_at for entity type
2. Call Procore API: GET /rest/v1.0/projects/{id}/{entities}?updated_after={last_synced_at}
3. For each returned item:
   a. Check if procore_id exists locally
   b. If exists → compare payload_hash → update if changed
   c. If new → create local record
4. Update sync_cursors.last_synced_at = now()
```

### Pagination

Procore API paginates at 100 items per page. The sync agent handles:

```
page = 1
loop:
    response = GET /entities?per_page=100&page={page}&updated_after={cursor}
    process(response.items)
    if response.items.length < 100: break
    page += 1
    sleep(rate_limit_delay)
```

---

## Webhook Integration (Optional)

When the client's network allows it (via Cloudflare Tunnel or similar), webhooks provide near-instant updates:

### Setup

```
Procore → HTTPS webhook → Cloudflare Tunnel → localhost:8401/webhooks/procore
```

### Webhook Events Subscribed

- `submittals.update`, `submittals.create`
- `rfis.update`, `rfis.create`
- `drawings.create`
- `change_orders.update`, `change_orders.create`
- `daily_logs.create`, `daily_logs.update`

### Webhook Processing

```
1. Receive webhook event
2. Verify HMAC signature (Procore webhook secret)
3. Extract entity_type + procore_id from payload
4. Enqueue an immediate sync for that specific entity:
   XADD eva00:sync:priority * type "submittal" procore_id "12345"
5. Sync agent picks up priority items before scheduled polls
```

Webhooks don't carry full payloads — they're just triggers. We still fetch the full entity from the API.

---

## Conflict Resolution

Since EVA-00 is read-only (Procore is source of truth), conflicts are rare. But they can occur:

### Scenario: Entity updated in Procore while local ingestion is processing

**Resolution:** Procore always wins. On next poll:
1. Compare `procore_updated_at` with our `local_updated_at`
2. If Procore is newer → overwrite local record
3. If local is newer (shouldn't happen, but defensive) → log as conflict in `sync_log`, overwrite with Procore data anyway
4. Re-trigger ingestion pipeline for updated content (re-chunk, re-embed)

### Scenario: Entity deleted in Procore

**Resolution:** Soft delete locally.
1. If entity exists locally but not returned by Procore "list all" endpoint → mark `is_deleted = TRUE`
2. Keep all data and embeddings (construction records are legal documents — never hard delete)
3. Exclude soft-deleted items from default queries (but allow explicit include)

### Scenario: File updated in Procore (new revision)

**Resolution:**
1. Download new file
2. Compute new SHA-256 hash
3. If hash differs → store new file, update `file_hash` and `file_path`
4. Keep old file (for drawings, create entry in `drawing_revisions`)
5. Re-trigger ingestion pipeline for the new content

---

## Rate Limiting

### Procore API Limits (CORRECTED from real testing)

- **100 requests per ~60 second window** (confirmed via `X-Rate-Limit-Limit` header)
- NOT 3,600/hour as previously assumed from docs — actual limit is much lower
- Exceeding the limit causes connection errors (not just 429 responses)
- Must implement exponential backoff with connection-aware retry

### Our Rate Limiter (Redis)

```
Token bucket in Redis:
- Bucket size: 10 tokens (burst — careful, this is 10% of the 60s budget)
- Refill rate: 1.5 tokens/second (sustained ~90/min, leaving buffer)
- Before each API call: acquire token, block if empty
- On ConnectionError: pause 65 seconds, reset bucket
```

### Budget Allocation

| Consumer | Budget (requests/min) |
|---|---|
| Scheduled polling | 60 (60%) |
| Webhook-triggered fetches | 15 (15%) |
| On-demand (user-triggered refresh) | 15 (15%) |
| Buffer / retry headroom | 10 (10%) |

### Token Keepalive

OAuth refresh tokens expire after extended inactivity. A cron job must refresh the
token every 12 hours regardless of sync activity. See `scripts/procore-keepalive.py`.
Failure to do this requires manual re-authorization (user must visit OAuth URL in browser).

---

## File Downloads

Large files (drawings, photos) require special handling:

1. **Download to temp directory** first: `/data/tmp/`
2. **Compute SHA-256** during download (streaming hash)
3. **Check dedup** — if hash exists, skip storage
4. **Move to final path** (atomic rename within same filesystem)
5. **Trigger thumbnail generation** asynchronously
6. **Queue for ingestion pipeline** (OCR, text extraction, embedding)

### Download Parallelism

- Max 3 concurrent file downloads (avoid saturating client's internet)
- Priority: submittals > RFIs > drawings > photos > other
- Resume support for interrupted downloads (HTTP Range headers)

---

## Initial Full Sync

When onboarding a new client:

```
Phase 1: Metadata (fast)
  1. Sync all projects
  2. Sync all companies and contacts
  3. Sync spec sections per project

Phase 2: Active data (medium)
  4. Sync all submittals + workflow history
  5. Sync all RFIs + responses
  6. Sync change orders
  7. Sync meeting minutes

Phase 3: Files (slow)
  8. Download all drawings (largest files)
  9. Download all photos
  10. Download all documents

Phase 4: Schedules
  11. Sync schedule data
  12. Sync daily reports
```

**Estimated time for full sync (20 projects, ~5000 items):**
- Metadata: ~30 minutes
- Active data: ~2 hours
- File downloads: ~4-8 hours (depends on internet speed + total file size)
- Run overnight, unattended

### Alternative: PDF Log Import (Faster for Initial Load)

For onboarding existing clients, Procore's exported PDF logs can be parsed locally instead
of pulling each item via API. Tested approach:

1. Client exports RFI log, Submittal log as PDFs from Procore
2. PyMuPDF extracts all text (questions, answers, dates, people, cost codes) — $0, <1 second
3. Parser structures data into JSON (133 RFIs from 98-page PDF in <1 second)
4. Batch upload via API for items that need to live in Procore sandbox (rate-limited)
5. OR direct insert into EVA-00 database (instant, no rate limit)

**Advantages:** 10-100x faster than API extraction, $0 token cost, gets full Q&A threads.
**Disadvantages:** No file attachments (just filenames), requires user to export PDFs manually.
**Recommendation:** Use PDF import for historical data, API sync for ongoing updates.

### Cover Sheet Pipeline (Submittals)

Procore cover sheet PDFs contain embedded signed download URLs for ALL attachments. Pipeline:
1. Export cover sheets from Procore (manual, one at a time — no bulk export)
2. PyMuPDF extracts links from `storage.procore.com` + metadata
3. Download actual attachment PDFs directly via signed URLs (bypasses API rate limit)
4. Create submittal records + upload attachments via API
**Cost:** $0 for parsing, rate-limited only for API creates.

---

## Monitoring & Observability

### Sync Dashboard Metrics

- Last successful sync per entity type per project
- Sync errors in last 24 hours
- API rate limit usage (current bucket level)
- Entities pending sync
- File download queue depth

### Alerts

| Condition | Severity | Action |
|---|---|---|
| Entity type not synced in 2× its interval | Warning | Log, retry |
| Entity type not synced in 5× its interval | Critical | Alert operator |
| Rate limit exhausted | Warning | Back off, resume next window |
| Procore API returning 5xx | Critical | Exponential backoff, alert |
| Sync conflict detected | Info | Log to sync_log |
| Disk space < 20% | Critical | Pause file downloads, alert |

### Sync Log

Every sync operation is recorded in `sync_log`:
- What was synced (entity type, ID)
- Direction (always procore_to_local for now)
- Result (success, conflict, error)
- Payload hash (for change detection)

Retention: 90 days, then archived to compressed files.
