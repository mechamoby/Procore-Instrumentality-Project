# EVA Product Lineup
> Source: Nick's product theory doc (2026-02-19)

## Terminology
- **SEELE** — Our company (code name). Handles pre-deployment: database setup, history ingestion, structuring
- **NERV** — The client's dedicated on-prem server + command station
- **EVAs** — Individual AI agents, each specialized for a specific role

## EVA-00: The Master Clerk & Project Historian ⭐ FIRST PRODUCT
- Primary agent on every NERV deployment
- Manages the structured local database of ALL client historical data:
  - Past project drawings, RFIs, submittals, schedules
  - Meeting agendas & minutes
  - All data parsed, categorized, stored locally for instant retrieval
- Can answer any question by cross-referencing the structured DB
- Near-zero loading time (local data, no cloud round-trips)
- SEELE + EVA-00 jointly manage and structure the database
- **This is the foundation all other EVAs build on**

## EVA-01: Submittal Agent
- 24/7 submittal manager with NERV access
- Workflow:
  1. User sends submittal document directly to EVA-01
  2. Initial compliance review against: drawings, contract docs, FL Building Code, ADA, FHA, FGBC
  3. Alerts user of conflicts
  4. Cross-references similar submittals from past projects via NERV
  5. With approval: creates draft in Procore, uploads docs, fills fields, sets workflow
  6. User reviews and publishes
  7. EVA-01 notifies reviewers via Procore Email tool
  8. Tracks and manages: sends reminders to design team at configured intervals
- Advanced capabilities:
  - Uses OPS + daily reports/logs/photos for updated on-site date estimates
  - With user-provided lead times → generates Key Material Tracker Logs
  - Analytics, data, and graphs from current + historical submittal data

## EVA-02: RFI Agent
- 24/7 RFI manager with NERV access
- Proactive analysis:
  1. Analyzes drawings for contradictions, coordination gaps, missing info
  2. Cross-checks against contract docs, FL Building Code, ADA, FHA, FGBC
  3. Cross-references similar project types via NERV historical RFI data
  4. Produces detailed list of potential RFIs with references
- With approval: drafts RFIs in Procore with all fields + docs
- User publishes, EVA-02 tracks + sends reminders to design team

## Key Insights
- EVA-00 is the moat — the structured historical database is what makes everything else powerful
- Each EVA is a separate agent (modular pricing, sell individually)
- All EVAs share access to NERV (the local knowledge base)
- Compliance checking (FL codes, ADA, FHA, FGBC) is a differentiator across all agents
- The local/on-prem model means data never leaves the client's building
