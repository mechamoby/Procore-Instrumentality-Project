"""SteelSync Database Interface — Connection layer for Command Center APIs.

Provides async-compatible database access using psycopg2 with connection pooling.
Connects to the same nerv_eva00 database as EVA-00.
"""

import os
import json
import logging
from contextlib import contextmanager
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg2
import psycopg2.pool
import psycopg2.extras

logger = logging.getLogger("steelsync.db")

# Register UUID adapter
psycopg2.extras.register_uuid()

# Support both DATABASE_URL (Docker) and individual env vars (local dev)
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_NAME = os.environ.get("EVA00_DB", "nerv")
DB_USER = os.environ.get("EVA00_DB_USER", "eva")
DB_HOST = os.environ.get("EVA00_DB_HOST", "localhost")
DB_PORT = os.environ.get("EVA00_DB_PORT", "5432")
DB_PASSWORD = os.environ.get("EVA00_DB_PASSWORD", "")

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None


def _parse_database_url(url: str) -> Dict:
    """Parse postgresql://user:pass@host:port/dbname into connection kwargs."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username or "eva",
        "password": parsed.password or "",
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
    }


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        if DATABASE_URL:
            conn_kwargs = _parse_database_url(DATABASE_URL)
        else:
            conn_kwargs = {
                "dbname": DB_NAME,
                "user": DB_USER,
                "host": DB_HOST,
                "port": DB_PORT,
            }
            if DB_PASSWORD:
                conn_kwargs["password"] = DB_PASSWORD
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            **conn_kwargs,
        )
        logger.info(f"Database pool created: {conn_kwargs.get('dbname')}@{conn_kwargs.get('host')}:{conn_kwargs.get('port')}")
    return _pool


@contextmanager
def get_cursor():
    """Get a database cursor with automatic connection management."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def serialize_row(row: Dict) -> Dict:
    """Convert database row to JSON-serializable dict."""
    if row is None:
        return None
    result = {}
    for key, value in row.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, UUID):
            result[key] = str(value)
        else:
            result[key] = value
    return result


def serialize_rows(rows: List[Dict]) -> List[Dict]:
    """Convert list of database rows to JSON-serializable dicts."""
    return [serialize_row(r) for r in rows]
