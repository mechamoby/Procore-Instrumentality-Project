# The Evangelion Project (EVA)

**Codename:** Evangelion Project / EVA
**Status:** Active Development
**Founded:** 2026-02-17
**Founders:** Nick Stula + Moby 🐋

---

## Mission
Build and sell locally-deployed, security-first AI agents specialized for the construction industry.

## Business Model
- Dedicated mini-servers deployed on-site at each client
- Data never leaves the client's building
- Hybrid local/cloud AI processing
- Hardware lease + monthly agent subscription + maintenance

## Target Market
- General Contractors & Developers in South Florida
- Executive-level decision makers (VP, C-suite)
- Multi-family / large commercial projects

## Phase 1 Target
- Procore-integrated daily reporting agent
- DocuSign automation
- Single killer demo that sells itself

## Competitive Advantages
1. Nick's 10+ years of construction industry expertise & relationships
2. Local-first security model ("your data never leaves your building")
3. Physical hardware = trust + stickiness
4. Niche specialization vs generic AI tools
5. First mover in OpenClaw construction agents

## Pricing (Draft)
- Setup fee: $2,000-3,000 (includes hardware)
- Monthly service: $3,000-5,000/agent
- Maintenance & updates: included

## Client Onboarding Protocol

### Pre-Visit Preparation
- Pre-configure NERV box with client's company info, project list, Procore sandbox credentials
- Load latest EVA agent builds + NERV interface
- Prepare demo dataset relevant to client's project type

### On-Site Deployment (Day 1)
1. **Hardware setup** — Connect NERV box to client network, verify connectivity
2. **Procore Drive bulk import** — Install Procore Drive on client workstation temporarily. Bulk-download all existing project documents (specs, plans, contracts, historical submittals, photos) directly to NERV box. This seeds EVA-00's knowledge base on day one without burning API calls or AI tokens.
3. **API credential configuration** — Set up Procore OAuth (private integration path). Configure live API access for EVA-01 (submittals), EVA-02 (RFIs), EVA-00 (historian).
4. **Remove Procore Drive** — Uninstall Drive from client machine. All ongoing operations run through API. Drive is a one-time moving truck, not the daily driver.
5. **Live demo** — Run EVA-01 on a real submittal from their project. Show review → approval → Procore draft in real time.
6. **Handoff** — Walk client through NERV interface, set up their login, confirm Telegram/notification channel.

### Post-Visit (Week 1)
- Monitor agent performance remotely
- Fine-tune EVA responses based on client's project-specific terminology
- Schedule follow-up call at day 3 and day 7

### Why Procore Drive for Onboarding
- **Speed**: Bulk download is faster than API pagination for initial data load
- **Zero AI cost**: Raw file transfer, no token burn
- **Completeness**: Grabs entire document library including historical files
- **No ongoing dependency**: Drive is removed after day 1. API handles everything live.
- **Source**: MAGI intelligence brief (2026-02-24) confirmed Drive's only viable use case is bulk onboarding

## Codename Origin
Evangelion — the pilots (agents) do the work, we run NERV (the operation) from behind the scenes.
