#!/usr/bin/env python3
"""Initialize SteelSync Intelligence Layer — Apply schema and verify tables.

Usage:
    python3 scripts/init-intelligence-layer.py [--verify-only]

Applies INTELLIGENCE-LAYER-SCHEMA.sql to the nerv_eva00 database.
Safely skips if tables already exist.
"""

import os
import sys
import argparse
from pathlib import Path

import psycopg2

DB_NAME = os.environ.get("EVA00_DB", "nerv_eva00")
DB_USER = os.environ.get("EVA00_DB_USER", "moby")
DB_HOST = os.environ.get("EVA00_DB_HOST", "localhost")
DB_PORT = os.environ.get("EVA00_DB_PORT", "5432")

SCHEMA_FILE = Path(__file__).parent.parent / "eva-agent" / "eva-00-design" / "INTELLIGENCE-LAYER-SCHEMA.sql"

EXPECTED_TABLES = [
    "signals",
    "synthesis_cycles",
    "intelligence_items",
    "intelligence_item_evidence",
    "working_memory_state",
    "reinforcement_candidates",
    "radar_items",
    "radar_activity",
    "radar_document_links",
]

EXPECTED_TYPES = [
    "signal_source_type",
    "signal_category",
    "decay_profile",
    "synthesis_cycle_type",
    "project_health",
    "intelligence_item_type",
    "intelligence_severity",
    "intelligence_status",
    "attention_level",
    "evidence_weight",
    "reinforcement_status",
    "radar_priority",
    "radar_status",
    "radar_activity_type",
    "radar_link_source",
]


def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, host=DB_HOST, port=DB_PORT,
    )


def check_tables(conn):
    """Check which expected tables exist."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        existing = {row[0] for row in cur.fetchall()}

    results = {}
    for table in EXPECTED_TABLES:
        results[table] = table in existing
    return results


def check_types(conn):
    """Check which expected enum types exist."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT typname FROM pg_type
            WHERE typtype = 'e' AND typnamespace = (
                SELECT oid FROM pg_namespace WHERE nspname = 'public'
            )
        """)
        existing = {row[0] for row in cur.fetchall()}

    results = {}
    for t in EXPECTED_TYPES:
        results[t] = t in existing
    return results


def apply_schema(conn):
    """Apply the intelligence layer schema."""
    sql = SCHEMA_FILE.read_text()

    # Split into individual statements and run each one,
    # wrapping in IF NOT EXISTS where possible
    with conn.cursor() as cur:
        # First check if any intelligence tables exist
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'signals'
            )
        """)
        if cur.fetchone()[0]:
            print("Intelligence layer tables already exist. Use --verify-only to check state.")
            print("To re-apply, drop existing tables first (manual operation).")
            return False

    # Apply the full schema as a single transaction
    with conn.cursor() as cur:
        try:
            cur.execute(sql)
            conn.commit()
            print("Schema applied successfully.")
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error applying schema: {e}")
            return False


def verify(conn):
    """Print verification report."""
    print("\n=== SteelSync Intelligence Layer Verification ===\n")

    print("Database:", DB_NAME)
    print("Host:", DB_HOST)
    print()

    # Check tables
    tables = check_tables(conn)
    print("Tables:")
    all_ok = True
    for name, exists in tables.items():
        status = "OK" if exists else "MISSING"
        print(f"  {name:40s} [{status}]")
        if not exists:
            all_ok = False

    print()

    # Check types
    types = check_types(conn)
    print("Enum Types:")
    for name, exists in types.items():
        status = "OK" if exists else "MISSING"
        print(f"  {name:40s} [{status}]")
        if not exists:
            all_ok = False

    print()

    # Check row counts
    if all_ok:
        print("Row Counts:")
        with conn.cursor() as cur:
            for table in EXPECTED_TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  {table:40s} {count:>6d} rows")

    print()

    # Check indexes
    with conn.cursor() as cur:
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename IN %s AND schemaname = 'public'
        """, (tuple(EXPECTED_TABLES),))
        indexes = [row[0] for row in cur.fetchall()]
        print(f"Indexes: {len(indexes)} found on intelligence layer tables")

    print()

    if all_ok:
        print("STATUS: All intelligence layer components present.")
    else:
        print("STATUS: Some components missing. Run without --verify-only to apply schema.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Initialize SteelSync Intelligence Layer")
    parser.add_argument("--verify-only", action="store_true", help="Only verify, don't apply schema")
    args = parser.parse_args()

    if not SCHEMA_FILE.exists():
        print(f"Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)

    conn = get_conn()

    try:
        if args.verify_only:
            ok = verify(conn)
            sys.exit(0 if ok else 1)
        else:
            success = apply_schema(conn)
            if success:
                verify(conn)
            sys.exit(0 if success else 1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
