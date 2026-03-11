# CLAUDE.md — SteelSync Development Context

## What This Project Is

SteelSync is an AI-powered construction intelligence platform. It functions as a 24/7 virtual Senior Project Manager — a "private AI employee" for mid-to-large General Contractors. It connects to a client's full project history through a dedicated, company-specific database and delivers cross-project pattern recognition, proactive risk identification, and institutional memory.

**This is an intelligence layer, not a task automation tool.** All outputs are structured reports (headers, findings, recommendations, sources). The system never asks clarifying questions — it states assumptions and invites resubmission.

**Target customer:** Boomer executives at mid-to-large GCs ($50M–$500M+ annual revenue), initially in South Florida.

## Repository Structure

There are two repos that together form the platform:

- **Procore-Instrumentality-Project** — Application code: microservices, database schemas, agent configurations, integration logic. Being rebranded to SteelSync.
- **NERV Deploy** — Docker Compose configuration, environment files, deployment scripts, infrastructure.

Both repos use legacy Evangelion-themed naming (NERV, EVA, SOUL, etc.) that is being replaced with SteelSync branding. When creating new code, always use SteelSync naming conventions. When modifying existing code, rename Evangelion references to SteelSync equivalents where practical.

## Architecture

### Three-Layer Platform

| Layer | Purpose |
|-------|---------|
| **Interface** | Command Center (web portal), email intake, Telegram/WhatsApp notifications |
| **Intelligence** | Signal generation, periodic synthesis cycles, Radar monitoring, structured reports |
| **Data** | PostgreSQL with pgvector, object storage, Procore API sync, Smartsheet adapter |

### Docker Services (15 services via Docker Compose)

The platform runs as a containerized microservice stack. All services communicate over HTTP and Redis. Key services include: webhook-receiver, security gateway (eva-sentry), notification-engine, drawing-intel, token-guardian, portal, embedding-pipeline, extraction-service, classification-service, and PostgreSQL with pgvector.

### Database

PostgreSQL with 31-table schema including pgvector for embeddings. The database is a derived analytical layer — not the system of record. Source data persists in Procore/OneDrive/Smartsheet regardless of SteelSync state.

### Model Strategy (Three Tiers)

| Tier | Model | Use |
|------|-------|-----|
| **Complex** | Claude Opus | Drawing interpretation, cross-project synthesis, deep analysis |
| **Standard** | Claude Sonnet | Routine analytical tasks, submittal review, change order analysis |
| **Local** | DeepSeek via Ollama | Classification, triage, routing, metadata tagging — high volume, near-zero cost |

The local LLM handles clean structured inputs (Procore API JSON, pre-extracted text, routing). Drawings and complex PDFs bypass local processing and route to Sonnet/Opus.

## Key Product Concepts

**Command Center** — The primary operational interface (web portal). Displays active intelligence items, watch items, contradictions, newly reinforced risks, and what changed since the prior synthesis cycle.

**Radar** — Flagship feature. Automated monitoring system that flags high-priority concerns across active projects. Ships automated from day one with visible confidence scores for user feedback. Uses a tiered pipeline: lightweight model for first-pass filtering, then Opus for judgment calls.

**Intelligence Items** — First-class outputs of the synthesis pipeline. Include: id, project_id, item_type, title, summary, severity, confidence, status, source_evidence_count, recommended_attention_level. Status values: new, active, watch, downgraded, resolved, archived.

**Signals** — First-class objects generated from ingested data. Categories defined in Signal Type Scoping Specification: A (Status Change), B (Contradiction), C (Reinforcement), D (Document Significance), E (Actor Pattern), F (Cross-Project Flag).

**Synthesis Cycles** — Periodic analysis runs: Morning Briefing, Midday Checkpoint, End-of-Day Consolidation, and Escalation Review. Each cycle receives new signals, active signals, unresolved intelligence items, and project state — produces new/updated intelligence items and briefing summaries.

**Baseline Establishment Mode** — For new client onboarding. Historical ingest builds context without flooding users with alerts on every historical artifact.

## Integration Points

**Procore API** — Primary data source. Webhook sync for real-time events. OAuth tokens managed by Token Guardian with AES-256-GCM encryption and automatic refresh.

**Smartsheet** — Secondary adapter for clients using Smartsheet alongside Procore.

**Anthropic API** — Cloud inference for Sonnet and Opus calls. Direct API key authentication.

**Ollama** — Local LLM endpoint running on the same server.

## Development Conventions

### Working Style
- **Ask before doing anything risky** (destructive operations, schema changes, security modifications, anything affecting existing integrations). Otherwise, just execute.
- When making changes, consider the big picture — how does this change affect other services, the database schema, the deployment config?
- All new code should include appropriate error handling and logging.
- Use structured JSON for inter-service communication.

### Naming
- New code uses `steelsync-` prefix for services, `SteelSync` for display names
- Database tables use snake_case
- API endpoints use kebab-case
- Environment variables use SCREAMING_SNAKE_CASE

### Testing
- Run existing E2E tests before and after changes: confirm nothing breaks
- New services should include basic health check endpoints
- Docker services should have proper healthcheck definitions

### Git
- Commit messages should be clear and descriptive
- One logical change per commit — don't bundle unrelated changes
- Always confirm current branch before committing

### Code Quality
- Python: follow PEP 8, use type hints
- JavaScript/TypeScript: use const/let (never var), async/await over raw promises
- SQL: use parameterized queries — never string interpolation
- Docker: multi-stage builds where appropriate, minimize image size

## Key Specification Documents

These documents (maintained in the Claude Project HQ) define the architecture and are the source of truth:

- **Business & Architecture Specification v1** — Overall platform architecture, pricing model, deployment strategy
- **Intelligence Layer System Design v1** — Signal → synthesis → intelligence item pipeline
- **Command Center Design Specification v1** — Primary interface design
- **Command Center & Radar Specification v1** — Radar feature design and integration
- **Signal Type Scoping Specification v1** — Signal taxonomy and model tier assignments
- **Document Pipeline Integration Point Specification v1** — Ingestion paths (webhook vs document pipeline)
- **Model Strategy & Cost Analysis v1** — Two-tier model strategy, cost projections
- **Synthesis Prompt Templates v1** — Morning briefing, midday checkpoint, end-of-day, escalation review
- **Agent Framework Orchestration Specification v1** — Deployment model, agent loop architecture
- **Command Center Implementation Plan v2** — Nine-task, four-phase build plan

## Current Priority

**Working end-to-end proof of concept** — sufficient to validate the concept before further investment. Immediate build focus:

1. **Command Center** — primary operational interface
2. **Radar** — automated monitoring with confidence scoring
3. **Single synthesis cycle** — prove the signal → synthesis → intelligence item pipeline works against real Procore sandbox data

## Hardware

- **ThinkPad X1 Carbon** (64GB RAM, Manjaro Linux) — Primary development and deployment server
- **Windows 11 Desktop** (Ryzen 7 9800X3D, RX 7900 XTX / 24GB VRAM) — Local LLM testing with Ollama
