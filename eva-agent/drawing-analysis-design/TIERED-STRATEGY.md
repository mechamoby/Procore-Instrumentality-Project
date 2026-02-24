# Tiered Extraction Strategy for Construction Drawings

## Overview

Not every EVA agent needs the same depth of drawing understanding. A submittal agent checking a specified door hardware set needs door schedule data (Tier 1). An RFI agent needs to reference specific drawing details (Tier 1-2). A coordination agent needs spatial understanding across disciplines (Tier 3).

**Principle:** Extract once, store structured, query many times. Each tier builds on the previous. Every drawing goes through Tier 0 on upload. Higher tiers are triggered on-demand or by agent requests.

---

## Tier 0: Metadata & Indexing

**Goal:** Know what you have. Every sheet catalogued with discipline, number, title, revision.

**Trigger:** Automatic on upload of any drawing PDF.

**Process:**
```
PDF Upload
  → PyMuPDF: Extract all text with coordinates
  → Identify title block region (bottom-right corner, typically)
     - Heuristic: text cluster in bottom 15% and right 40% of page
     - Fallback: VLM on rendered thumbnail (low-res, ~500px wide)
  → Extract from title block:
     - Sheet number (e.g., A-201, S-003, M-101)
     - Sheet title (e.g., "FIRST FLOOR PLAN", "DOOR SCHEDULE")
     - Discipline (Architecture, Structural, MEP, Civil, Landscape)
     - Revision number/date
     - Project name/number
     - Scale(s)
     - Drawn by / Checked by
  → Classify sheet type:
     - Plan / Elevation / Section / Detail / Schedule / Cover / General Notes
  → Store in database
  → Generate and store thumbnail (PNG, 1000px wide)
```

**Technology:**
- PyMuPDF for text extraction (CAD-generated PDFs)
- Regex patterns for common title block formats
- Gemini Flash or Claude Haiku as fallback for non-standard title blocks or scanned sheets
- Image rendering via PyMuPDF or pdf2image

**Cost:** ~$0.001-0.005 per sheet (mostly free for CAD PDFs; VLM fallback ~$0.005)

**Accuracy:** 90-95% for CAD-generated PDFs, 75-85% for scanned

**Output Schema:**
```json
{
  "sheet_id": "uuid",
  "project_id": "uuid",
  "sheet_number": "A-201",
  "sheet_title": "FIRST FLOOR PLAN",
  "discipline": "architectural",
  "sheet_type": "plan",
  "revision": "3",
  "revision_date": "2025-11-15",
  "scale": ["1/4\" = 1'-0\""],
  "page_size": "ARCH D (24x36)",
  "is_scanned": false,
  "thumbnail_path": "/drawings/proj-123/thumbnails/A-201.png",
  "text_content": "... full extracted text for search ...",
  "uploaded_at": "2026-02-18T15:00:00Z",
  "tier_0_processed_at": "2026-02-18T15:00:03Z"
}
```

---

## Tier 1: Text & Schedule Extraction

**Goal:** Extract all readable text content — general notes, keynotes, schedules, specifications, abbreviation legends — into structured, queryable form.

**Trigger:** On-demand when an EVA agent needs text/schedule data from a sheet, or batch-processed for schedule sheets.

**Process:**
```
Sheet (from Tier 0)
  → Classify regions of the sheet:
     - Schedule tables
     - General notes blocks
     - Keynote legends
     - Abbreviation lists
     - Detail callouts with text
  → For each region type, apply appropriate extraction:

  SCHEDULES (see SCHEDULE-EXTRACTION.md for full pipeline):
     → Detect table boundaries (pdfplumber line detection OR VLM)
     → Extract table to structured JSON
     → Map column headers to semantic fields
     → Validate against known schedule types

  GENERAL NOTES:
     → Extract text block as ordered list
     → Parse section numbers/letters if present
     → Tag by topic (materials, installation, testing, etc.)

  KEYNOTES:
     → Extract keynote number → description mapping
     → Link to CSI division if possible

  ABBREVIATIONS:
     → Extract abbreviation → full term mapping
     → Use as context dictionary for other extraction
```

**Technology:**
- pdfplumber for table boundary detection on CAD PDFs
- Gemini 2.5 Flash as primary VLM for schedule extraction (best cost/accuracy)
- Gemini 2.5 Pro as fallback for complex/failed schedules
- PyMuPDF for text block extraction
- Custom post-processing for construction abbreviations

**Cost:** ~$0.02-0.10 per sheet
- Simple notes page: ~$0.02
- Complex schedule sheet: ~$0.05-0.10
- Full 500-sheet set, all Tier 1: ~$10-50

**Accuracy:**
- General notes: 90-95%
- Simple schedules (clean, standard layout): 85-92%
- Complex schedules (merged cells, abbreviations): 70-85%
- Keynotes: 85-90%

**Output Schema (example — door schedule):**
```json
{
  "sheet_id": "uuid",
  "extraction_type": "schedule",
  "schedule_type": "door_schedule",
  "confidence": 0.87,
  "extracted_at": "2026-02-18T15:01:00Z",
  "data": {
    "columns": ["MARK", "WIDTH", "HEIGHT", "THK", "TYPE", "MATL", "FIRE RATING", "HARDWARE SET", "REMARKS"],
    "rows": [
      {"MARK": "101", "WIDTH": "3'-0\"", "HEIGHT": "7'-0\"", "THK": "1-3/4\"", "TYPE": "A", "MATL": "WD", "FIRE RATING": "20 MIN", "HARDWARE SET": "1", "REMARKS": ""},
      {"MARK": "102", "WIDTH": "3'-0\"", "HEIGHT": "7'-0\"", "THK": "1-3/4\"", "TYPE": "B", "MATL": "HM", "FIRE RATING": "90 MIN", "HARDWARE SET": "3", "REMARKS": "RATED ASSEMBLY"}
    ]
  }
}
```

---

## Tier 2: Spatial Understanding

**Goal:** Understand *what* is drawn *where*. Room layouts, equipment locations, routing, element relationships.

**Trigger:** On-demand by agents needing spatial context (e.g., "what's specified for the lobby ceiling?" requires knowing which room is the lobby on which sheet).

**Process:**
```
Sheet (from Tier 0 + Tier 1)
  → Render to high-resolution image (300 DPI, can be 8000x12000px)
  → Tile into overlapping quadrants if needed (VLM input size limits)
  → For PLANS:
     → Identify rooms (enclosed spaces)
     → Extract room names/numbers
     → Map approximate room boundaries (bounding boxes, not exact polygons)
     → Identify major elements (doors, windows, stairs, elevators)
     → Note grid line references (column lines A, B, C... / 1, 2, 3...)
  → For ELEVATIONS/SECTIONS:
     → Identify floor levels
     → Material callouts
     → Height dimensions
  → For DETAILS:
     → Extract detail title and scale
     → Identify materials and assemblies
     → Extract dimensions and notes
  → Build spatial index linking rooms/areas to grid references
```

**Technology:**
- Gemini 2.5 Pro (best spatial reasoning on drawings)
- High-res rendering via PyMuPDF (300 DPI)
- Tiling strategy: split large pages into 4-6 overlapping tiles, process each, merge results
- PostGIS or similar for spatial indexing of room/element bounding boxes
- Custom domain model for room classification

**Cost:** ~$0.15-0.50 per sheet
- Simple plan: ~$0.15 (single VLM call)
- Complex plan with tiling: ~$0.30-0.50 (4-6 VLM calls)
- Full 500-sheet set: ~$75-250 (but you wouldn't process all sheets)
- Typical: process 50-100 key plan sheets = $8-50

**Accuracy:**
- Room identification: 75-85%
- Room name extraction: 80-90%
- Grid reference mapping: 70-80%
- Element identification (doors/windows): 65-80%
- Spatial relationships: 60-75%

**Output Schema (example — floor plan):**
```json
{
  "sheet_id": "uuid",
  "tier": 2,
  "spaces": [
    {
      "name": "LOBBY",
      "number": "101",
      "grid_reference": {"from": "A/1", "to": "C/3"},
      "bounding_box": {"x": 120, "y": 340, "w": 450, "h": 380},
      "floor": "1",
      "area_approx_sf": 1200,
      "elements": ["door:101", "door:102", "window:W1"],
      "finishes_ref": "FINISH SCHEDULE TYPE A"
    }
  ],
  "grid_lines": {
    "horizontal": ["1", "2", "3", "4"],
    "vertical": ["A", "B", "C", "D"]
  }
}
```

---

## Tier 3: Cross-Discipline Analysis

**Goal:** Correlate information across multiple sheets and disciplines. "Does the structural plan show a beam where the MEP plan routes a duct?" "Do the architectural dimensions match the structural grid?"

**Trigger:** Explicit agent request for coordination analysis. Most expensive, used sparingly.

**Process:**
```
Multiple sheets (all with Tier 0-2 data)
  → Align sheets by grid references and scale
  → For COORDINATION CHECKS:
     → Overlay architectural plan with structural plan at same level
     → Identify potential conflicts (beam vs. duct routing, column vs. door)
     → Compare dimensions across disciplines
  → For SPECIFICATION CONSISTENCY:
     → Cross-reference schedule data with specification sections
     → Check that materials called out in details match schedules
  → For COMPLETENESS CHECKS:
     → Verify all rooms have finish designations
     → Check all doors in plans appear in door schedule
     → Verify section/detail callouts have corresponding sheets
```

**Technology:**
- Gemini 2.5 Pro or Claude Opus 4 for multi-image reasoning
- Requires sending multiple drawing images in a single context
- Custom logic for grid alignment and overlay
- Rule-based validation on top of extracted data

**Cost:** ~$1-5 per analysis query (multiple VLM calls with large contexts)
- Full coordination review of a 500-sheet set: $50-500+

**Accuracy:**
- Known-pattern conflict detection: 50-70%
- Specification consistency: 60-75%
- Completeness checks (schedule vs. plan): 70-85% (mostly data comparison)
- Novel conflict detection: <50% (not reliable)

**Honest Assessment:** Tier 3 is largely aspirational today. The data from Tiers 0-2 enables *some* cross-referencing (e.g., "door 101 appears in the plan but not the schedule"), but true geometric coordination requires spatial precision that VLMs don't reliably provide. **Invest in Tiers 0-1 first.** Tier 2 is valuable for specific use cases. Tier 3 should wait for better models.

---

## Cost Summary

| Tier | Per Sheet | 500-Sheet Set (full) | Typical Usage | Latency |
|------|-----------|---------------------|---------------|---------|
| 0 | $0.001-0.005 | $0.50-2.50 | All sheets | 1-3 sec |
| 1 | $0.02-0.10 | $10-50 | Schedule/notes sheets (~20%) | 5-15 sec |
| 2 | $0.15-0.50 | $75-250 | Key plans (~10-20%) | 15-45 sec |
| 3 | $1-5/query | $50-500+ | On-demand | 30-120 sec |

**Total for a typical project (Tier 0 all + Tier 1 schedules + Tier 2 key plans):**
~$15-75 per drawing set upload. Acceptable for commercial construction projects.

---

## Processing Architecture

```
┌─────────────────────────────────────────────┐
│  Drawing Upload (PDF)                        │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  TIER 0: Metadata Pipeline (automatic)       │
│  PyMuPDF → Text Extract → Title Block Parse  │
│  → Sheet Classification → Thumbnail → DB     │
└──────────────┬──────────────────────────────┘
               │
               ▼ (auto for schedule sheets, on-demand otherwise)
┌─────────────────────────────────────────────┐
│  TIER 1: Text/Schedule Pipeline              │
│  Region Detection → Table Extraction →       │
│  Notes Parsing → Keynote Mapping → DB        │
└──────────────┬──────────────────────────────┘
               │
               ▼ (on-demand by EVA agents)
┌─────────────────────────────────────────────┐
│  TIER 2: Spatial Pipeline                    │
│  High-Res Render → Tile → VLM Analysis →     │
│  Room/Element Mapping → Spatial Index → DB   │
└──────────────┬──────────────────────────────┘
               │
               ▼ (explicit request only)
┌─────────────────────────────────────────────┐
│  TIER 3: Cross-Discipline Analysis           │
│  Multi-Sheet Context → Coordination Check →  │
│  Conflict Report                             │
└─────────────────────────────────────────────┘
```

## Integration with EVA Agents

| EVA Agent | Primary Tier Needed | Usage Pattern |
|-----------|-------------------|---------------|
| **Submittal Agent** | Tier 1 (schedules, specs) | "What hardware set is specified for door 101?" → Query door schedule |
| **RFI Agent** | Tier 1-2 (text + spatial) | "What's the ceiling height in the lobby?" → Room lookup + detail reference |
| **Daily Report Agent** | Tier 0-1 (sheet reference) | "Work today on area shown in A-201" → Sheet metadata + room names |
| **Change Order Agent** | Tier 1-2 (schedules + spatial) | "What changes between Rev 2 and Rev 3?" → Diff extracted data |
| **QA/QC Agent** | Tier 2-3 (spatial + coordination) | "Are all doors in the plan reflected in the schedule?" → Cross-reference |
