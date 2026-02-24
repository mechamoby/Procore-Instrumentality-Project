# Limitations: What AI Can and Cannot Do With Construction Drawings (2026)

## The Honest Truth

Most construction AI marketing is aspirational bullshit. Here's what actually works, what kind-of works, and what doesn't work at all.

---

## ✅ What Works Today (Invest Now)

### Title Block / Sheet Metadata Extraction
- **Reliability:** 90-95% on CAD PDFs, 75-85% on scans
- **Why it works:** Title blocks are in predictable locations with predictable content. This is a solved problem for vector PDFs.
- **Caveat:** Every architect has a different title block layout. You need either a flexible parser or a VLM fallback.

### Full-Text Search Across Drawing Sets
- **Reliability:** 85-95% on CAD PDFs
- **Why it works:** PyMuPDF extracts text with coordinates from vector PDFs. Build a search index. Done.
- **Caveat:** Scanned PDFs need OCR first, dropping accuracy to 70-80%. Abbreviations mean search needs synonym expansion.

### Simple Schedule Table Extraction
- **Reliability:** 85-92% for well-formatted tables
- **Why it works:** Tables with clear grid lines in vector PDFs are parseable by pdfplumber. VLMs handle the rest.
- **Caveat:** "Simple" means standard grid layout, no complex merges, clean text. Maybe 40% of real schedules qualify.

### Drawing Set Organization and Navigation
- **Reliability:** 90%+
- **Why it works:** Sheet numbering follows industry conventions (A=Arch, S=Structural, etc.). Classification is straightforward.
- **Caveat:** Non-standard numbering exists. Some firms use custom discipline codes.

---

## ⚠️ What Kind-of Works (Invest Carefully)

### Complex Schedule Extraction
- **Reliability:** 70-85%
- **Reality:** Merged cells, unusual layouts, abbreviation-heavy content, and footnotes all reduce accuracy. You'll need human review for critical data.
- **The 80/20:** You can get 80% of schedules to 85%+ accuracy. The remaining 20% will be painful edge cases. Design for human-in-the-loop.

### Room/Space Identification on Floor Plans
- **Reliability:** 75-85% for room names, 60-75% for boundaries
- **Reality:** VLMs can identify labeled rooms on floor plans. But room boundaries (where one room ends and another begins) require understanding wall lines, which VLMs do imprecisely.
- **Good enough for:** "Which rooms are on this floor?" Not for: "What's the exact area of Room 201?"

### Keynote/Callout Extraction
- **Reliability:** 80-90% for text, 50-70% for linking to locations
- **Reality:** Extracting the keynote legend is easy (it's a table/list). Linking keynote numbers to their locations on the drawing requires spatial understanding that VLMs struggle with.

### Dimension Reading
- **Reliability:** 70-85% per the BusinesswareTech benchmarks
- **Reality:** VLMs can read dimension values but struggle with:
  - Which dimension goes with which element
  - Tolerance values (upper/lower bounds)
  - Chain dimensions vs. overall dimensions
  - Imperial vs. metric mixed on same sheet

### Drawing Revision Comparison
- **Reliability:** 60-80%
- **Reality:** You can diff the extracted text/data between revisions. But identifying *visual* changes (moved walls, revised details) requires precise spatial comparison that doesn't work well.
- **What works:** "These text values changed in the door schedule between Rev 2 and Rev 3"
- **What doesn't:** "This wall moved 6 inches to the north"

---

## ❌ What Doesn't Work (Wait for Better Models)

### True Spatial Understanding
- **Reliability:** <60%
- **Reality:** VLMs cannot reliably create an accurate spatial model from a floor plan. They can't tell you that Room 201 is 15'-3" × 22'-6" or that it's adjacent to Room 202 on the east side. They can approximate, but the error bars are too wide for professional use.
- **Why:** Construction drawings encode spatial information through a complex visual language (line weights, dash patterns, symbols, dimensions) that VLMs interpret imprecisely.
- **When it'll work:** When VLMs achieve sub-pixel spatial reasoning. Probably 2-3 years.

### Cross-Discipline Coordination
- **Reliability:** <50%
- **Reality:** Detecting that a structural beam conflicts with an HVAC duct requires:
  1. Accurate spatial extraction from both sheets
  2. Alignment of coordinate systems
  3. 3D interpretation from 2D views
  4. Understanding of clearance requirements
  
  Each step has compounding errors. The end result is unreliable.
- **The alternative:** BIM clash detection (Navisworks, Solibri) does this properly from 3D models. Don't try to replicate it from 2D drawings.

### Automatic Code Compliance Checking
- **Reliability:** <40%
- **Reality:** Checking "is this corridor wide enough per IBC?" requires:
  - Knowing what's a corridor (spatial understanding)
  - Measuring its width accurately (dimension extraction)
  - Knowing which code applies (jurisdictional)
  - Understanding exceptions and variances
  
  Too many failure modes stacked on each other.

### Scanned Drawing Analysis (Old/Poor Quality)
- **Reliability:** 40-60% for text, <30% for structure
- **Reality:** Old scanned drawings are often:
  - Low resolution (150 DPI or less)
  - Skewed, stained, faded
  - Multiple generations of copies
  - Handwritten annotations mixed with original
  
  No OCR or VLM handles these well. You're better off having a human read them.

### Handwritten Markup Interpretation
- **Reliability:** 30-50%
- **Reality:** Field markups, RFI sketches, and redline comments are handwritten over complex drawing backgrounds. Even humans struggle to read other people's field markups.

### Symbol Recognition Without Training
- **Reliability:** 40-60% for common symbols, <30% for custom
- **Reality:** VLMs can recognize some common architectural symbols (door swings, north arrows, section marks) but fail on:
  - Electrical symbols (varies by firm)
  - Plumbing symbols
  - Custom detail markers
  - Equipment symbols
  
  You need fine-tuned object detection models (YOLO) with domain-specific training data, which requires 500-2000+ labeled examples per symbol class.

---

## The Compounding Error Problem

The fundamental challenge with construction drawing AI is **error compounding**. Each extraction step has an error rate, and downstream tasks multiply these errors:

```
Title block extraction:     95% accurate
Schedule table parsing:     85% accurate
Abbreviation expansion:     90% accurate
Value validation:           95% accurate

Combined accuracy for a single schedule cell
going through all steps:    95% × 85% × 90% × 95% = ~69%
```

This is why **human-in-the-loop is not optional** for anything beyond Tier 0. Design every pipeline with review checkpoints.

---

## What To Build vs. What To Wait For

### Build Now (Q1-Q2 2026)
- Tier 0 metadata pipeline — high ROI, high reliability, every agent needs it
- Schedule extraction pipeline — the most valuable structured data, achievable accuracy
- Full-text search index — simple but transformative for agent queries
- Thumbnail generation and sheet organization

### Build Next (Q3-Q4 2026)
- Room identification on floor plans (Tier 2 lite)
- Keynote extraction and linking to specs
- Drawing revision diffing (text/data level)
- Multi-page schedule merging

### Wait (2027+)
- True spatial modeling from 2D drawings
- Cross-discipline coordination analysis
- Automatic code compliance checking
- Symbol recognition without per-project training
- Scanned/legacy drawing analysis

### Never Build (Use Existing Tools)
- 3D clash detection — use Navisworks/Solibri/BIMcollab from BIM models
- Quantity takeoff from drawings — use Bluebeam/PlanSwift/On-Screen Takeoff
- Drawing production — use Revit/AutoCAD

---

## Cost Reality Check

For a typical commercial project (500-sheet drawing set):

| What You Want | What It Costs | What You Get |
|--------------|---------------|--------------|
| Index everything (Tier 0) | $1-3 | Sheet catalog, searchable text, thumbnails |
| Extract all schedules (Tier 1) | $5-25 | Structured schedule data, 80-90% accurate |
| Understand all floor plans (Tier 2) | $50-150 | Room maps, element lists, 70-80% accurate |
| Full coordination analysis (Tier 3) | $200-500+ | Unreliable results, not worth it today |

The economics work for Tier 0-1. Tier 2 is justifiable for high-value projects. Tier 3 is not cost-effective given the accuracy.

---

## The Model Improvement Trajectory

VLM capability on technical documents is improving roughly **15-25% per year** on structured extraction tasks. Based on current trajectory:

- **2026:** Gemini 2.5 / Claude Opus 4 level — good text extraction, decent tables, poor spatial
- **2027:** Likely 85-90% on complex schedules, 70-80% on spatial tasks
- **2028:** Possibly production-ready spatial understanding for floor plans

**Design your system for model swapability.** The extraction pipeline should be model-agnostic. Today's best model (Gemini 2.5 Flash for schedules) might be surpassed next quarter.
