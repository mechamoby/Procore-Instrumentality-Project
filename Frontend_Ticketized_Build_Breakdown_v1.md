# STEELSYNC — Frontend Build Breakdown

## Dashboard Overview & Project Detail Views

### Agent Framework Implementation Sequence

Version 1.0 | March 2026

CONFIDENTIAL — FOR INTERNAL USE ONLY

---

## Overview

This document breaks the Frontend Design Specification v1 into discrete, self-contained tickets designed for direct handoff to Claude Code. Each ticket specifies a goal, inputs, expected outputs, agent implementation notes, and acceptance criteria. The format mirrors the Command Center Ticketized Build Breakdown v1 and the Document Pipeline Ticketized Build Breakdown.

This breakdown covers only the frontend prototype build against mock data. It does not cover backend API endpoints, signal generation, or synthesis cycle implementation — those are covered by the Command Center Ticketized Build Breakdown v1 (Phases 1–3).

### Relationship to Existing Documents

- **Frontend Design Specification v1** — the authoritative design reference for every ticket below. When a ticket says "per the spec," it means this document.
- **Command Center Design Spec v1.0** — visual design system (Section 4: color palette, typography, status language) remains authoritative. Layout patterns for Dashboard Overview and Project Detail are superseded by the Frontend Design Spec v1.
- **Command Center Ticketized Build Breakdown v1** — this document replaces tickets CC-1.4, CC-1.5, CC-4.1, CC-4.2, and CC-6.1–6.4 from that breakdown with more granular, design-aligned tickets. All other tickets in that breakdown remain unchanged.
- **Structured Channel Routing Spec v1.0** — URL structure and project-scoped workspace model (Section 3) apply directly to routing and navigation tickets here.

### Ticket Numbering

Tickets use the prefix **FE-** (Frontend) to distinguish from the **CC-** prefix used in the Command Center Ticketized Build Breakdown. The numbering is sequential within phases.

---

## Critical Path

**FE-1.1 → FE-1.2 → FE-2.1 → FE-2.2 → FE-3.1 → FE-3.2 → FE-3.3 → FE-3.4 → FE-4.1 → FE-4.2 → FE-5.1 → FE-5.2**

This is the layout shell through to demo-ready polish. The critical path ensures that each ticket builds on visible, testable output from the previous one.

### Parallel Tracks

**Radar sidebar** (FE-4.1) can start as soon as FE-1.1 is complete — it's a standalone component that plugs into both views.

**Live Activity Feed** (FE-4.2) can start as soon as FE-2.1 is complete — it's a Dashboard Overview component independent of the Project Detail work.

### Estimated Total Effort

8–12 focused agent sessions. Achievable in 1–2 weeks of evening/weekend work.

---

## Phase 1: Foundation

*Build the shell. Get routing working. Establish the mock data layer that every subsequent ticket consumes.*

---

### FE-1.1: Layout Shell & Routing

| Field | Detail |
|-------|--------|
| **Goal** | Create the React application shell with routing, top navigation bar, two-column layout (main + Radar sidebar), and dark theme foundation. This is the skeleton everything else attaches to. |
| **Effort** | 1–2 hours |
| **Inputs** | • Existing portal codebase (React + Vite + Tailwind CSS) |
| | • Frontend Design Spec v1, Section 2.1 (Navigation Model) |
| | • Command Center Design Spec v1.0, Section 4 (Visual Design System — color palette, typography) |
| | • Structured Channel Routing Spec v1.0, Section 3.2 (URL structure) |
| **Expected Outputs** | • React app loads at `/command-center` without errors |
| | • React Router configured: `/command-center` (Dashboard Overview), `/command-center/project/:slug` (Project Detail), `/command-center/radar` (Radar placeholder) |
| | • Top navigation bar: SteelSync logo/wordmark area (left), view tabs — Overview and Radar (center), date/time display and user avatar placeholder (right). Fixed position, does not scroll. |
| | • Two-column layout: main content area (~75% width) and Radar sidebar container (~25% width). Sidebar is a persistent empty container at this stage. |
| | • Dark theme applied: page background #0F1419, surface #161D26, card #1A2332, borders #243040. |
| | • DM Sans font loaded via Google Fonts or local asset. Fallback: Segoe UI, system-ui, sans-serif. |
| | • Basic responsive: layout functional at 1920x1080 and 1440x900. |
| **Agent Notes** | • Use React with Vite. Tailwind CSS for styling. These are confirmed and non-negotiable. |
| | • The dark theme is non-negotiable for brand identity. Use the exact hex values from the Command Center Design Spec v1.0, Section 4.2. |
| | • Set up a simple API service module (`src/services/api.js`) that all components will use. For now it returns mock data. This keeps the data layer in one place so switching to real endpoints later is a single-file change. |
| | • Component naming convention matters. Use domain names: `TopNavBar`, `RadarSidebar`, `MainContent` — not `Header`, `Sidebar`, `Content`. |
| | • The Radar sidebar is an empty container at this stage. It will be populated in FE-4.1. |
| **Acceptance Criteria** | ✓ App loads at `/command-center` with no console errors |
| | ✓ Navigation between routes works (URL updates, correct view renders) |
| | ✓ Dark theme applied consistently — no white flashes, no unstyled elements |
| | ✓ Two-column layout renders correctly at 1920x1080 and 1440x900 |
| | ✓ Top nav bar is fixed and does not scroll with content |

---

### FE-1.2: Mock Data Layer

| Field | Detail |
|-------|--------|
| **Goal** | Create the mock data module that all frontend components consume. This is the single source of truth for the prototype — every component reads from this module, never from hardcoded inline data. |
| **Effort** | 1 hour |
| **Inputs** | • Frontend Design Spec v1, Section 7 (Data Source Mapping) and Section 8 (Mock Data Contract) |
| | • Command Center Design Spec v1.0, Section 4.5 (Status Language) |
| **Expected Outputs** | • `src/data/mockData.js` — a single module exporting all mock data |
| | • **Projects** (3–5): at least one red (action required), one amber (needs attention), one green (on track). Realistic South Florida construction names: e.g., "Brickell Tower V" (BTV5-2024), "FPL Ducbank Relocation" (FPL-DB-2025), "Aventura Medical Center" (AMC-2025). Each project has: id, name, number, client, overall_health (green/amber/red), cycle_summary (1–2 sentence plain-English assessment), completion percentage, contract value, daily log status, open RFI count, overdue RFI count, open submittal count, last synthesis timestamp, confidence level. |
| | • **Intelligence items** (8–12 per red/amber project, 2–4 per green project): each has id, project_id, title, summary (1–2 sentences), full_summary (3–5 sentences for expanded detail), severity (critical/high/watch), category (Schedule/Manpower/Drawings/Procurement/Submittals/Compliance), intelligence_type (Convergence/Contradiction/Pattern Match/Decay Detection/Emerging Risk/Watch Item), confidence_percentage, trend (escalating/stable/improving/resolving), source_count, timestamp, evidence_chain (array of {type, title, date, procore_link}), recommended_actions (array of strings). |
| | • **Radar items** (3–5 per project): each has id, project_id, title, priority (critical/high/watch), trend, last_activity_timestamp. |
| | • **Activity feed entries** (15–20 across all projects): each has id, project_id, project_name, timestamp, description (plain-language), is_critical (boolean). |
| | • Helper functions: `getProjectBySlug(slug)`, `getIntelligenceItemsByProject(projectId)`, `getRadarItemsByProject(projectId)`, `getAllProjects()`, `getRecentActivity()`. |
| **Agent Notes** | • The quality of this mock data directly determines how convincing the demo is. Write the intelligence item summaries as if you are a senior PM briefing an executive. Not "RFI is overdue" — rather "Mechanical rough-in trending 6 days behind schedule. Production rate dropped 22% over 7 days. Drywall impact in 10 days if unchanged." |
| | • Include at least one cross-project pattern item: e.g., "Light pole clarification RFI — 5 similar RFIs issued across 4 projects in the last 2 years. Historical data suggests spec ambiguity." |
| | • Include at least 2 items per red/amber project with a complete evidence chain (3+ source documents) for the expanded detail demo. Evidence entries should reference realistic Procore document types: RFI #047, Submittal #S-2024-089, Daily Log 03/10/2026, Drawing A-3.01 Rev C. |
| | • The cycle_summary for each project should read like the synthesis banner text: "Mechanical rough-in falling behind — drywall impact in 10 days if unchanged." Not "Project has 2 critical issues." |
| | • Do NOT use placeholder text like "Lorem ipsum" or "Sample description." Every string must read like real construction intelligence. |
| **Acceptance Criteria** | ✓ `mockData.js` exports all required data structures |
| | ✓ Helper functions return correct filtered/sorted results |
| | ✓ At least 3 projects with correct severity distribution (1 red, 1 amber, 1 green minimum) |
| | ✓ Intelligence items distributed across all 6 categories |
| | ✓ At least 2 items have full evidence chains with 3+ entries |
| | ✓ All text reads as genuine construction intelligence, not placeholder content |

---

## Phase 2: Dashboard Overview

*Build the portfolio landing page. This is the first screen the user sees every morning.*

---

### FE-2.1: Project Health Cards & Greeting

| Field | Detail |
|-------|--------|
| **Goal** | Build the Dashboard Overview landing page with the personalized greeting headline and project health card grid. Clicking a card navigates to the Project Detail view. |
| **Effort** | 2 hours |
| **Inputs** | • Layout shell from FE-1.1 |
| | • Mock data from FE-1.2 |
| | • Frontend Design Spec v1, Section 3 (Dashboard Overview) — specifically Section 3.1 (Layout Structure) and Section 3.2 (Project Health Card Specification) |
| | • Command Center Design Spec v1.0, Section 3.1 (Project Health Card component spec) |
| **Expected Outputs** | • Greeting headline at top of main content area: "Good morning, [Name]. [N] critical items across your projects need attention today." Derived from mock data aggregation. |
| | • Grid of `ProjectHealthCard` components, one per active project |
| | • Each card displays (top to bottom): 3px colored top border (green/amber/red from overall_health), project name (large, readable), project number (smaller, secondary), status badge ("On Track" / "Needs Attention" / "Action Required"), headline summary (cycle_summary — single sentence, plain English), issue counts (critical in red, high in amber, watch in default text), confidence indicator ("High confidence — 5 sources active"), last synthesis timestamp |
| | • Cards sorted by: critical projects first, then amber, then green, then alphabetical within each tier |
| | • Card grid: 3-up at 1920px, 2-up at 1440px |
| | • Clicking any card navigates to `/command-center/project/:slug` |
| | • Empty state: if no projects exist, display "No active projects. Projects will appear here when data begins syncing." |
| **Agent Notes** | • The health card summary comes directly from the synthesis cycle output (cycle_summary in mock data). Do NOT compute health from raw data on the frontend. The synthesis cycle's judgment IS the health assessment. |
| | • The confidence indicator is a subtle but important trust signal. Show something like "High confidence — 5 data sources active" or "Limited data — daily logs not yet synced." This sets expectations when data is thin. |
| | • Use the SteelSync color palette for status: green = #34C77B, amber = #E8A838, red = #E05555. |
| | • The card should feel substantial, not like a tiny widget. Give it enough height to display the summary comfortably. Card background: #1A2332. Hover: #1F2B3D. |
| | • The greeting should feel personal, not robotic. "Good morning" before noon, "Good afternoon" after. Use the user's name (mock: "Moby"). |
| **Acceptance Criteria** | ✓ Greeting headline renders with correct time-of-day and item count |
| | ✓ Health cards display all required fields with correct data |
| | ✓ Cards sorted by severity (red first, then amber, then green) |
| | ✓ Clicking a card navigates to the correct project detail URL |
| | ✓ Card grid responsive: 3-up at 1920px, 2-up at 1440px |
| | ✓ Empty state displays correctly when no projects exist |

---

### FE-2.2: Quick Action Bar (Dashboard)

| Field | Detail |
|-------|--------|
| **Goal** | Build the Quick Action Bar at the bottom of the Dashboard Overview. Four action buttons in a horizontal row. |
| **Effort** | 30 minutes |
| **Inputs** | • Layout shell from FE-1.1 |
| | • Frontend Design Spec v1, Section 5.1 (Quick Action Bar) |
| **Expected Outputs** | • `QuickActionBar` component with four buttons: Search Database, Request Deep Dive, View Reports, Add to Radar |
| | • Each button: icon (simple SVG or text icon), label, subtitle description |
| | • Buttons are non-functional for prototype — clicking shows a placeholder toast/overlay: "Coming soon — [action name]" |
| | • "Add to Radar" navigates to `/command-center/radar` |
| | • Horizontal layout with equal-width buttons. Background: surface color. Border: standard border color. |
| **Agent Notes** | • Keep this simple. The action bar is a navigation element, not a feature. Don't over-design it. |
| | • The same component will be reused on the Project Detail view (FE-3.4) with project-scoped behavior. Build it as a reusable component that accepts an optional `projectId` prop. When `projectId` is present, the toast message should indicate project scope. |
| **Acceptance Criteria** | ✓ Four action buttons render in a horizontal row |
| | ✓ Buttons are visually consistent with the dark theme |
| | ✓ Clicking any button shows appropriate placeholder feedback |
| | ✓ "Add to Radar" navigates to Radar route |

---

## Phase 3: Project Detail View

*This is the money screen. Every ticket in this phase builds toward the moment a VP of Operations clicks into a project and leans forward.*

---

### FE-3.1: Project Header & Synthesis Banner

| Field | Detail |
|-------|--------|
| **Goal** | Build the top section of the Project Detail view: breadcrumb navigation, project header with status, synthesis summary banner, and stats bar. |
| **Effort** | 1.5 hours |
| **Inputs** | • Layout shell from FE-1.1 |
| | • Mock data from FE-1.2 |
| | • Frontend Design Spec v1, Section 4.1 (Layout Structure — items 1–3) and Section 5.2 (Synthesis Summary Banner) |
| **Expected Outputs** | • **Project header bar**: Breadcrumb link "← All projects" (navigates to `/command-center`), status dot (colored by overall_health), project name (18px, weight 500), project number (12px, secondary), status badge ("On Track" / "Needs Attention" / "Action Required"). |
| | • **Synthesis summary banner**: Full-width below header. Left border 3px solid colored by overall_health. Background: surface color. Content: welcome greeting ("Welcome back Moby."), report timestamp ("Last report issued at [time]"), item count ("[N] new items require attention"), headline assessment (cycle_summary — 1–2 sentences). Metadata line below: next cycle time, confidence level, active source count. |
| | • **Typewriter effect**: On initial page load, the headline assessment text types out character by character over ~2 seconds. After animation completes, text is static. On re-navigation within the same session, text appears immediately (use a session flag). |
| | • **Stats bar**: Horizontal row of 7 compact stat cards below the banner. Fields: Critical count (red text), High count (amber text), Open RFIs, Overdue RFIs (red text if > 0), Open Submittals, Daily Log status (green "Current" or red "Missing [N] days"), Completion percentage. Background: surface color. No border. |
| **Agent Notes** | • The synthesis banner is the "AI employee" moment. The text should feel like a person wrote it. The typewriter effect on the headline reinforces this — it's a deliberate demo polish choice that makes the VP think "the system is telling me something." |
| | • Don't over-engineer the typewriter. A simple `setInterval` adding one character at a time to a state variable works fine. 30–50ms per character. Cancel on unmount. |
| | • The stats bar is secondary information. Keep the cards compact — they should not compete with the banner or the accordion below. Small font (16px for values, 11px for labels). Surface color background, no border, rounded corners. |
| | • The breadcrumb must work. Clicking "← All projects" should navigate back to the Dashboard Overview. This is the superintendent's escape hatch — he doesn't want to learn a nav system, he wants to click the obvious back link. |
| **Acceptance Criteria** | ✓ Breadcrumb navigates back to Dashboard Overview |
| | ✓ Project header shows correct name, number, status for the routed project |
| | ✓ Synthesis banner displays cycle_summary with correct styling |
| | ✓ Typewriter effect fires on initial load, does not re-fire on same-session navigation |
| | ✓ Stats bar displays all 7 fields with correct color coding |
| | ✓ All data sourced from mock data module via project slug |

---

### FE-3.2: Intelligence Tiers (Accordion Structure)

| Field | Detail |
|-------|--------|
| **Goal** | Build the horizontal accordion with three collapsible priority tiers. This is the core interaction pattern of the Project Detail view. |
| **Effort** | 2 hours |
| **Inputs** | • Project Detail shell from FE-3.1 |
| | • Mock data from FE-1.2 |
| | • Frontend Design Spec v1, Section 4.2 (Horizontal Accordion — Intelligence Tiers) |
| **Expected Outputs** | • `IntelligenceTier` component — a full-width collapsible section with colored header bar and expandable body. |
| | • Three tier instances rendered below the stats bar: |
| | — **Tier 1 "Action required"** (red): header bg red at 15% opacity, left border 4px solid #E05555, text #E05555. Default: **expanded**. |
| | — **Tier 2 "Attention"** (amber): header bg amber at 15% opacity, left border 4px solid #E8A838, text #E8A838. Default: **expanded**. |
| | — **Tier 3 "Tracking"** (blue): header bg blue at 15% opacity, left border 4px solid #4A90D9, text #4A90D9. Default: **collapsed**. |
| | • Each header shows: tier label (left, 14px bold), item count "[N] items" (right, 13px bold), chevron indicator (right, rotates 90° when open). |
| | • Click anywhere on header to toggle expand/collapse. |
| | • Expand/collapse animation: 200ms ease-out, smooth height transition. |
| | • Tier body contains a 2-column CSS grid for intelligence cards (built in FE-3.3). At this stage, body shows placeholder text: "[N] intelligence items will render here." |
| | • **Zero-item state**: If a tier has zero items, header still renders showing "0 items." Body is empty. The header alone communicates status — a red bar showing "0 items" tells the super everything is fine. |
| **Agent Notes** | • The accordion must feel responsive. No janky collapse. Use CSS `max-height` transition or `grid-template-rows: 0fr / 1fr` pattern for smooth animation. Do NOT use JavaScript height calculation — it's brittle and flashes. |
| | • The header bar must be large enough to tap on a tablet (44px minimum height). The super might be using an iPad in the field. |
| | • The tier colors use semantic meaning that the user base already understands: red = stop and deal with this, amber = be aware, blue = we're watching. Do not introduce new color meanings. |
| | • Build `IntelligenceTier` as a reusable component that accepts: `label`, `color` (red/amber/blue), `itemCount`, `defaultExpanded` (boolean), and `children` (the card content). |
| | • The 2-column grid inside the body: `grid-template-columns: 1fr 1fr` at 1440px+, collapsing to `1fr` below 1280px. Gap: 8–10px. |
| **Acceptance Criteria** | ✓ Three tier bars render in correct order (red, amber, blue) |
| | ✓ Red and amber tiers expanded by default, blue collapsed |
| | ✓ Click toggles expand/collapse with smooth animation |
| | ✓ Item counts display correctly from mock data |
| | ✓ Zero-item tier renders header with "0 items" and empty body |
| | ✓ Chevron rotates to indicate open/closed state |
| | ✓ Tier body shows 2-column grid at 1920px and 1440px |

---

### FE-3.3: Intelligence Item Cards

| Field | Detail |
|-------|--------|
| **Goal** | Build the intelligence item cards that populate the accordion tiers. Two layers: surface (always visible) and detail (expanded on click). This is the core unit of value in SteelSync. |
| **Effort** | 2–3 hours |
| **Inputs** | • Accordion structure from FE-3.2 |
| | • Mock data from FE-1.2 |
| | • Frontend Design Spec v1, Section 4.3 (Intelligence Item Card) |
| | • Command Center Design Spec v1.0, Section 3.2 (Intelligence Item component spec) |
| **Expected Outputs** | • `IntelligenceCard` component with two layers: |
| | • **Surface layer** (always visible): Left border 3px solid (colored by severity — red/amber/blue). Severity badge ("Action required" / "Attention" / "Watch" — uses status background colors). Category badge (gray pill — Schedule, Manpower, Drawings, Procurement, Submittals, or Compliance). Title (13px bold, max 2 lines). Summary (12px secondary, 1–2 sentences, max 3 lines on surface). Metadata line: source count ("3 sources"), timestamp ("12h ago"), trend indicator with color ("↑ Escalating" in red, "→ Stable" in amber, "↓ Improving" in green). |
| | • **Detail layer** (visible on card click): Full summary paragraph (3–5 sentences, the complete analytical narrative). Evidence chain: list of source documents — each entry shows document type icon, title/number, date, and clickable link (opens Procore in new tab — use mock URLs for prototype). Recommended actions: plain-language list of 2–3 suggested next steps. Technical metadata: intelligence type, confidence percentage, trend with direction, last updated. Feedback buttons: "Useful," "Not Useful," "Already Known" — toggle state on click, write to console.log for prototype. |
| | • **Single-expansion constraint**: Only one card within a tier may be expanded at a time. Expanding a new card collapses the previously expanded card within the same tier. Cards in different tiers are independent. |
| | • Cards render in a 2-column grid within each tier body, sorted by: timestamp (most recent first) within each severity tier. |
| **Agent Notes** | • The two-layer design is critical. The surface must be scannable in 2 seconds. The detail must be comprehensive enough to act on without leaving the page. Don't blur the layers — if something is on the surface, it should not be repeated in the detail. |
| | • The evidence chain is the trust mechanism. When the system says "mechanical rough-in is behind," the PM needs to see the 3 daily logs, 2 RFIs, and the schedule update that support that conclusion. Without evidence, the system is just another alerting tool. |
| | • The feedback buttons are simple toggles for the prototype. Click "Useful" → button gets a subtle highlight, console logs `{item_id, feedback: 'useful'}`. No API call. The data shape is what matters for later integration. |
| | • Card background: #1A2332. Hover: #1F2B3D. Border: #243040. The card must feel clickable — use `cursor: pointer` and a subtle hover state transition. |
| | • Keep the expansion animation smooth. 200ms ease-out. The detail layer should slide open, not pop. |
| | • For the evidence chain links, use realistic mock URLs: `https://app.procore.com/12345/project/rfis/47` — the format doesn't need to work, it needs to look real. |
| **Acceptance Criteria** | ✓ Surface layer displays all required fields with correct formatting |
| | ✓ Clicking a card expands its detail layer |
| | ✓ Only one card expanded per tier at a time |
| | ✓ Evidence chain renders with document type, title, date, and link |
| | ✓ Recommended actions render as a readable list |
| | ✓ Feedback buttons toggle on click and log to console |
| | ✓ Cards sorted correctly within each tier |
| | ✓ 2-column grid layout within tiers at 1440px+ |

---

### FE-3.4: Quick Action Bar (Project Detail)

| Field | Detail |
|-------|--------|
| **Goal** | Add the Quick Action Bar to the Project Detail view, scoped to the active project. |
| **Effort** | 15 minutes |
| **Inputs** | • `QuickActionBar` component from FE-2.2 |
| | • Frontend Design Spec v1, Section 5.1 (Scope Behavior column) |
| | • Structured Channel Routing Spec v1.0, Section 3.3 (Deep Dive & Radar auto-scoping) |
| **Expected Outputs** | • Reuse `QuickActionBar` component from FE-2.2, passing the active `projectId` |
| | • Placeholder toast messages indicate project scope: "Deep Dive Request — Brickell Tower V (coming soon)" |
| | • Rendered below the intelligence tiers, above the page footer |
| **Agent Notes** | • This should be a 15-minute ticket. The component already exists from FE-2.2. Just pass the projectId prop and update the toast message format. |
| **Acceptance Criteria** | ✓ Quick Action Bar renders on Project Detail view |
| | ✓ Toast messages include the active project name |
| | ✓ Visual consistency with Dashboard Overview version |

---

## Phase 4: Shared Components

*Populate the Radar sidebar and the Live Activity Feed. These components appear on both views.*

---

### FE-4.1: Radar Sidebar

| Field | Detail |
|-------|--------|
| **Goal** | Build the Radar sidebar component and populate it on both the Dashboard Overview and Project Detail views. |
| **Effort** | 1 hour |
| **Inputs** | • Layout shell from FE-1.1 (sidebar container) |
| | • Mock data from FE-1.2 (Radar items) |
| | • Frontend Design Spec v1, Section 4.4 (Radar Sidebar) |
| | • Command Center Design Spec v1.0, Section 3.3 (Radar Item — sidebar view) |
| **Expected Outputs** | • `RadarSidebar` component that renders in the right column of the two-column layout |
| | • Header: "Radar" (14px, weight 500) |
| | • List of `RadarSidebarItem` components, each showing: title, priority color (left border — 2px solid red/amber/blue), trend indicator text ("Critical · ↑ Escalating") |
| | • **Dashboard Overview**: shows all Radar items across all projects, sorted by priority (critical first). Each item includes the project name as a subtitle. |
| | • **Project Detail**: shows only Radar items for the active project. No project name subtitle needed. |
| | • Clicking a Radar item: for prototype, scrolls to or highlights the related intelligence item in the main content area if one exists. If no match, navigates to `/command-center/radar`. |
| | • Sidebar width: ~250px at 1920px, ~200px at 1440px. Collapsible via toggle button at 1280px and below. |
| **Agent Notes** | • The sidebar should feel like a persistent awareness panel, not a notification center. Keep it minimal — title and trend only. No summaries, no timestamps, no detail. The detail lives in the full Radar view. |
| | • Build as a single component that accepts a `projectId` prop. When null (Dashboard), show all items. When set (Project Detail), filter to that project. |
| | • The sidebar scroll is independent from the main content scroll. If there are 15 Radar items, the sidebar scrolls internally without affecting the main content. |
| **Acceptance Criteria** | ✓ Radar sidebar renders on both Dashboard Overview and Project Detail |
| | ✓ Dashboard shows all projects' Radar items; Project Detail shows only active project's items |
| | ✓ Items sorted by priority (critical first) |
| | ✓ Click behavior works (highlight or navigate) |
| | ✓ Sidebar scrolls independently from main content |

---

### FE-4.2: Live Activity Feed (Dashboard)

| Field | Detail |
|-------|--------|
| **Goal** | Build the Live Activity Feed on the Dashboard Overview. A chronological log of system actions across all projects. |
| **Effort** | 45 minutes |
| **Inputs** | • Dashboard Overview from FE-2.1 |
| | • Mock data from FE-1.2 (activity feed entries) |
| | • Frontend Design Spec v1, Section 3.1 (Layout Structure — item 3) |
| | • Command Center Design Spec v1.0, Section 3.4 (Live Activity Feed) |
| **Expected Outputs** | • `ActivityFeed` component rendered below the health cards, above the Quick Action Bar |
| | • Section header: "Live activity" with a subtle separator |
| | • Chronological list of activity entries (most recent first). Each entry: timestamp (HH:MM format, tabular-nums, tertiary text), plain-language description, project tag (small badge with project name), highlight indicator (red dot for critical events). |
| | • Maximum 10 entries visible by default. "Show more" link to expand if > 10. |
| | • No WebSocket — data loaded from mock data module on page load. |
| **Agent Notes** | • The activity feed creates a "live" feel even though it's static for the prototype. The timestamps and plain-language descriptions make the system feel active. |
| | • Write the mock activity descriptions as system actions, not user actions: "New RFI opened at BTV5: Light Pole Clarification. 5 similar RFIs issued across 4 projects in the last 2 years." Not "User opened RFI #47." |
| | • The highlight indicator (red dot) should be subtle but visible. Use it sparingly — 2–3 entries out of 15–20. |
| **Acceptance Criteria** | ✓ Activity feed renders with chronological entries |
| | ✓ Each entry shows timestamp, description, project tag |
| | ✓ Critical entries highlighted with red dot |
| | ✓ "Show more" works if > 10 entries |
| | ✓ Descriptions read as system intelligence, not raw events |

---

## Phase 5: Polish & Demo Readiness

*Make it beautiful. Handle edge cases. Ensure a construction executive can look at it and understand what they're seeing.*

---

### FE-5.1: Visual Polish & State Handling

| Field | Detail |
|-------|--------|
| **Goal** | Apply final visual polish across all components. Handle loading, empty, and error states. Ensure responsive behavior at all target breakpoints. |
| **Effort** | 1.5–2 hours |
| **Inputs** | • All components from Phases 1–4 |
| | • Frontend Design Spec v1, Section 6 (Responsive Behavior) and Section 9 (Visual Design Alignment) |
| | • Command Center Design Spec v1.0, Section 4 (Visual Design System) |
| **Expected Outputs** | • **Color consistency audit**: every component uses the exact SteelSync palette. No off-brand colors, no default Tailwind blues leaking through. |
| | • **Typography consistency**: DM Sans everywhere. Font sizes, weights, and spacing consistent across all components. No system font fallback visible. |
| | • **Hover states**: all clickable elements (cards, buttons, Radar items, tier headers) have visible hover transitions (200ms). Card hover: background shifts from #1A2332 to #1F2B3D. |
| | • **Loading states**: skeleton loaders for health cards and intelligence items. Show a pulsing placeholder card shape, not a spinner. The loading state should look like the data is about to appear, not like something broke. |
| | • **Empty states**: every component has a graceful empty message. Health cards: "No active projects." Intelligence tiers: "No [severity] items for this project." Radar: "No items being tracked." Activity feed: "No recent activity." |
| | • **Error states**: if mock data somehow fails to load, show "Unable to load data. Please refresh." Not a blank screen, not a stack trace. |
| | • **Responsive verification**: test all layouts at 1920x1080 and 1440x900. Confirm: health card grid (3-up → 2-up), accordion card grid (2-column → 2-column), Radar sidebar width (250px → 200px), stats bar labels (full → full). |
| | • **Transitions**: smooth expand/collapse on accordion tiers (200ms). Smooth card expansion (200ms). Page transitions between Dashboard and Project Detail (no flash of unstyled content). |
| **Agent Notes** | • This is the ticket that separates a prototype from a demo. Every pixel matters. A construction executive who has never seen the product will judge it in the first 5 seconds based on visual quality. |
| | • Check contrast ratios. Light text on dark backgrounds must be readable. The secondary text color (#9AABB8) on the card background (#1A2332) must pass WCAG AA for normal text. If it doesn't, bump the text color lighter. |
| | • Test with realistic project names, not "Project A." Long names like "Aventura Medical Center Phase II — Building B" must not break card layouts. Truncate with ellipsis if needed. |
| | • If time is limited, prioritize: the Dashboard landing page (health cards) and the Project Detail intelligence tiers. These are the two surfaces that will be shown in a demo. |
| **Acceptance Criteria** | ✓ Color palette consistent across all components |
| | ✓ No broken layouts at 1920x1080 and 1440x900 |
| | ✓ All loading, error, and empty states handled gracefully |
| | ✓ All hover states and transitions smooth |
| | ✓ No developer-facing debug UI visible |
| | ✓ No console errors on any page or interaction |

---

### FE-5.2: Demo Walkthrough Verification

| Field | Detail |
|-------|--------|
| **Goal** | Execute a complete demo walkthrough as a final verification pass. Simulate the pilot demo script and confirm every screen, interaction, and transition works. |
| **Effort** | 30 minutes |
| **Inputs** | • Complete frontend from FE-5.1 |
| **Expected Outputs** | • Execute this exact walkthrough sequence and confirm each step works: |
| | 1. Load `/command-center` — greeting appears, health cards render sorted by severity |
| | 2. Scan the health cards — red project is first, summary is readable, confidence indicator visible |
| | 3. Check the Live Activity Feed — entries are chronological, critical entries highlighted |
| | 4. Glance at the Radar sidebar — items visible with priority colors |
| | 5. Click the red (critical) project health card — navigates to Project Detail |
| | 6. Synthesis banner appears with typewriter effect — headline types out over ~2 seconds |
| | 7. Stats bar shows correct counts — critical count in red, overdue RFIs in red |
| | 8. Red "Action required" tier is expanded — 2-column card grid visible with critical items |
| | 9. Amber "Attention" tier is expanded — high-priority items visible |
| | 10. Blue "Tracking" tier is collapsed — shows "3 items" but body hidden |
| | 11. Click a critical intelligence card — detail layer expands with evidence chain, recommended actions, feedback buttons |
| | 12. Click another card in the same tier — first card collapses, second expands |
| | 13. Click the "Tracking" tier header — tier expands to show watch items |
| | 14. Check Radar sidebar — filtered to this project only |
| | 15. Click "← All projects" breadcrumb — returns to Dashboard Overview |
| | 16. Click a green (on-track) project — Project Detail loads with minimal items, green status |
| | 17. Verify zero-critical state: red tier shows "0 items" with empty body |
| | • Any failures must be fixed before this ticket is marked complete. |
| **Agent Notes** | • This is a test pass, not a build ticket. If something breaks during the walkthrough, fix it and re-run. |
| | • The walkthrough simulates the exact demo flow for the pilot targets. If step 6 (typewriter effect) feels too slow or too fast, adjust the timing. If step 11 (evidence chain) looks sparse, add more mock data entries. |
| | • Take a screenshot at steps 1, 5, 8, 11, and 17. These are the five frames that sell the product. |
| **Acceptance Criteria** | ✓ All 17 walkthrough steps execute without errors |
| | ✓ Typewriter effect timing feels natural (not robotic, not sluggish) |
| | ✓ Card expansion/collapse is smooth at every step |
| | ✓ Navigation between views is instant (no loading flash) |
| | ✓ A construction executive can look at any screen and understand what they're seeing |

---

## Dependency Structure

```text
Phase 1 (Foundation)
 FE-1.1: Layout Shell & Routing
 FE-1.2: Mock Data Layer
 ↓
Phase 2 (Dashboard Overview) Phase 4 (Shared — parallel)
 FE-2.1: Health Cards & Greeting FE-4.1: Radar Sidebar (needs FE-1.1)
 FE-2.2: Quick Action Bar FE-4.2: Activity Feed (needs FE-2.1)
 ↓
Phase 3 (Project Detail — critical path)
 FE-3.1: Project Header & Synthesis Banner
 FE-3.2: Intelligence Tiers (Accordion)
 FE-3.3: Intelligence Item Cards
 FE-3.4: Quick Action Bar (reuse from FE-2.2)
 ↓
Phase 5 (Polish)
 FE-5.1: Visual Polish & State Handling
 FE-5.2: Demo Walkthrough Verification
```

### Critical Path

**FE-1.1 → FE-1.2 → FE-2.1 → FE-3.1 → FE-3.2 → FE-3.3 → FE-5.1 → FE-5.2**

### Key Notes for the Agent

**Read the Frontend Design Specification v1 before starting.** This breakdown incorporates the key requirements but the full spec contains design rationale, color values, responsive breakpoints, and edge case definitions.

**The mock data is the demo.** Construction executives evaluate software in the first 10 seconds. If the mock data reads like placeholder text, the demo fails regardless of how polished the UI is. Every intelligence item summary, every Radar item title, every activity feed entry must read like real construction intelligence written by a senior PM.

**Component naming follows domain language.** `IntelligenceTier`, `IntelligenceCard`, `ProjectHealthCard`, `SynthesisBanner`, `EvidenceChain`, `RadarSidebar` — not `AccordionPanel`, `GenericCard`, `StatusCard`, `AlertBanner`, `LinkList`, `NotificationPanel`.

**Dark theme is non-negotiable.** Every component, every state (loading, empty, error, hover), every transition must look correct against the dark background. If you're ever unsure about a color, check the palette in the Command Center Design Spec v1.0, Section 4.2.

**If time is limited, prioritize the Dashboard landing page (health cards) and the Project Detail intelligence tiers with the accordion.** These are the two surfaces shown in a pilot demo. The Live Activity Feed and Quick Action Bar are supporting cast.
