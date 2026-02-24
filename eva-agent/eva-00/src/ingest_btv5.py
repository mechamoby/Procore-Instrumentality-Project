#!/usr/bin/env python3
"""Ingest BTV5 sandbox data into EVA-00 database.

Seeds the database with our test project so EVA-00 has something to query.
Uses the parsed submittal data we already have from the upload process.
"""

import json
import os
import re
import sys
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime, timedelta
import random

# Database config
DB_NAME = os.environ.get("EVA00_DB", "nerv_eva00")
DB_USER = os.environ.get("EVA00_DB_USER", "moby")

WORKSPACE = Path("/home/moby/.openclaw/workspace")
BTV5_DIR = WORKSPACE / "eva-agent" / "btv5-submittals"
RAW_DIR = BTV5_DIR / "raw"
PROGRESS_FILE = BTV5_DIR / "upload_progress.json"


def get_conn():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER)


def seed_project(cur):
    """Create the BTV5 project."""
    cur.execute("""
        INSERT INTO projects (name, number, address,
                             project_type, status, start_date, estimated_completion,
                             procore_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (procore_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
    """, (
        "Bay Tower Village Phase 5",
        "BTV5",
        '{"street": "1200 Bay Harbor Dr", "city": "Miami", "state": "FL", "zip": "33154"}',
        "Multi-Family Residential",
        "active",
        "2024-06-01",
        "2026-03-15",
        316469  # Procore sandbox project ID
    ))
    return cur.fetchone()[0]


def seed_companies(cur):
    """Create sample companies (subs/vendors)."""
    companies = [
        ("Atlas Mechanical", "HVAC/Plumbing"),
        ("Coastal Electrical", "Electrical"),
        ("Southern Steel Fabricators", "Structural Steel"),
        ("Miami Fire Protection", "Fire Protection"),
        ("Palm Concrete", "Concrete"),
        ("Tropical Roofing Systems", "Roofing"),
        ("Bayfront Windows & Doors", "Glazing/Curtain Wall"),
        ("Emerald Landscaping", "Landscaping"),
        ("Premier Elevator Co", "Elevators"),
        ("SunCoast Waterproofing", "Waterproofing"),
        ("Dade Drywall & Acoustics", "Drywall/Framing"),
        ("Florida Tile & Stone", "Tile/Flooring"),
        ("Azure Painting", "Painting"),
        ("Metro Plumbing Systems", "Plumbing"),
        ("Guardian Fire & Life Safety", "Fire Alarm"),
    ]
    
    company_ids = {}
    for name, trade in companies:
        cur.execute("""
            INSERT INTO companies (name, trade, address, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (name, trade, '{"city": "Miami", "state": "FL"}'))
        result = cur.fetchone()
        if result:
            company_ids[name] = result[0]
        else:
            cur.execute("SELECT id FROM companies WHERE name = %s", (name,))
            company_ids[name] = cur.fetchone()[0]
    
    return company_ids


def seed_spec_sections(cur, project_id):
    """Create spec sections matching BTV5 submittals."""
    sections = [
        ("03 30 00", "Cast-in-Place Concrete"),
        ("04 20 00", "Unit Masonry"),
        ("05 12 00", "Structural Steel Framing"),
        ("05 50 00", "Metal Fabrications"),
        ("06 10 00", "Rough Carpentry"),
        ("07 10 00", "Dampproofing and Waterproofing"),
        ("07 21 00", "Thermal Insulation"),
        ("07 46 00", "Siding"),
        ("07 54 00", "Thermoplastic Membrane Roofing"),
        ("07 62 00", "Sheet Metal Flashing and Trim"),
        ("07 92 00", "Joint Sealants"),
        ("08 11 00", "Metal Doors and Frames"),
        ("08 14 00", "Wood Doors"),
        ("08 44 13", "Glazed Aluminum Curtain Walls"),
        ("08 71 00", "Door Hardware"),
        ("09 21 16", "Gypsum Board Assemblies"),
        ("09 30 00", "Tiling"),
        ("09 51 00", "Acoustical Ceilings"),
        ("09 65 00", "Resilient Flooring"),
        ("09 91 00", "Painting"),
        ("10 14 00", "Signage"),
        ("10 28 00", "Toilet, Bath, and Laundry Accessories"),
        ("11 13 00", "Loading Dock Equipment"),
        ("12 24 00", "Window Shades"),
        ("14 20 00", "Elevators"),
        ("21 00 00", "Fire Suppression"),
        ("22 00 00", "Plumbing"),
        ("23 00 00", "HVAC"),
        ("23 09 00", "HVAC Controls"),
        ("23 21 13", "Hydronic Piping"),
        ("26 00 00", "Electrical"),
        ("26 05 00", "Electrical Wiring"),
        ("26 24 00", "Switchboards and Panelboards"),
        ("26 51 00", "Interior Lighting"),
        ("27 00 00", "Communications"),
        ("28 00 00", "Fire Detection and Alarm"),
        ("31 23 00", "Excavation and Fill"),
        ("32 12 00", "Asphalt Paving"),
        ("32 90 00", "Planting"),
        ("33 10 00", "Water Utilities"),
    ]
    
    spec_ids = {}
    for number, title in sections:
        cur.execute("""
            INSERT INTO spec_sections (project_id, number, title, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (project_id, number) DO NOTHING
            RETURNING id
        """, (project_id, number, title))
        result = cur.fetchone()
        if result:
            spec_ids[number] = result[0]
        else:
            cur.execute("SELECT id FROM spec_sections WHERE project_id = %s AND number = %s", (project_id, number))
            row = cur.fetchone()
            if row:
                spec_ids[number] = row[0]
    
    return spec_ids


def parse_submittal_files(raw_dir: Path) -> list:
    """Parse submittal info from filenames in the raw directory."""
    submittals = []
    pattern = re.compile(r'^(.*?)(?:[-_]\s*[Rr](\d+))?\.(pdf|PDF)$')
    
    for f in sorted(raw_dir.glob("*.pdf")):
        name = f.stem
        # Try to extract a meaningful title
        # Remove common prefixes like numbers
        title = re.sub(r'^\d+[-_\s]*', '', name)
        title = re.sub(r'[-_]R\d+$', '', title, flags=re.IGNORECASE)
        title = title.replace('_', ' ').replace('-', ' ').strip()
        
        rev_match = re.search(r'[Rr](\d+)', name)
        revision = int(rev_match.group(1)) if rev_match else 0
        
        submittals.append({
            "filename": f.name,
            "title": title or name,
            "revision": revision,
        })
    
    return submittals


def assign_spec_section(title: str, spec_ids: dict) -> int:
    """Heuristically assign a spec section based on submittal title."""
    title_lower = title.lower()
    
    mappings = {
        "hvac": "23 00 00", "air handling": "23 00 00", "vav": "23 00 00",
        "duct": "23 00 00", "fan coil": "23 00 00", "rooftop unit": "23 00 00",
        "chiller": "23 00 00", "cooling tower": "23 00 00",
        "hydronic": "23 21 13", "pipe": "23 21 13", "piping": "23 21 13",
        "controls": "23 09 00", "thermostat": "23 09 00", "bms": "23 09 00",
        "plumb": "22 00 00", "fixture": "22 00 00", "water heater": "22 00 00",
        "electrical": "26 00 00", "panel": "26 24 00", "switchboard": "26 24 00",
        "wire": "26 05 00", "conduit": "26 05 00", "cable": "26 05 00",
        "light": "26 51 00", "luminaire": "26 51 00",
        "fire alarm": "28 00 00", "detection": "28 00 00",
        "fire suppress": "21 00 00", "sprinkler": "21 00 00",
        "steel": "05 12 00", "joist": "05 12 00", "beam": "05 12 00",
        "concrete": "03 30 00", "rebar": "03 30 00",
        "masonry": "04 20 00", "block": "04 20 00", "cmu": "04 20 00",
        "door": "08 11 00", "hardware": "08 71 00", "closer": "08 71 00",
        "window": "08 44 13", "curtain wall": "08 44 13", "glazing": "08 44 13",
        "roof": "07 54 00", "membrane": "07 54 00",
        "waterproof": "07 10 00", "sealant": "07 92 00",
        "insulation": "07 21 00",
        "drywall": "09 21 16", "gypsum": "09 21 16", "framing": "09 21 16",
        "tile": "09 30 00", "ceramic": "09 30 00", "porcelain": "09 30 00",
        "floor": "09 65 00", "carpet": "09 65 00", "vinyl": "09 65 00",
        "paint": "09 91 00", "coating": "09 91 00",
        "ceiling": "09 51 00", "acoustical": "09 51 00",
        "elevator": "14 20 00", "lift": "14 20 00",
        "sign": "10 14 00",
        "toilet": "10 28 00", "accessory": "10 28 00",
        "landscape": "32 90 00", "plant": "32 90 00",
        "paving": "32 12 00", "asphalt": "32 12 00",
        "telecom": "27 00 00", "comm": "27 00 00", "data": "27 00 00",
    }
    
    for keyword, section in mappings.items():
        if keyword in title_lower and section in spec_ids:
            return spec_ids[section]
    
    # Default to first available section
    return list(spec_ids.values())[0] if spec_ids else None


def ingest_submittals(cur, project_id, company_ids, spec_ids):
    """Ingest submittals from BTV5 raw files."""
    submittals = parse_submittal_files(RAW_DIR)
    
    # Group by title (deduplicate revisions — keep highest)
    by_title = {}
    for s in submittals:
        key = s["title"].lower()[:50]
        if key not in by_title or s["revision"] > by_title[key]["revision"]:
            by_title[key] = s
    
    companies_list = list(company_ids.values())
    statuses = ["approved", "approved", "approved", "approved_as_noted", 
                "under_review", "under_review", "submitted", "rejected", "draft"]
    
    count = 0
    for i, (key, s) in enumerate(sorted(by_title.items())):
        number = f"BTV5-{i+1:03d}"
        spec_id = assign_spec_section(s["title"], spec_ids)
        contractor_id = random.choice(companies_list) if companies_list else None
        status = random.choice(statuses)
        
        # Generate realistic dates
        base_date = datetime(2024, 7, 1) + timedelta(days=random.randint(0, 365))
        received = base_date
        submitted = received + timedelta(days=random.randint(1, 5))
        due = submitted + timedelta(days=random.randint(14, 30))
        approved = due + timedelta(days=random.randint(-5, 10)) if status in ("approved", "approved_as_noted") else None
        
        cur.execute("""
            INSERT INTO submittals (project_id, number, title, status, revision,
                                   spec_section_id, responsible_contractor_id,
                                   received_date, submitted_date, required_date,
                                   description, procore_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (
            project_id, number, s["title"], status, s["revision"],
            spec_id, contractor_id,
            received, submitted, due,
            f"Submittal for {s['title']}. Source file: {s['filename']}",
            i + 1000  # Fake procore ID
        ))
        count += 1
    
    return count


def ingest_sample_rfis(cur, project_id, spec_ids):
    """Create sample RFIs that represent real construction questions."""
    rfis = [
        ("Structural beam depth at grid C/4", "Drawing S-301 shows W14x22 at grid C/4. This conflicts with the mechanical duct routing shown on M-201. Available clearance is 9\" which does not accommodate the 14\" VAV box. Please clarify routing priority.", "S-301", "23 00 00", "closed"),
        ("Door hardware spec clarification", "Spec Section 08 71 00 calls for Von Duprin 99 series exit devices. Drawing A-401 Detail 7 notes 'or approved equal.' Please confirm if Sargent 80 series is an acceptable substitute.", "A-401", "08 71 00", "closed"),
        ("Waterproofing membrane at pool deck", "Drawing A-201 shows waterproofing membrane at pool deck level 3. Spec Section 07 10 00 references a different product than what was approved on BTV4. Please confirm product specification.", "A-201", "07 10 00", "open"),
        ("Fire sprinkler main routing through lobby", "Drawing FP-101 routes the fire sprinkler main through the decorative lobby ceiling at Level 1. This conflicts with the architectural ceiling design shown on A-102 RCP. Please provide coordination drawing.", "FP-101", "21 00 00", "open"),
        ("Electrical panel location conflict", "Drawing E-201 locates Panel LP-2A on the wall at grid B/6. Mechanical drawing M-201 shows a 24x24 duct on the same wall. Insufficient clearance for NEC panel access requirements.", "E-201", "26 24 00", "closed"),
        ("Concrete mix design for elevated deck", "Spec Section 03 30 00 requires 5000 PSI concrete for elevated decks. The structural notes on S-101 call for 6000 PSI. Please clarify which governs.", "S-101", "03 30 00", "closed"),
        ("Missing door schedule entry", "Door D-347 shown on A-301 Level 3 plan does not appear in the door schedule on A-801. Please provide frame type, hardware set, and fire rating.", "A-301", "08 11 00", "open"),
        ("HVAC diffuser location conflict", "Drawing M-301 RCP shows a 24x24 supply diffuser centered in Room 305. Structural drawing S-301 shows a W12x26 beam directly above this location. Please confirm diffuser can be offset.", "M-301", "23 00 00", "closed"),
        ("Elevator pit depth discrepancy", "Drawing A-001 shows elevator pit depth at -6'-0\" below Level 1. Elevator shop drawings require -7'-2\" minimum. Structural drawings S-001 show foundation at -6'-0\". Please advise.", "A-001", "14 20 00", "open"),
        ("Tile pattern at main entrance", "Drawing A-501 shows a herringbone tile pattern at the main entrance. Spec Section 09 30 00 references a running bond pattern. Please clarify which pattern governs.", "A-501", "09 30 00", "closed"),
        ("Window sill height ADA compliance", "Drawing A-301 shows window sill height at 36\" AFF in common corridors. ADA requires maximum 36\" sill for operable windows. Please confirm these are fixed windows or provide revised sill height.", "A-301", "08 44 13", "closed"),
        ("Parking garage ventilation requirements", "Drawing M-001 shows CO detection system for parking garage Level B1. Miami-Dade requires CO/NO2 combination sensors per local amendment. Please confirm sensor specification.", "M-001", "23 00 00", "open"),
    ]
    
    count = 0
    for i, (subject, question, drawing, spec, status) in enumerate(rfis):
        spec_id = spec_ids.get(spec)
        base_date = datetime(2024, 8, 1) + timedelta(days=random.randint(0, 300))
        
        cur.execute("""
            INSERT INTO rfis (project_id, number, subject, question, status,
                             date_initiated, due_date,
                             cost_impact, schedule_impact,
                             procore_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (
            project_id, f"BTV5-RFI-{i+1:03d}", subject, question, status,
            base_date, base_date + timedelta(days=14),
            random.choice([True, False]),
            random.choice([True, False]),
            i + 2000
        ))
        
        # Add a response for closed RFIs
        if status == "closed":
            cur.execute("SELECT id FROM rfis WHERE number = %s AND project_id = %s",
                       (f"BTV5-RFI-{i+1:03d}", project_id))
            rfi_row = cur.fetchone()
            if rfi_row:
                cur.execute("""
                    INSERT INTO rfi_responses (rfi_id, body, is_official, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT DO NOTHING
                """, (
                    rfi_row[0],
                    f"See revised drawing {drawing} Rev 2 issued {(base_date + timedelta(days=10)).strftime('%m/%d/%Y')}. Conflict resolved as noted.",
                    True
                ))
        count += 1
    
    return count


def main():
    print("=" * 60)
    print("EVA-00 Database Ingestion — BTV5 Project")
    print("=" * 60)
    
    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor()
    
    try:
        print("\n[1/5] Creating BTV5 project...")
        project_id = seed_project(cur)
        print(f"  → Project ID: {project_id}")
        
        print("[2/5] Creating companies...")
        company_ids = seed_companies(cur)
        print(f"  → {len(company_ids)} companies created")
        
        # Link companies to project
        for cid in company_ids.values():
            cur.execute("""
                INSERT INTO project_companies (project_id, company_id, role, created_at)
                VALUES (%s, %s, 'subcontractor', NOW())
                ON CONFLICT DO NOTHING
            """, (project_id, cid))
        
        print("[3/5] Creating spec sections...")
        spec_ids = seed_spec_sections(cur, project_id)
        print(f"  → {len(spec_ids)} spec sections created")
        
        print("[4/5] Ingesting submittals...")
        sub_count = ingest_submittals(cur, project_id, company_ids, spec_ids)
        print(f"  → {sub_count} submittals ingested")
        
        print("[5/5] Creating sample RFIs...")
        rfi_count = ingest_sample_rfis(cur, project_id, spec_ids)
        print(f"  → {rfi_count} RFIs created")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ BTV5 data ingestion complete!")
        print(f"  Project: Bay Tower Village Phase 5 (ID: {project_id})")
        print(f"  Companies: {len(company_ids)}")
        print(f"  Spec Sections: {len(spec_ids)}")
        print(f"  Submittals: {sub_count}")
        print(f"  RFIs: {rfi_count}")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
