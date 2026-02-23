#!/usr/bin/env python3
"""EVA-01 Submittal Review Pipeline

Complete two-pass review: text extraction + vision analysis.
Called by EVA-01 agent or directly for testing.

Usage:
  python3 eva01-review.py /path/to/submittal.pdf [--output-dir /path] [--vision-only] [--text-only]

Output: JSON review package to stdout with all extracted data.
EVA-01 uses this data to compose the final review.
"""

import json, os, sys, subprocess, base64, argparse
from pathlib import Path
from datetime import datetime

# EVA-01 hardening helpers
sys.path.append('/home/moby/.openclaw/workspace/eva-agent/submittal-agent')
from eva00.eva01_flow import require_attachment_path, EVA01RefinementInput, build_submittal_payload

# Use workspace path for outputs so agent image tool can access them
WORKSPACE_REVIEW_DIR = Path("/home/moby/.openclaw/workspace/eva01-reviews")

def extract_text(pdf_path):
    """Extract text using PyMuPDF."""
    import fitz
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append({
            "page": i + 1,
            "text": text,
            "char_count": len(text),
            "has_text": len(text.strip()) > 50,
        })
    doc.close()
    return pages

def render_pages(pdf_path, output_dir, dpi=300, max_dimension=2400):
    """Render PDF pages as PNGs using pdftoppm."""
    prefix = str(output_dir / "page")
    cmd = [
        "pdftoppm", "-png", "-r", str(dpi),
        "-scale-to", str(max_dimension),
        str(pdf_path), prefix
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    pngs = sorted(output_dir.glob("page-*.png"))
    renamed = []
    for png in pngs:
        num = int(png.stem.split("-")[-1])
        new_name = output_dir / f"page_{num}.png"
        png.rename(new_name)
        renamed.append(new_name)
    return renamed

def has_dimensions(text):
    """Check if extracted text contains dimensional data."""
    import re
    # Patterns for construction dimensions
    patterns = [
        r'\d+[\-\s]*\d*/\d+\"',          # Fractional inches: 3-1/2", 7/8"
        r"\d+'-\d+",                       # Feet-inches: 8'-7"
        r'\d+\.\d+\"',                     # Decimal inches: 2.50"
        r'\d+\s*mm\b',                     # Millimeters
        r'\d+\s*\[\d+\.?\d*\"?\]',         # Metric [imperial]: 108 [4.25"]
        r'\d+\s*(?:ga\.?|gauge)',          # Gauge: 14 ga, 16 gauge
        r'\d+\s*(?:dia\.?|diameter|Ø)',    # Diameter
        r'(?:ø|Ø)\s*\d+',                 # Diameter symbol prefix
        r'\d+\s*x\s*\d+\s*x\s*\d+',      # Member sizes: 2x6, 2-1/2 x 2-1/2 x 0.94
        r'[WCHSL]\d+x\d+',               # Steel shapes: W12x26, C8x11.5, HSS4x4
        r'#\d+\s*(?:rebar|bar)',          # Rebar: #4 rebar
        r'\d+\s*(?:psf|psi|plf|ksi|lbs|kips)', # Loads/forces
        r'\d+\s*(?:cfm|gpm|fpm)',         # Flow rates
        r'\d+\s*(?:ton|hp|kw|amp|volt)',  # Equipment ratings
    ]
    matches = 0
    for p in patterns:
        found = re.findall(p, text, re.IGNORECASE)
        matches += len(found)
    return matches

def classify_page(text, page_num):
    """Classify page type based on text content."""
    t = text.lower()
    
    if page_num == 1 and any(k in t for k in ["transmittal", "letter of", "cover", "submittal #"]):
        return "cover"
    if any(k in t for k in ["schedule", "catalog", "cfm", "btu", "capacity", "technical data", "performance"]):
        return "product_data"
    if any(k in t for k in ["shop drawing", "detail", "elevation", "section view", "plan view", "assembly"]):
        return "shop_drawing"
    if any(k in t for k in ["warranty", "guarantee"]):
        return "warranty"
    if any(k in t for k in ["msds", "safety data", "sds"]):
        return "safety_data"
    if any(k in t for k in ["test report", "certification", "ul listed", "fm approved", "noa"]):
        return "certification"
    if any(k in t for k in ["installation", "instructions", "guide", "mounting"]):
        return "installation"
    if len(text.strip()) < 50:
        return "drawing"
    return "general"

def main():
    parser = argparse.ArgumentParser(description="EVA-01 Submittal Review Preprocessor")
    parser.add_argument("pdf_path", help="Path to submittal PDF")
    parser.add_argument("--output-dir", help="Output directory (default: workspace/eva01-reviews/<stem>)")
    parser.add_argument("--text-only", action="store_true", help="Skip PNG rendering")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages to process")
    parser.add_argument("--project-name", default="Project", help="Project name for EVA-01 filename payload")
    parser.add_argument("--pm-title-override", default="", help="Optional PM title override")
    parser.add_argument("--placeholder-number", default="", help="Optional prior TBD-### to increment")
    args = parser.parse_args()
    
    # Hard guardrail: fail loud if attachment path missing/invalid
    try:
        safe_path = require_attachment_path(args.pdf_path)
    except Exception as e:
        print(json.dumps({"error": str(e), "stage": "attachment_guardrail"}))
        sys.exit(1)

    pdf_path = Path(safe_path).resolve()
    if pdf_path.suffix.lower() != ".pdf":
        print(json.dumps({"error": f"Expected PDF input, got: {pdf_path.name}", "stage": "file_type_guardrail"}))
        sys.exit(1)
    
    # Output to workspace so image tool can access PNGs
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = WORKSPACE_REVIEW_DIR / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing: {pdf_path.name}", file=sys.stderr)
    
    # 1. Extract text
    pages = extract_text(pdf_path)
    
    if len(pages) > args.max_pages:
        print(f"Warning: {len(pages)} pages, truncating to {args.max_pages}", file=sys.stderr)
        pages = pages[:args.max_pages]
    
    # 2. Classify pages + smart vision triggering
    for p in pages:
        p["type"] = classify_page(p["text"], p["page"])
        p["dimension_count"] = has_dimensions(p["text"])
        
        # Smart vision trigger: only when text extraction can't get the job done
        is_drawing_type = p["type"] in ("shop_drawing", "drawing", "general")
        text_has_dimensions = p["dimension_count"] >= 3  # At least 3 dimensional values found
        
        if not p["has_text"]:
            # Almost no text → definitely need vision
            p["needs_vision"] = True
            p["vision_reason"] = "minimal_text"
        elif is_drawing_type and not text_has_dimensions:
            # Drawing page but text didn't capture dimensions → need vision
            p["needs_vision"] = True
            p["vision_reason"] = "drawing_missing_dimensions"
        elif is_drawing_type and text_has_dimensions:
            # Drawing page AND text got dimensions → text is enough
            p["needs_vision"] = False
            p["vision_reason"] = "text_has_dimensions"
        elif p["type"] in ("cover", "product_data", "certification", "warranty", "safety_data", "installation"):
            # Data pages → text is always enough
            p["needs_vision"] = False
            p["vision_reason"] = "data_page"
        else:
            # Fallback: if we have decent text, skip vision
            p["needs_vision"] = p["char_count"] < 200
            p["vision_reason"] = "fallback"
    
    # 3. Render PNGs (unless text-only)
    png_paths = {}
    if not args.text_only:
        print(f"Rendering {len(pages)} pages as PNG...", file=sys.stderr)
        pngs = render_pages(pdf_path, output_dir)
        for png in pngs:
            num = int(png.stem.split("_")[-1])
            png_paths[num] = str(png)
    
    # 4. Write text files
    full_text = "\n\n".join(f"=== PAGE {p['page']} ===\n{p['text']}" for p in pages)
    (output_dir / "text_full.txt").write_text(full_text)
    
    # 5. Build deterministic EVA-01 defaults payload
    cover_title = pdf_path.stem.replace('_', ' ').replace('-', ' ').strip()
    defaults_payload = build_submittal_payload(
        EVA01RefinementInput(
            project_name=args.project_name,
            extracted_title=cover_title,
            pm_title_override=args.pm_title_override,
            placeholder_number=args.placeholder_number or None,
            received_at=datetime.now(),
        )
    )

    # 6. Build review package
    review_pages = []
    for p in pages:
        page_info = {
            "page": p["page"],
            "type": p["type"],
            "has_text": p["has_text"],
            "char_count": p["char_count"],
            "dimension_count": p["dimension_count"],
            "needs_vision": p["needs_vision"],
            "vision_reason": p["vision_reason"],
            "text": p["text"],
        }
        if p["page"] in png_paths:
            page_info["png_path"] = png_paths[p["page"]]
        review_pages.append(page_info)
    
    file_size = pdf_path.stat().st_size
    review_package = {
        "source_file": str(pdf_path),
        "file_name": pdf_path.name,
        "file_size": file_size,
        "file_size_human": f"{file_size/1024:.0f}K" if file_size < 1048576 else f"{file_size/1048576:.1f}M",
        "page_count": len(pages),
        "processed_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "summary": {
            "total_pages": len(pages),
            "text_pages": sum(1 for p in pages if p["has_text"]),
            "vision_pages": sum(1 for p in pages if p["needs_vision"]),
            "page_types": {},
        },
        "eva01_defaults": defaults_payload,
        "pages": review_pages,
        "vision_page_numbers": [p["page"] for p in pages if p["needs_vision"]],
        "vision_page_paths": [png_paths.get(p["page"]) for p in pages if p["needs_vision"] and p["page"] in png_paths],
    }
    
    # Count page types
    for p in pages:
        t = p["type"]
        review_package["summary"]["page_types"][t] = review_package["summary"]["page_types"].get(t, 0) + 1
    
    # Write metadata
    (output_dir / "review_package.json").write_text(json.dumps(review_package, indent=2))
    
    # Output to stdout
    print(json.dumps(review_package, indent=2))
    
    print(f"\nReady: {len(pages)} pages | {review_package['summary']['text_pages']} text | {review_package['summary']['vision_pages']} need vision", file=sys.stderr)
    print(f"Output: {output_dir}", file=sys.stderr)
    if review_package["vision_page_paths"]:
        print(f"Vision PNGs: {', '.join(review_package['vision_page_paths'])}", file=sys.stderr)

if __name__ == "__main__":
    main()
