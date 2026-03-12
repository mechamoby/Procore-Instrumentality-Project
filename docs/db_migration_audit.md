# Database Migration Audit

## Date: 2026-03-12T02:10:00Z
## Database: steelsync_migration_test (temporary, created for this audit)
## Source: /home/moby/.openclaw/workspace/nerv-deploy-repo/database/

## Summary

- Total migration files: **19**
- Successful: **19**
- Failed: **0**
- Base schema tables (from schema.sql): **24**
- Resulting tables after all migrations: **58**
- Expected tables per spec: **31**
- Schema drift detected: **YES** — significantly more tables than the documented 31
- pgvector extension: **Installed (v0.8.2)**

## Notes on "31-Table Specification"

The CLAUDE.md documentation states "PostgreSQL with 31-table schema." This appears to refer to the **original base schema** (24 tables from `schema.sql`) plus the first few migration additions (tables from migrations 001-006), totaling roughly 31 tables. The subsequent pipeline phases (migrations 007-019) added 27 additional tables, bringing the total to 58. The "31-table" count in the documentation is outdated and should be updated to reflect the current state.

## Base Schema (schema.sql)

The base schema creates 24 tables before any migrations run:

| # | Table Name | Purpose |
|---|---|---|
| 1 | audit_log | System audit trail |
| 2 | change_orders | Procore change orders |
| 3 | companies | Company records |
| 4 | contacts | Contact records |
| 5 | daily_reports | Procore daily reports |
| 6 | document_chunks | Vector embeddings for semantic search |
| 7 | documents | Core document store |
| 8 | drawing_cad_data | CAD metadata for drawings |
| 9 | drawing_revisions | Drawing revision tracking |
| 10 | drawings | Drawing records |
| 11 | meeting_items | Meeting agenda/action items |
| 12 | meetings | Meeting records |
| 13 | photos | Procore photos |
| 14 | project_companies | Project-company associations |
| 15 | projects | Core project records |
| 16 | rfi_responses | RFI response records |
| 17 | rfis | Request for Information records |
| 18 | schedule_activities | Schedule activity records |
| 19 | schedules | Project schedules |
| 20 | spec_sections | Specification sections |
| 21 | submittal_workflow_history | Submittal workflow audit |
| 22 | submittals | Submittal records |
| 23 | sync_cursors | Procore API sync state |
| 24 | sync_log | Sync operation log |

## Migration Execution Log

| # | Filename | Size | Result | Objects Created/Modified |
|---|---|---|---|---|
| 1 | 001_webhook_events.sql | 939 B | SUCCESS | webhook_events table + 3 indexes |
| 2 | 002_document_chunks.sql | 1,410 B | SUCCESS | Skipped (table already in schema.sql), added 1 new index |
| 3 | 003_oauth_tokens.sql | 4,499 B | SUCCESS | oauth_tokens, oauth_refresh_log tables + indexes + trigger |
| 4 | 004_smartsheet.sql | 4,111 B | SUCCESS | smartsheet_mappings, smartsheet_row_map, smartsheet_sync_log tables |
| 5 | 005_portal_auth.sql | 3,420 B | SUCCESS | portal_users, portal_sessions, portal_auth_log tables |
| 6 | 006_outbound_gate.sql | 2,440 B | SUCCESS | verified_contacts, outbound_audit_log, project_domain_allowlists tables |
| 7 | 007_data_extraction.sql | 3,501 B | SUCCESS | extraction_runs, document_processing_runs tables + ALTER on documents |
| 8 | 008_email_extraction.sql | 5,759 B | SUCCESS | emails, email_attachments tables + project_sync_state table |
| 9 | 009_pipeline_phase1_foundations.sql | 4,363 B | SUCCESS | ALTER TABLE additions to documents, projects, etc. |
| 10 | 010_pipeline_phase2_sentry_results.sql | 1,836 B | SUCCESS | sentry_results table + 5 indexes |
| 11 | 011_pipeline_phase3_extraction.sql | 2,080 B | SUCCESS | document_extractions table + 4 indexes |
| 12 | 012_pipeline_phase4_classifications.sql | 2,174 B | SUCCESS | document_classifications table + 4 indexes |
| 13 | 013_pipeline_phase5_project_matching.sql | 2,411 B | SUCCESS | document_project_matches table + 5 indexes |
| 14 | 014_pipeline_phase6_routing.sql | 2,008 B | SUCCESS | document_routes table + 4 indexes |
| 15 | 015_pipeline_phase6_review_queue.sql | 3,120 B | SUCCESS | review_queue_items table + 6 indexes |
| 16 | 016_pipeline_phase7_retrieval.sql | 952 B | SUCCESS | ALTER TABLE documents ADD retrieval_status + index |
| 17 | 017_pipeline_phase7_relationships.sql | 2,376 B | SUCCESS | document_relationships table + 3 indexes |
| 18 | 018_intelligence_layer_schema.sql | 8,749 B | SUCCESS | signals, intelligence_items, intelligence_item_evidence, synthesis_cycles, working_memory_state, reinforcement_candidates tables |
| 19 | 019_radar_feedback_onboarding.sql | 6,123 B | SUCCESS | radar_items, radar_activity, radar_document_links, intelligence_item_feedback tables + ALTER projects ADD onboarding_phase |

## Full Table Inventory After All Migrations (58 tables)

| # | Table Name | Origin |
|---|---|---|
| 1 | audit_log | schema.sql |
| 2 | change_orders | schema.sql |
| 3 | companies | schema.sql |
| 4 | contacts | schema.sql |
| 5 | daily_reports | schema.sql |
| 6 | document_chunks | schema.sql |
| 7 | document_classifications | migration 012 |
| 8 | document_extractions | migration 011 |
| 9 | document_processing_runs | migration 007 |
| 10 | document_project_matches | migration 013 |
| 11 | document_relationships | migration 017 |
| 12 | document_routes | migration 014 |
| 13 | documents | schema.sql |
| 14 | drawing_cad_data | schema.sql |
| 15 | drawing_revisions | schema.sql |
| 16 | drawings | schema.sql |
| 17 | email_attachments | migration 008 |
| 18 | emails | migration 008 |
| 19 | extraction_runs | migration 007 |
| 20 | intelligence_item_evidence | migration 018 |
| 21 | intelligence_item_feedback | migration 019 |
| 22 | intelligence_items | migration 018 |
| 23 | meeting_items | schema.sql |
| 24 | meetings | schema.sql |
| 25 | oauth_refresh_log | migration 003 |
| 26 | oauth_tokens | migration 003 |
| 27 | outbound_audit_log | migration 006 |
| 28 | photos | schema.sql |
| 29 | portal_auth_log | migration 005 |
| 30 | portal_sessions | migration 005 |
| 31 | portal_users | migration 005 |
| 32 | project_companies | schema.sql |
| 33 | project_domain_allowlists | migration 006 |
| 34 | project_sync_state | migration 008 |
| 35 | projects | schema.sql |
| 36 | radar_activity | migration 019 |
| 37 | radar_document_links | migration 019 |
| 38 | radar_items | migration 019 |
| 39 | reinforcement_candidates | migration 018 |
| 40 | review_queue_items | migration 015 |
| 41 | rfi_responses | schema.sql |
| 42 | rfis | schema.sql |
| 43 | schedule_activities | schema.sql |
| 44 | schedules | schema.sql |
| 45 | sentry_results | migration 010 |
| 46 | signals | migration 018 |
| 47 | smartsheet_mappings | migration 004 |
| 48 | smartsheet_row_map | migration 004 |
| 49 | smartsheet_sync_log | migration 004 |
| 50 | spec_sections | schema.sql |
| 51 | submittal_workflow_history | schema.sql |
| 52 | submittals | schema.sql |
| 53 | sync_cursors | schema.sql |
| 54 | sync_log | schema.sql |
| 55 | synthesis_cycles | migration 018 |
| 56 | verified_contacts | migration 006 |
| 57 | webhook_events | migration 001 |
| 58 | working_memory_state | migration 018 |

## Schema Comparison: Test (Migrations) vs Production (nerv)

Production database `nerv` has **44 tables**. Test database from clean migrations has **58 tables**.

### Tables in test but NOT in production (16 tables — migrations not yet applied)

| Table | Migration | Notes |
|---|---|---|
| document_classifications | 012 | Pipeline Phase 4 — not applied to prod |
| document_extractions | 011 | Pipeline Phase 3 — not applied to prod |
| document_project_matches | 013 | Pipeline Phase 5 — not applied to prod |
| document_relationships | 017 | Pipeline Phase 7 — not applied to prod |
| document_routes | 014 | Pipeline Phase 6 — not applied to prod |
| intelligence_item_evidence | 018 | Intelligence layer — not applied to prod |
| intelligence_item_feedback | 019 | Radar/feedback — not applied to prod |
| intelligence_items | 018 | Intelligence layer — not applied to prod |
| radar_activity | 019 | Radar — not applied to prod |
| radar_document_links | 019 | Radar — not applied to prod |
| radar_items | 019 | Radar — not applied to prod |
| reinforcement_candidates | 018 | Intelligence layer — not applied to prod |
| review_queue_items | 015 | Pipeline Phase 6 — not applied to prod |
| signals | 018 | Intelligence layer — not applied to prod |
| synthesis_cycles | 018 | Intelligence layer — not applied to prod |
| working_memory_state | 018 | Intelligence layer — not applied to prod |

### Tables in production but NOT in test (2 tables — not in any migration)

| Table | Possible Origin |
|---|---|
| notification_preferences | Created manually or by notification-engine service startup, not in any migration file |
| notifications | Created manually or by notification-engine service startup, not in any migration file |

## Duplicate Migration Files

Migrations 007, 008, and 011-018 exist in **two locations**:
- `database/migrations/` (primary — 19 files, 001-019)
- `database/docker-init/sql/migrations/` (subset — 11 files, 007-008 and 011-018)

The `docker-init` copies appear to be duplicates mounted into the container's init directory. Migration 019 is only in `database/migrations/`, suggesting the docker-init copy wasn't updated for the latest migration.

## pgvector Status

- **Extension installed:** YES (v0.8.2)
- **Vector columns found:** 1
  - `document_chunks.embedding` (type: vector)

## Issues Identified

1. **Documentation drift:** CLAUDE.md states "31-table schema" but actual schema produces 58 tables. The documentation should be updated.
2. **Production schema lag:** 16 tables from migrations 011-019 have not been applied to the production database.
3. **Orphan production tables:** 2 tables (notifications, notification_preferences) exist in production but have no migration file — created out-of-band.
4. **Duplicate migration files:** Migrations exist in two directories with the docker-init copy missing migration 019.
5. **No migration tracking:** There is no `schema_migrations` or equivalent tracking table — no way to know which migrations have been applied without comparing table lists.
