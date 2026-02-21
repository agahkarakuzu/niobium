"""
Niobium cache — tracks processed images and caches Claude API responses.

DB location: ~/.config/niobium/cache.db
"""

import sqlite3
import hashlib
import json
import time
from pathlib import Path

CACHE_DIR = Path.home() / ".config" / "niobium"
CACHE_DB = CACHE_DIR / "cache.db"

_conn = None


def _get_conn():
    global _conn
    if _conn is None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(CACHE_DB))
        _conn.execute("PRAGMA journal_mode=WAL")
        _init_tables(_conn)
    return _conn


def _init_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed (
            content_hash  TEXT PRIMARY KEY,
            source        TEXT,
            processed_at  REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS claude_cache (
            cache_key      TEXT PRIMARY KEY,
            response_json  TEXT,
            model          TEXT,
            created_at     REAL
        )
    """)
    conn.commit()


# ── Content hashing ──────────────────────────────────────────────────

def content_hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def content_hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


# ── Processed-image table ────────────────────────────────────────────

def is_processed(content_hash):
    row = _get_conn().execute(
        "SELECT 1 FROM processed WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    return row is not None


def mark_processed(content_hash, source):
    _get_conn().execute(
        "INSERT OR REPLACE INTO processed (content_hash, source, processed_at) VALUES (?, ?, ?)",
        (content_hash, source, time.time()),
    )
    _get_conn().commit()


# ── Claude response cache ────────────────────────────────────────────

def _claude_cache_key(image_bytes_hash, text_list_json, model, instructions):
    parts = f"{image_bytes_hash}\n{text_list_json}\n{model}\n{instructions or ''}"
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


def get_cached_claude_response(image_bytes_hash, text_list_json, model, instructions):
    key = _claude_cache_key(image_bytes_hash, text_list_json, model, instructions)
    row = _get_conn().execute(
        "SELECT response_json FROM claude_cache WHERE cache_key = ?", (key,)
    ).fetchone()
    if row is not None:
        return json.loads(row[0])
    return None


def set_cached_claude_response(image_bytes_hash, text_list_json, model, instructions, response_data):
    key = _claude_cache_key(image_bytes_hash, text_list_json, model, instructions)
    _get_conn().execute(
        "INSERT OR REPLACE INTO claude_cache (cache_key, response_json, model, created_at) VALUES (?, ?, ?, ?)",
        (key, json.dumps(response_data), model, time.time()),
    )
    _get_conn().commit()


# ── Maintenance ──────────────────────────────────────────────────────

def clear_all():
    conn = _get_conn()
    conn.execute("DELETE FROM processed")
    conn.execute("DELETE FROM claude_cache")
    conn.commit()


def stats():
    conn = _get_conn()
    p = conn.execute("SELECT COUNT(*) FROM processed").fetchone()[0]
    c = conn.execute("SELECT COUNT(*) FROM claude_cache").fetchone()[0]
    return {"processed": p, "claude_cache": c}
