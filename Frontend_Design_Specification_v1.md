# STEELSYNC

## AI-Powered Construction Intelligence Platform

# FRONTEND DESIGN SPECIFICATION

### Dashboard Overview & Project Detail Views

Version 1.0 | March 2026

CONFIDENTIAL — FOR INTERNAL USE ONLY

---

## 1. Document Purpose

This specification defines the frontend design for the SteelSync Command Center prototype, covering the Dashboard Overview (portfolio-level) and the Project Detail view (single-project). It formalizes layout patterns, component specifications, interaction behaviors, responsive requirements, and data source mappings that the Operations agent will implement.

This document supersedes the layout and component guidance in the Command Center Design Specification v1.0 where they conflict, while preserving all visual design system decisions (color palette, typography, status language, client theming) from that document. The Ticketized Build Breakdown v1 remains the execution reference for task sequencing.

### 1.1 Scope

- Dashboard Overview: the portfolio-level landing page
- Project Detail: the single-project intelligence workspace
- Shared components: navigation, Radar sidebar, Quick Action Bar
- Responsive behavior at target breakpoints
- Mock data contract for prototype development

Out of scope: Radar full-page view (covered by Command Center Design Spec v1.0), Deep Dive Request form, Database search interface, Reports archive. These views will be specified separately when their build priority arrives.

### 1.2 Relationship to Existing Specifications

| Specification | Relationship |
|---|---|
| Command Center Design Spec v1.0 | Visual design system (Section 4) remains authoritative. Layout patterns (Sections 2–3) are superseded by this document for Dashboard Overview and Project Detail views. |
| Command Center & Radar Feature Spec v1 | Module definitions remain authoritative. This document specifies how those modules render in the two target views. |
| Structured Channel Routing Spec v1.0 | Project-scoped workspace model (Section 3) is adopted. URL structure and navigation model from that spec apply directly. |
| Ticketized Build Breakdown v1 | Task sequence unchanged. This document provides the design detail that tickets CC-1.4, CC-1.5, CC-4.1, CC-4.2, and CC-6.1–6.4 reference. |
| Synthesis Prompt Templates v1 | Output fields from synthesis cycle (cycle_summary, overall_health, item counts) map directly to UI components defined here. |

---

## 2. Information Architecture

### 2.1 Navigation Model

The Command Center uses a project-first navigation model as defined in the Structured Channel Routing Specification v1.0. The entry point is always the Dashboard Overview (portfolio level). Clicking a project health card enters that project's workspace.

#### URL Structure

| View | URL Pattern | Example |
|---|---|---|
| Dashboard Overview | /command-center | portal.acme.steelsync.com/command-center |
| Project Detail | /command-center/project/:slug | portal.acme.steelsync.com/command-center/project/btv5 |
| Radar (full view) | /command-center/radar | portal.acme.steelsync.com/command-center/radar |

All project workspace URLs are bookmarkable. A PM managing three active projects can bookmark all three and open them directly each morning without navigating through the Dashboard Overview.

#### Persistent Elements

| Element | Behavior |
|---|---|
| Top Navigation Bar | Always visible. SteelSync branding (client-overridable), view tabs (Overview, Radar), date/time, user avatar. Fixed position, does not scroll. |
| Radar Sidebar | Visible on both Dashboard Overview and Project Detail. Shows simplified item list (title, project, trend). Click navigates to full Radar view. On Project Detail, filtered to active project only. |
| Quick Action Bar | Visible at bottom of both Dashboard Overview and Project Detail. Four actions: Search Database, Request Deep Dive, View Reports, Add to Radar. |

---

## 3. Dashboard Overview

The Dashboard Overview is the default landing page. It provides a portfolio-level health scan across all active projects. Every element on this page answers the question: "What needs my attention right now?"

### 3.1 Layout Structure

The Dashboard Overview uses a two-column layout: main content area (left, ~75% width) and Radar sidebar (right, ~25% width). The main content area contains, in order from top to bottom:

1. **Greeting headline:** "Good morning, [Name]. [N] critical items across your projects need attention today." Personalized, plain-English, derived from the most recent portfolio-level synthesis.

2. **Project health cards:** One card per active project. Grid layout. Sorted by severity (critical projects first, then amber, then green, then alphabetical within each tier). Cards are the primary navigation element — clicking enters the project workspace.

3. **Live Activity Feed:** Chronological log of system actions across all projects. Each entry: timestamp, plain-language description, project tag, highlight indicator for critical events. Populated from signals table on page load (not WebSocket for pilot).

4. **Quick Action Bar:** Four action buttons in a horizontal row. Search Database, Request Deep Dive, View Reports, Add to Radar.

### 3.2 Project Health Card Specification

Each project health card is a self-contained assessment unit. The card communicates the system's judgment, not raw data. Health status is derived from the synthesis cycle output, never computed on the frontend.

#### Card Anatomy (Top to Bottom)

| Element | Source | Design Notes |
|---|---|---|
| Top border (3px) | overall_health from synthesis | Colored bar: green (#34C77B), amber (#E8A838), or red (#E05555). Fastest visual signal. |
| Project name | projects table | Large, readable. Primary identifier. Left-aligned. |
| Project number | projects table | Smaller, secondary text. Adjacent to name. |
| Status badge | overall_health from synthesis | Plain-language: "On Track," "Needs Attention," "Action Required." |
| Headline summary | cycle_summary from synthesis | Single sentence. Plain English. Most important thing about this project right now. |
| Issue counts | intelligence_items aggregation | Critical count (red), High count (amber), Watch count (default text). Secondary information. |
| Confidence indicator | Data source completeness | e.g., "High confidence — 5 sources active" or "Limited data — daily logs not synced." |
| Last synthesis timestamp | synthesis_cycles table | Footer element. Subtle. |

**Empty state:** If no synthesis cycles have run for a project, the card shows the project name with "Awaiting first analysis" and a neutral gray indicator. No fake data, no placeholder summaries.

**Sort order:** Projects with critical items first, then by overall_health (red → amber → green), then alphabetically within each tier.

**Grid layout:** 2-up at 1440px, 3-up at 1920px. Cards maintain consistent height within each row via CSS grid auto-rows.

---

## 4. Project Detail View

The Project Detail view is the single-project intelligence workspace. This is the screen where SteelSync proves its value. When a VP of Operations clicks into a project during a demo, every element on this screen must justify the product's existence in one glance.

The Project Detail view uses a horizontal accordion layout with collapsible priority tiers. This pattern was selected over three alternatives (three vertical columns, single chronological feed, and tabbed interface) based on the following criteria:

- Accessibility for non-technical users: a 62-year-old superintendent wearing glasses can see the red bar at the top and know immediately what needs attention without scrolling or learning a filter system.
- Scalability: handles any item count gracefully. Empty tiers collapse to a single bar. Dense tiers expand without layout breakage.
- Responsive behavior: horizontal bars adapt to any screen width without requiring layout restructuring at breakpoints.
- Priority-first scanning: the PM reads top-to-bottom in urgency order. Action Required is always at the top, always visible.

### 4.1 Layout Structure

The Project Detail view uses a two-column layout: main content area (left, ~75% width) and Radar sidebar (right, ~25% width). The Radar sidebar is filtered to show only items associated with the active project.

The main content area contains, in order from top to bottom:

1. **Project header bar:** Breadcrumb ("← All projects"), status dot, project name, project number, status badge. Fixed at top of content area.

2. **Synthesis summary banner:** LLM-generated summary from the most recent synthesis cycle. Static text until the next cycle runs. Includes: welcome greeting, cycle timestamp, item count requiring attention, headline assessment. Left border colored by project status. Typewriter animation on initial load for demo polish.

3. **Stats bar:** Horizontal row of compact stat cards. Quick-reference context, not the main event. Fields: Critical item count, High item count, Open RFIs, Overdue RFIs, Open Submittals, Daily Log status, Completion percentage. All derived from Procore data and intelligence item aggregation.

4. **Intelligence tiers (horizontal accordion):** Three collapsible priority sections. This is the core of the view. See Section 4.2 for detailed specification.

5. **Quick Action Bar:** Identical to Dashboard Overview. All actions are automatically scoped to the active project (per Structured Channel Routing Spec v1.0, Section 3.3).

### 4.2 Horizontal Accordion — Intelligence Tiers

The intelligence feed is organized into three collapsible priority tiers. Each tier is a full-width horizontal bar with a colored header that expands to reveal intelligence item cards.

#### Tier Definitions

| Tier | Header Color | Label | Default State | Contains |
|---|---|---|---|---|
| 1 — Critical | Red (#E05555 bg) | Action required | Expanded | Intelligence items with severity = critical. These require PM action. |
| 2 — High | Amber (#E8A838 bg) | Attention | Expanded | Intelligence items with severity = high. Heating up but not yet critical. |
| 3 — Watch | Blue (#4A90D9 bg) | Tracking | Collapsed | Intelligence items with severity = watch/low. Patterns, trends, monitoring items. |

Default state rationale: the superintendent opens the page and sees the red and amber items immediately. Watch items are available but not competing for attention. If the PM wants to review trends, one click expands the Tracking tier.

#### Tier Header Specification

- Full width of the main content area
- Left border: 4px solid, colored by tier (red/amber/blue)
- Background: light tinted version of tier color
- Content: tier label (left-aligned, 14px bold), item count (right-aligned, 13px bold), chevron indicator (right, rotates 90° when open)
- Click anywhere on the header bar to toggle expand/collapse
- Height: 40–44px. Must be large enough to tap on a tablet.
- **Zero-item state:** If a tier has zero items, the header still renders with "0 items." The tier body is empty but the header provides instant status confirmation. A red bar showing "0 items" tells the super everything is fine — without him opening anything.

#### Tier Body Specification

- Appears below the header when expanded
- Contains intelligence item cards in a 2-column grid (see Section 4.3)
- 2-column grid at 1440px+; collapses to single-column below 1280px
- Padding: 10–14px inside the tier body
- Light border on sides and bottom to visually contain the cards
- Smooth expand/collapse animation (200ms ease-out) for polish

### 4.3 Intelligence Item Card

Intelligence item cards are the core unit of value in SteelSync. They follow the two-layer expand/collapse principle from the Command Center Design Spec v1.0: surface for scanning, detail for understanding.

#### Surface Layer (Always Visible)

| Element | Source | Design Notes |
|---|---|---|
| Left border (3px) | severity | Red, amber, or blue. Matches parent tier color. |
| Severity badge | severity | Pill: "Action required," "Attention," or "Watch." Uses status background colors. |
| Category badge | category | Gray pill. One of: Schedule, Manpower, Drawings, Procurement, Submittals, Compliance. |
| Title | title field | 13px bold. Plain-language headline. Maximum two lines. |
| Summary | summary field | 12px secondary text. 1–2 sentences expanding on the title. Maximum three lines on surface. |
| Metadata line | Multiple sources | Source count ("3 sources"), timestamp ("12h ago"), trend indicator ("↑ Escalating," "→ Stable," "↓ Improving"). Tertiary text color. |

#### Detail Layer (Expanded on Click)

Clicking anywhere on the card surface expands the detail layer below the metadata line. The detail layer contains:

- Full summary paragraph: the complete analytical narrative from the synthesis cycle. May be 3–5 sentences.
- Evidence chain: a list of source documents that contributed to this intelligence item. Each entry shows: document type icon (RFI, submittal, daily log, email, drawing), document title/number, date, and a clickable link that opens the source in Procore (new tab).
- Recommended actions: plain-language suggestions generated by the synthesis cycle. Displayed as a short list.
- Technical metadata: intelligence type (Convergence, Contradiction, Pattern Match, Decay Detection, Emerging Risk, Watch Item), confidence percentage, trend indicator with direction, last updated timestamp.
- Feedback buttons: "Useful," "Not Useful," "Already Known." Write to intelligence_item_feedback table. Simple toggle, no confirmation dialog.

**Card interaction:** Only one card within a tier may be expanded at a time. Expanding a new card collapses the previously expanded card. This prevents the tier from becoming an overwhelming wall of expanded detail.

### 4.4 Radar Sidebar (Project-Filtered)

The Radar sidebar on the Project Detail view shows only Radar items associated with the active project. The sidebar is identical in structure to the Dashboard Overview sidebar but filtered by project_id.

- Each item shows: title, priority color (left border), trend indicator
- Clicking a Radar item navigates to the full Radar view with that item focused
- If a Radar item relates to an intelligence item in the main content area, both share the same evidence chain. The connection is implicit through shared signal data, not a visual cross-link on the surface.

---

## 5. Shared Components

### 5.1 Quick Action Bar

| Action | Function | Scope Behavior |
|---|---|---|
| Search Database | Cross-project institutional memory search | On Dashboard: searches all projects. On Project Detail: pre-filtered to active project with option to expand. |
| Request Deep Dive | Opens structured Deep Dive request form | On Dashboard: includes project selector field. On Project Detail: project field auto-populated and hidden (per Structured Channel Routing Spec v1.0, Section 3.3). |
| View Reports | Report archive and briefing history | On Dashboard: all projects. On Project Detail: filtered to active project. |
| Add to Radar | Navigates to Radar view with intake form open | On Dashboard: includes project selector. On Project Detail: project auto-populated. |

### 5.2 Synthesis Summary Banner

The synthesis summary banner appears on the Project Detail view. It displays the LLM-generated narrative from the most recent synthesis cycle for the active project.

| Element | Source | Notes |
|---|---|---|
| Welcome greeting | User name + synthesis output | "Welcome back [Name]." Personalized. |
| Report timestamp | synthesis_cycles.completed_at | "Last report issued at [time]." |
| Item count | Intelligence item aggregation | "[N] new items require attention." |
| Headline assessment | cycle_summary from synthesis | The most important thing about this project right now. 1–2 sentences. |
| Metadata line | synthesis_cycles + data sources | Next cycle time, confidence level, active source count. |

**Styling:** Left border colored by project overall_health (red/amber/green). Background: surface color (slightly elevated from page). Text: 15px weight 500 for headline, 12px secondary for metadata.

**Typewriter effect:** On initial page load, the headline text types out character by character over ~2 seconds. This is a demo polish feature that reinforces the "AI employee writing you a briefing" positioning. After initial animation, text is static. On subsequent visits within the same session, text appears immediately (no re-animation).

**Empty state:** If no synthesis cycle has run for this project, the banner shows: "Analysis pending — first report will be generated at [next cycle time]." Neutral gray left border.

---

## 6. Responsive Behavior

The Command Center is desktop-first. The two required breakpoints are 1920x1080 (primary development target) and 1440x900 (must be fully functional). Behavior below 1280px is defined for robustness but is not a pilot priority.

| Breakpoint | Health Card Grid | Accordion Card Grid | Radar Sidebar | Stats Bar |
|---|---|---|---|---|
| 1920px+ | 3-up grid | 2-column within tiers | Visible, ~250px | Full labels |
| 1440px | 2-up grid | 2-column within tiers | Visible, ~200px | Full labels |
| 1280px | 2-up grid | Single-column within tiers | Collapsible (toggle button) | Abbreviated labels |
| <1280px | Single-column | Single-column within tiers | Hidden (accessible via nav) | Abbreviated labels |

The horizontal accordion pattern was specifically chosen because it degrades gracefully. The tier headers are always full-width and readable. The card grid inside each tier drops from 2-column to 1-column with a single CSS breakpoint change. No layout restructuring is required at any breakpoint.

---

## 7. Data Source Mapping

The Command Center is a display layer. No LLM calls occur in the frontend. All intelligence processing happens in the backend synthesis cycle. The frontend reads from the PostgreSQL database via REST API endpoints.

| UI Component | API Endpoint | Database Source |
|---|---|---|
| Project health cards | GET /api/dashboard/overview | intelligence_items + synthesis_cycles (most recent per project) |
| Synthesis summary banner | GET /api/projects/:id/synthesis/latest | synthesis_cycles (cycle_summary, overall_health, completed_at) |
| Stats bar | GET /api/projects/:id/stats | Procore sync tables (rfis, submittals, daily_logs) + intelligence_items aggregation |
| Intelligence tier items | GET /api/projects/:id/intelligence-items?include=evidence | intelligence_items with evidence chain join |
| Radar sidebar items | GET /api/projects/:id/radar-items | radar_items + radar_activity (filtered by project_id) |
| Live Activity Feed | GET /api/signals/recent | signals table (most recent N, chronological) |
| Feedback buttons | POST /api/intelligence-items/:id/feedback | Writes to intelligence_item_feedback |

**Prototype note:** For the prototype build phase, all data above will be mocked in the frontend. The mock data contract must match the field names and shapes defined above so the transition to live API endpoints requires only changing the data fetch layer, not the component structure.

---

## 8. Mock Data Contract

The prototype will be built against mock data that matches the shape of the real API responses. This section defines the minimum mock dataset required for a convincing demo.

### 8.1 Projects

- Minimum 3 projects, maximum 5
- At least one red (critical issues), one amber (needs attention), one green (on track)
- Use realistic South Florida construction project names and numbers
- Each project must have a synthesis summary that reads like a real PM briefing

### 8.2 Intelligence Items

- Minimum 8–12 items per project with active issues (red/amber projects)
- Minimum 2–4 items per green project (watch items, compliance tracking)
- Distribution across all six categories: Schedule, Manpower, Drawings, Procurement, Submittals, Compliance
- At least 2 items per project must have a complete evidence chain (3+ source documents) for the expanded detail demo
- Include at least one cross-project pattern item (e.g., "5 similar RFIs across 4 projects")

### 8.3 Radar Items

- Minimum 3–5 Radar items per project
- At least one per priority tier (Critical, High, Watch)
- Include trend indicators: at least one Escalating, one Stable, one Improving

### 8.4 Live Activity Feed

- Minimum 15–20 entries across all projects
- Include: RFI opened, submittal uploaded, email ingested, drawing revision detected, daily log processed
- At least 2 entries should be highlighted as critical events
- Timestamps spanning the current day (realistic working hours)

---

## 9. Visual Design Alignment

All visual design tokens remain as defined in the Command Center Design Specification v1.0, Section 4. This section restates only the decisions that directly affect the two views specified in this document.

### 9.1 Color Application to New Components

| Component | Color Treatment |
|---|---|
| Accordion tier header (red) | Background: #E05555 at 15% opacity. Left border: #E05555 solid 4px. Text: #E05555. |
| Accordion tier header (amber) | Background: #E8A838 at 15% opacity. Left border: #E8A838 solid 4px. Text: #E8A838. |
| Accordion tier header (blue) | Background: #4A90D9 at 15% opacity. Left border: #4A90D9 solid 4px. Text: #4A90D9. |
| Intelligence card left border | 3px solid, color matches severity: #E05555 (critical), #E8A838 (high), #4A90D9 (watch). |
| Stats bar cards | Background: surface color (#161D26). No border. Text: primary for values, secondary for labels. Critical/overdue counts use red text. |
| Synthesis banner | Background: surface color. Left border: 3px solid, matches overall_health color. |

### 9.2 Component Naming Convention

Per the Command Center Design Spec v1.0, Section 6.1: UI is structured around intelligence workflows. Component names must reflect the domain, not generic patterns.

| Correct | Incorrect |
|---|---|
| IntelligenceTier | AccordionPanel |
| IntelligenceCard | GenericCard |
| SynthesisBanner | AlertBanner |
| ProjectHealthCard | StatusCard |
| EvidenceChain | LinkList |
| RadarSidebar | NotificationPanel |

---

## 10. Design Decisions Log

The following decisions were made during the design session of March 12, 2026, and represent binding architectural choices for implementation.

### 10.1 Layout Pattern Selection

**Decision:** Horizontal accordion with collapsible priority tiers for Project Detail view.

**Alternatives evaluated:** Three vertical columns (Moby's initial wireframe concept), single chronological feed with filter bar, tabbed interface.

**Selection rationale:** The horizontal accordion was selected because it provides instant priority scanning without scrolling (the superintendent sees red/amber bars at the top), scales to any item count (empty tiers collapse to a single bar, dense tiers expand without layout breakage), degrades gracefully at all screen sizes (bars are always full-width), and preserves Moby's original three-tier priority concept (Action Required / High Priority / Tracking Trends) in a more space-efficient format.

### 10.2 Rejected Alternatives

#### Three Vertical Columns

Moby's initial wireframe placed Recommended Action Items, High Priority, and Tracking Trends in three side-by-side columns. This provided excellent spatial awareness (all three tiers visible at once) but created horizontal space pressure at 1440px, required scrolling within individual columns when item count exceeded 4–5 per tier, and needed a complete layout restructure below 1280px.

#### Single Chronological Feed

A single vertical feed of all intelligence items, grouped by severity with section dividers and a filter bar. This handled any item count gracefully and worked at any screen width, but required the user to learn the filter system, created excessive scrolling for users who only care about critical items, and lacked the instant visual priority signal of the colored tier headers.

### 10.3 Accordion Default State

**Decision:** Action Required and Attention tiers open by default. Tracking tier collapsed by default.

**Rationale:** Optimized for the most common use case: the PM or superintendent opens the page to see what needs their attention right now. Watch items are important but not urgent — they should be available but not competing for screen real estate against critical and high items.

### 10.4 Card Grid Within Tiers

**Decision:** 2-column card grid inside expanded tiers at 1440px+, single-column below 1280px.

**Rationale:** Balances information density (two cards visible per row) with readability (each card has sufficient width for its text content). Single-column fallback ensures no card text is truncated at narrow viewports.

### 10.5 Single-Card Expansion Constraint

**Decision:** Only one intelligence item card may be expanded within a tier at any time.

**Rationale:** Prevents the tier body from becoming an overwhelming wall of expanded detail. Forces the user to focus on one item's evidence chain before moving to the next. This is the correct behavior for a triage workflow.

---

## 11. Implementation Notes for Operations

### 11.1 Build Sequence

This spec covers tickets CC-1.4, CC-1.5, CC-4.1, CC-4.2, and CC-6.1–6.4 from the Ticketized Build Breakdown. The recommended build order within this spec's scope:

1. **Layout shell:** Top nav, routing (/command-center, /command-center/project/:slug), two-column layout with Radar sidebar container.
2. **Dashboard Overview:** Greeting headline, project health card grid (mock data), Quick Action Bar.
3. **Project Detail — structure:** Project header, synthesis banner, stats bar, accordion tier headers with expand/collapse.
4. **Project Detail — cards:** Intelligence item cards (surface layer) in 2-column grid within tiers.
5. **Card expansion:** Detail layer with evidence chain, recommended actions, feedback buttons.
6. **Radar sidebar:** Populate both Dashboard and Project Detail sidebars. Project filtering for detail view.
7. **Live Activity Feed:** Dashboard Overview only. Chronological list with project tags.
8. **Polish:** Typewriter effect on synthesis banner, hover states, transitions, responsive breakpoints, empty states, loading states.

### 11.2 Technology Constraints

- Framework: React with Vite. Tailwind CSS for styling. Confirmed by Operations.
- Dark theme is non-negotiable for brand identity. Use the color palette from Command Center Design Spec v1.0, Section 4.2.
- Font: DM Sans (primary), Segoe UI / system-ui / sans-serif (fallback).
- Desktop-first. Functional at 1920x1080 and 1440x900. No mobile optimization for pilot.
- No WebSocket for pilot. All data loaded on page load or on navigation. Polling acceptable for near-real-time feel.
- No LLM calls from the frontend. All intelligence is pre-computed by the backend synthesis cycle.

### 11.3 Acceptance Criteria

- Dashboard Overview renders with mock project health cards sorted by severity
- Clicking a health card navigates to the Project Detail view for that project
- Project Detail displays synthesis banner, stats bar, and three accordion tiers
- Accordion tiers expand/collapse on click with smooth animation
- Intelligence cards display surface layer; clicking expands detail layer
- Only one card expanded per tier at a time
- Radar sidebar shows project-filtered items on Project Detail
- All states handled: loading, empty, error
- No broken layouts at 1920x1080 and 1440x900
- No console errors on initial load or navigation
- Color palette consistent across all components
- Demo-ready: a construction executive can look at it and understand what they are seeing

---

## Appendix: Document Control

| Field | Value |
|---|---|
| Document | Frontend Design Specification |
| Version | 1.0 |
| Date | March 12, 2026 |
| Author | HQ (Claude Opus) — VP / CTO |
| Approved By | Moby — CEO |
| Classification | Internal — Founders Only |
| Status | Approved for Implementation |
| Dependencies | Command Center Design Spec v1.0, Command Center & Radar Feature Spec v1, Structured Channel Routing Spec v1.0, Ticketized Build Breakdown v1, Synthesis Prompt Templates v1 |
