# Schedule Extraction Pipeline

## Why Schedules Matter Most

Drawing schedules (door, window, finish, equipment, fixture, hardware) are the **single most actionable structured data** in a construction drawing set. They are:

- **Directly referenced by submittals** — "Submit door hardware per Hardware Set 3 in the door schedule"
- **The spec-to-field bridge** — Translate architectural intent into material procurement
- **Structured by nature** — They're tables, the most extractable format in drawings
- **High-value** — A wrong door hardware set costs $500-5000+ to fix in the field

Yet they're notoriously hard to extract because:
- Merged cells (headers spanning multiple columns)
- Abbreviations everywhere (WD, HM, AL, SC, PR, FRP, GPT...)
- Mixed units and formats in the same column
- Footnotes and remarks that modify row meaning
- Multi-page schedules that span sheets
- Non-standard layouts per architect

---

## Pipeline Architecture

```
┌──────────────────────────────────────────────┐
│  Input: Sheet identified as "schedule" (Tier 0) │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  STEP 1: PDF Type Detection                   │
│  Is this CAD-generated (vector) or scanned?   │
└──────┬──────────────────┬────────────────────┘
       │ Vector            │ Scanned/Raster
       ▼                   ▼
┌──────────────┐  ┌────────────────────┐
│ STEP 2a:     │  │ STEP 2b:           │
│ pdfplumber   │  │ Render to image    │
│ table detect │  │ (300 DPI)          │
└──────┬───────┘  └────────┬───────────┘
       │                   │
       ▼                   ▼
┌──────────────┐  ┌────────────────────┐
│ Table found? │  │ VLM table extract  │
│ Yes → Parse  │  │ (Gemini Flash)     │
│ No → Step 2b │  │                    │
└──────┬───────┘  └────────┬───────────┘
       │                   │
       ▼                   ▼
┌──────────────────────────────────────────────┐
│  STEP 3: Raw Table Normalization              │
│  - Resolve merged cell spans                  │
│  - Normalize column headers                   │
│  - Handle multi-line cell content             │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  STEP 4: Schedule Type Classification         │
│  Map to known schema (door/window/finish/etc) │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  STEP 5: Abbreviation Expansion & Validation  │
│  Expand construction abbreviations            │
│  Validate values against expected ranges      │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  STEP 6: Confidence Scoring & Human Review    │
│  Flag low-confidence cells for review         │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Output: Structured JSON + optional Excel     │
└──────────────────────────────────────────────┘
```

---

## Step-by-Step Detail

### Step 1: PDF Type Detection

```python
import pymupdf

def detect_pdf_type(page):
    """Determine if a PDF page has usable vector data."""
    text_blocks = page.get_text("dict")["blocks"]
    text_chars = sum(
        len(span["text"])
        for block in text_blocks if block["type"] == 0
        for line in block["lines"]
        for span in line["spans"]
    )
    drawings = page.get_drawings()

    if text_chars > 100 and len(drawings) > 20:
        return "vector"  # CAD-generated, parseable
    elif text_chars > 100:
        return "vector_minimal"  # Text but few drawings
    else:
        return "raster"  # Scanned, need OCR/VLM
```

### Step 2a: Vector Table Extraction (pdfplumber)

```python
import pdfplumber

def extract_tables_vector(pdf_path, page_num):
    """Extract tables from vector PDF using pdfplumber."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]

        # Custom table settings tuned for construction schedules
        table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 5,        # Construction drawings have thick lines
            "join_tolerance": 5,
            "edge_min_length": 20,
            "min_words_vertical": 1,
            "min_words_horizontal": 1,
        }

        tables = page.extract_tables(table_settings)

        if not tables:
            # Fallback: try text-based strategy
            table_settings["vertical_strategy"] = "text"
            table_settings["horizontal_strategy"] = "text"
            tables = page.extract_tables(table_settings)

        return tables
```

**When pdfplumber fails** (returns empty/garbage): Fall through to Step 2b.

Common failure modes:
- Dashed lines used as table borders
- Very thick lines that pdfplumber doesn't recognize
- Tables without full grid lines (only horizontal rules)
- Overlapping drawing elements confuse table detection

### Step 2b: VLM Table Extraction

```python
import google.generativeai as genai
from PIL import Image

SCHEDULE_EXTRACTION_PROMPT = """
You are analyzing a construction drawing schedule table.
Extract the COMPLETE table into a JSON structure.

Rules:
1. Preserve ALL rows and columns exactly as shown
2. For merged header cells, repeat the header value for each spanned column
3. Preserve abbreviations exactly as written (do not expand)
4. For empty cells, use empty string ""
5. For cells with multiple lines, join with " / "
6. Include ALL footnotes below the table as a separate "footnotes" array
7. If the schedule continues from a previous page, note "continues_from_previous": true

Output format:
{
  "table_title": "DOOR SCHEDULE" or similar,
  "headers": ["COL1", "COL2", ...],
  "rows": [
    {"COL1": "value", "COL2": "value", ...},
    ...
  ],
  "footnotes": ["1. All doors to be ...", ...],
  "continues_from_previous": false
}

Be EXHAUSTIVE. Missing a single row or cell is a critical error.
"""

def extract_table_vlm(image_path):
    """Extract table using Gemini vision model."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    image = Image.open(image_path)

    response = model.generate_content(
        [SCHEDULE_EXTRACTION_PROMPT, image],
        generation_config={"temperature": 0.1}  # Low temp for accuracy
    )

    return parse_json_response(response.text)
```

**Key VLM considerations:**
- **Resolution matters**: Render at 300 DPI minimum. Schedule text is often 6-8pt font.
- **Tiling for large schedules**: If the table exceeds the VLM's effective resolution, tile horizontally with overlap and merge.
- **Temperature 0.1**: We want deterministic extraction, not creative interpretation.
- **Model choice**: Gemini 2.5 Flash is the sweet spot. Pro for retries on failures.

### Step 3: Raw Table Normalization

```python
def normalize_table(raw_table):
    """Clean and normalize extracted table data."""
    # 1. Remove completely empty rows/columns
    rows = [r for r in raw_table["rows"] if any(v.strip() for v in r.values())]

    # 2. Normalize headers
    headers = [h.strip().upper().replace("\n", " ") for h in raw_table["headers"]]

    # 3. Handle common header variations
    header_mappings = {
        # Door schedule
        "MK": "MARK", "NO.": "MARK", "DR NO": "MARK", "DOOR NO": "MARK",
        "W": "WIDTH", "WD": "WIDTH", "DOOR WIDTH": "WIDTH",
        "H": "HEIGHT", "HT": "HEIGHT", "DOOR HEIGHT": "HEIGHT",
        "THK": "THICKNESS", "T": "THICKNESS",
        "MTL": "MATERIAL", "MATL": "MATERIAL", "MAT": "MATERIAL",
        "FR": "FIRE RATING", "FIRE": "FIRE RATING", "FRR": "FIRE RATING",
        "HW SET": "HARDWARE SET", "HDWR": "HARDWARE SET", "HW": "HARDWARE SET",
        "RMK": "REMARKS", "NOTE": "REMARKS", "NOTES": "REMARKS",

        # Finish schedule
        "RM": "ROOM", "RM NO": "ROOM NUMBER", "ROOM NO": "ROOM NUMBER",
        "FLR": "FLOOR", "FL": "FLOOR",
        "CLG": "CEILING", "CEIL": "CEILING",
        "N WALL": "NORTH WALL", "S WALL": "SOUTH WALL",
        "E WALL": "EAST WALL", "W WALL": "WEST WALL",
        "BASE": "BASE", "WAINSCOT": "WAINSCOT",
        "CLG HT": "CEILING HEIGHT", "CLG. HT.": "CEILING HEIGHT",
    }

    normalized_headers = [header_mappings.get(h, h) for h in headers]

    # 4. Clean cell values
    for row in rows:
        for key, value in row.items():
            if isinstance(value, str):
                row[key] = value.strip()
                # Normalize common dimension formats
                row[key] = normalize_dimension(row[key])

    return {"headers": normalized_headers, "rows": rows, "footnotes": raw_table.get("footnotes", [])}


def normalize_dimension(value):
    """Normalize dimension strings."""
    # Handle feet-inches: 3'-0", 3'0", 3'-0
    import re
    match = re.match(r"(\d+)['\u2019]\s*-?\s*(\d+(?:/\d+)?)[\"″\u201D]?", value)
    if match:
        feet, inches = match.groups()
        return f"{feet}'-{inches}\""
    return value
```

### Step 4: Schedule Type Classification

```python
SCHEDULE_SIGNATURES = {
    "door_schedule": {
        "required_columns": ["MARK", "WIDTH", "HEIGHT"],
        "optional_columns": ["MATERIAL", "FIRE RATING", "HARDWARE SET", "TYPE", "FRAME"],
        "title_patterns": [r"door\s+schedule", r"door\s+&\s+frame", r"dr\s+schedule"],
    },
    "window_schedule": {
        "required_columns": ["MARK", "WIDTH", "HEIGHT"],
        "optional_columns": ["TYPE", "GLAZING", "FRAME", "MANUFACTURER", "REMARKS"],
        "title_patterns": [r"window\s+schedule", r"win\s+schedule"],
    },
    "finish_schedule": {
        "required_columns": ["ROOM"],
        "optional_columns": ["FLOOR", "CEILING", "NORTH WALL", "SOUTH WALL", "BASE", "WAINSCOT", "CEILING HEIGHT"],
        "title_patterns": [r"finish\s+schedule", r"room\s+finish", r"interior\s+finish"],
    },
    "equipment_schedule": {
        "required_columns": ["MARK"],
        "optional_columns": ["DESCRIPTION", "MANUFACTURER", "MODEL", "SIZE", "CAPACITY", "VOLTAGE"],
        "title_patterns": [r"equipment\s+schedule", r"equip\s+schedule"],
    },
    "hardware_schedule": {
        "required_columns": ["SET"],
        "optional_columns": ["ITEM", "MANUFACTURER", "DESCRIPTION", "FINISH", "QUANTITY"],
        "title_patterns": [r"hardware\s+(group|set|schedule)", r"hdwr\s+schedule"],
    },
    "plumbing_fixture_schedule": {
        "required_columns": ["MARK"],
        "optional_columns": ["TYPE", "MANUFACTURER", "MODEL", "CONNECTION", "REMARKS"],
        "title_patterns": [r"plumbing\s+fixture", r"fixture\s+schedule"],
    },
}

def classify_schedule(table, title=""):
    """Classify a table into a known schedule type."""
    best_match = None
    best_score = 0

    for stype, sig in SCHEDULE_SIGNATURES.items():
        score = 0

        # Title match
        for pattern in sig["title_patterns"]:
            if re.search(pattern, title.lower()):
                score += 5

        # Column match
        headers_lower = [h.lower() for h in table["headers"]]
        for req in sig["required_columns"]:
            if req.lower() in headers_lower:
                score += 3
        for opt in sig["optional_columns"]:
            if opt.lower() in headers_lower:
                score += 1

        if score > best_score:
            best_score = score
            best_match = stype

    return best_match if best_score >= 4 else "unknown_schedule"
```

### Step 5: Abbreviation Expansion & Validation

```python
# Construction abbreviation dictionary (extensive but not exhaustive)
CONSTRUCTION_ABBREVIATIONS = {
    # Materials
    "WD": "WOOD", "HM": "HOLLOW METAL", "AL": "ALUMINUM", "GL": "GLASS",
    "STL": "STEEL", "SS": "STAINLESS STEEL", "CONC": "CONCRETE",
    "CMU": "CONCRETE MASONRY UNIT", "GYP BD": "GYPSUM BOARD",
    "GWB": "GYPSUM WALL BOARD", "ACT": "ACOUSTIC CEILING TILE",
    "VCT": "VINYL COMPOSITION TILE", "CPT": "CARPET", "CT": "CERAMIC TILE",
    "PT": "PORCELAIN TILE", "EPXY": "EPOXY", "FRP": "FIBERGLASS REINFORCED PANEL",
    "PLAS LAM": "PLASTIC LAMINATE", "SLD SRF": "SOLID SURFACE",
    "RBR": "RUBBER", "TERZ": "TERRAZZO",

    # Hardware
    "PR": "PAIR", "SGL": "SINGLE", "MTG": "MORTISE", "CYL": "CYLINDER",
    "LCK": "LOCK", "LVR": "LEVER", "KNB": "KNOB",

    # Fire rating
    "20 MIN": "20 MINUTE RATED", "45 MIN": "45 MINUTE RATED",
    "60 MIN": "60 MINUTE RATED", "90 MIN": "90 MINUTE RATED",
    "NR": "NOT RATED",

    # General
    "TYP": "TYPICAL", "SIM": "SIMILAR", "NIC": "NOT IN CONTRACT",
    "BY OWN": "BY OWNER", "FBO": "FURNISHED BY OWNER",
    "FBC": "FURNISHED BY CONTRACTOR", "VIF": "VERIFY IN FIELD",
    "NTS": "NOT TO SCALE", "EQ": "EQUAL", "MAX": "MAXIMUM", "MIN": "MINIMUM",
}

def expand_abbreviations(table, expand=False):
    """Optionally expand abbreviations, always tag them."""
    for row in table["rows"]:
        for key, value in row.items():
            if isinstance(value, str):
                for abbr, full in CONSTRUCTION_ABBREVIATIONS.items():
                    if value.upper() == abbr:
                        row[key] = full if expand else value
                        row[f"_{key}_expanded"] = full
    return table


# Validation rules per schedule type
VALIDATION_RULES = {
    "door_schedule": {
        "WIDTH": {"type": "dimension", "min_inches": 18, "max_inches": 96},
        "HEIGHT": {"type": "dimension", "min_inches": 60, "max_inches": 120},
        "FIRE RATING": {"type": "enum", "values": ["NR", "20 MIN", "45 MIN", "60 MIN", "90 MIN", "3 HR"]},
    },
    "finish_schedule": {
        "CEILING HEIGHT": {"type": "dimension", "min_inches": 84, "max_inches": 240},
    },
}

def validate_schedule(table, schedule_type):
    """Validate extracted values against expected ranges. Return warnings."""
    warnings = []
    rules = VALIDATION_RULES.get(schedule_type, {})

    for i, row in enumerate(table["rows"]):
        for column, rule in rules.items():
            value = row.get(column, "")
            if not value:
                continue

            if rule["type"] == "dimension":
                inches = parse_dimension_to_inches(value)
                if inches and (inches < rule["min_inches"] or inches > rule["max_inches"]):
                    warnings.append({
                        "row": i, "column": column, "value": value,
                        "message": f"Value {value} outside expected range ({rule['min_inches']}-{rule['max_inches']} inches)"
                    })

            elif rule["type"] == "enum":
                if value.upper() not in [v.upper() for v in rule["values"]]:
                    warnings.append({
                        "row": i, "column": column, "value": value,
                        "message": f"Unexpected value '{value}'. Expected one of: {rule['values']}"
                    })

    return warnings
```

### Step 6: Confidence Scoring

```python
def score_confidence(table, extraction_method, warnings):
    """Score overall confidence of extraction."""
    score = 1.0

    # Method penalty
    if extraction_method == "vlm":
        score -= 0.05  # VLM slightly less trustworthy than direct parsing
    if extraction_method == "vlm_retry":
        score -= 0.15  # Needed retry, likely a hard table

    # Completeness penalty
    empty_cells = sum(1 for row in table["rows"] for v in row.values() if not str(v).strip())
    total_cells = sum(1 for row in table["rows"] for _ in row.values())
    empty_ratio = empty_cells / max(total_cells, 1)
    if empty_ratio > 0.3:
        score -= 0.2  # Suspiciously many empty cells

    # Validation warnings penalty
    score -= len(warnings) * 0.03

    # Row count sanity
    if len(table["rows"]) < 2:
        score -= 0.3  # Probably missed rows
    if len(table["rows"]) > 200:
        score -= 0.1  # Unusually large, verify

    return max(0.0, min(1.0, round(score, 2)))
```

---

## Handling Multi-Page Schedules

Many schedules span multiple sheets (e.g., "DOOR SCHEDULE - SHEET 1 OF 3").

```python
def merge_multi_page_schedules(extracted_tables):
    """Merge schedule tables that span multiple sheets."""
    groups = {}

    for table in extracted_tables:
        title = table["table_title"]
        # Remove page indicators
        base_title = re.sub(r"\s*[-–]\s*(SHEET|PAGE|CONT'?D?).*", "", title, flags=re.IGNORECASE)
        base_title = base_title.strip()

        if base_title not in groups:
            groups[base_title] = []
        groups[base_title].append(table)

    merged = []
    for title, tables in groups.items():
        if len(tables) == 1:
            merged.append(tables[0])
        else:
            # Sort by sheet number, merge rows
            # Use first table's headers as canonical
            result = {
                "table_title": title,
                "headers": tables[0]["headers"],
                "rows": [],
                "footnotes": [],
                "source_sheets": [],
            }
            for t in tables:
                result["rows"].extend(t["rows"])
                result["footnotes"].extend(t.get("footnotes", []))
                result["source_sheets"].append(t.get("source_sheet", "unknown"))

            # Deduplicate footnotes
            result["footnotes"] = list(dict.fromkeys(result["footnotes"]))
            merged.append(result)

    return merged
```

---

## Known Failure Modes & Mitigations

| Failure Mode | Frequency | Mitigation |
|-------------|-----------|------------|
| **Merged header cells mis-parsed** | Common (30%+) | VLM handles better than pdfplumber. Explicit prompt instruction. |
| **Footnote symbols (*, †, ‡) lost** | Common | Include in extraction prompt. Post-process to link footnotes to rows. |
| **Abbreviations not in dictionary** | Frequent | Project-specific abbreviation list from general notes sheet (Tier 1). |
| **Rotated/sideways schedules** | Occasional (5%) | Detect rotation via PyMuPDF text orientation. Rotate before processing. |
| **Schedules split across columns** | Occasional | Some architects put two schedule sections side-by-side. VLM handles this better than pdfplumber. |
| **"See spec" or "By owner" entries** | Common | Don't treat as errors. Tag as references needing resolution. |
| **Schedule in a detail sheet, not standalone** | Common | Tier 0 may not flag as schedule sheet. Need Tier 1 region detection to find embedded schedules. |

---

## Expected Performance

| Schedule Type | pdfplumber Accuracy | VLM Accuracy | Combined Pipeline |
|--------------|--------------------|--------------|--------------------|
| Door Schedule (simple) | 80-90% | 85-92% | 90-95% |
| Door Schedule (complex, merged cells) | 50-65% | 75-85% | 80-88% |
| Window Schedule | 80-90% | 85-90% | 88-93% |
| Finish Schedule | 70-80% | 80-88% | 85-90% |
| Equipment Schedule | 75-85% | 80-88% | 85-92% |
| Hardware Group Schedule | 60-70% | 70-80% | 75-85% |

"Accuracy" = percentage of cells correctly extracted with correct row/column placement.

**The combined pipeline** uses pdfplumber first (fast, free), falls back to VLM (slower, costs money), and uses VLM to validate/correct pdfplumber output when confidence is low.
