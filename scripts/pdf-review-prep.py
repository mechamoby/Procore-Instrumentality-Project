#!/usr/bin/env python3
"""PDF Submittal Review Preprocessor

Extracts text + renders pages as PNGs for vision analysis.
Used by EVA-01 before running submittal review.

Usage:
  python3 pdf-review-prep.py /path/to/submittal.pdf [output_dir]
  
Output:
  {output_dir}/
    text_full.txt          - Full extracted text
    text_page_{N}.txt      - Per-page text
    page_{N}.png           - Per-page PNG renders (300 DPI)
    metadata.json          - Page count, file info, text coverage stats
"""

import json, os, sys, subprocess, hashlib
from pathlib import Path
from datetime import datetime

def extract_text(pdf_path):
    """Extract text using PyMuPDF (fitz)."""
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
            "width": page.rect.width,
            "height": page.rect.height,
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
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"Warning: pdftoppm error: {result.stderr}", file=sys.stderr)
    
    # pdftoppm outputs page-01.png, page-02.png, etc.
    pngs = sorted(output_dir.glob("page-*.png"))
    
    # Rename to page_1.png, page_2.png for cleaner naming
    renamed = []
    for png in pngs:
        # Extract page number from pdftoppm output (page-01.png → 1)
        num = int(png.stem.split("-")[-1])
        new_name = output_dir / f"page_{num}.png"
        png.rename(new_name)
        renamed.append(new_name)
    
    return renamed

def classify_page(text, page_num):
    """Classify page type based on text content."""
    t = text.lower()
    
    if page_num == 1 and any(k in t for k in ["transmittal", "letter of", "cover"]):
        return "cover"
    if any(k in t for k in ["schedule", "model", "catalog", "cfm", "btu", "capacity", "specifications"]):
        return "product_data"
    if any(k in t for k in ["shop drawing", "detail", "elevation", "section", "plan view"]):
        return "shop_drawing"
    if any(k in t for k in ["warranty", "guarantee"]):
        return "warranty"
    if any(k in t for k in ["msds", "safety data", "sds"]):
        return "safety_data"
    if any(k in t for k in ["test report", "certification", "ul listed", "fm approved"]):
        return "certification"
    if any(k in t for k in ["installation", "instructions", "guide"]):
        return "installation"
    if len(text.strip()) < 50:
        return "drawing_or_image"  # Minimal text = likely a drawing
    return "unknown"

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1]).resolve()
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found", file=sys.stderr)
        sys.exit(1)
    
    # Output dir
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])
    else:
        output_dir = Path("/tmp/eva01-review") / pdf_path.stem
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing: {pdf_path.name}", file=sys.stderr)
    print(f"Output: {output_dir}", file=sys.stderr)
    
    # 1. Extract text
    print("Extracting text...", file=sys.stderr)
    pages = extract_text(pdf_path)
    
    # Write full text
    full_text = "\n\n".join(
        f"=== PAGE {p['page']} ===\n{p['text']}" for p in pages
    )
    (output_dir / "text_full.txt").write_text(full_text)
    
    # Write per-page text
    for p in pages:
        (output_dir / f"text_page_{p['page']}.txt").write_text(p["text"])
    
    # 2. Render PNGs
    print("Rendering pages as PNG...", file=sys.stderr)
    pngs = render_pages(pdf_path, output_dir)
    
    # 3. Classify pages
    for p in pages:
        p["type"] = classify_page(p["text"], p["page"])
        p["png"] = str(output_dir / f"page_{p['page']}.png")
        p["needs_vision"] = p["type"] in ("shop_drawing", "drawing_or_image", "unknown") or not p["has_text"]
    
    # 4. Build metadata
    file_size = pdf_path.stat().st_size
    metadata = {
        "source_file": str(pdf_path),
        "file_name": pdf_path.name,
        "file_size": file_size,
        "file_size_human": f"{file_size / 1024:.0f}K" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f}M",
        "page_count": len(pages),
        "processed_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "pages": [{
            "page": p["page"],
            "type": p["type"],
            "has_text": p["has_text"],
            "char_count": p["char_count"],
            "needs_vision": p["needs_vision"],
            "png": p["png"],
            "text_file": str(output_dir / f"text_page_{p['page']}.txt"),
        } for p in pages],
        "summary": {
            "total_pages": len(pages),
            "text_pages": sum(1 for p in pages if p["has_text"]),
            "drawing_pages": sum(1 for p in pages if p["needs_vision"]),
            "page_types": {t: sum(1 for p in pages if p["type"] == t) for t in set(p["type"] for p in pages)},
        },
        "vision_pages": [p["page"] for p in pages if p["needs_vision"]],
    }
    
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))
    
    # Print summary to stdout (this is what EVA-01 reads)
    print(json.dumps(metadata, indent=2))
    
    print(f"\nDone: {len(pages)} pages, {metadata['summary']['text_pages']} with text, {metadata['summary']['drawing_pages']} need vision", file=sys.stderr)

if __name__ == "__main__":
    main()
