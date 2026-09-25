"""
db.py — SQLite schema management and helper functions for RECON.

All pipeline stages read and write to case.db to maintain state and forensic auditability.
"""

import sqlite3
import os
import logging
from typing import Optional, Any, List, Dict

logger = logging.getLogger(__name__)

def get_connection(db_path: str) -> sqlite3.Connection:
    """Returns a SQLite connection configured with WAL mode and dict row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(db_path: str) -> None:
    """Initializes SQLite schema for RECON analysis case database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Meta table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    
    # Blocks table (4KB sector block map)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            offset INTEGER PRIMARY KEY,
            type_pred TEXT,
            entropy REAL,
            confidence REAL,
            claimed INTEGER DEFAULT 0
        );
    """)
    
    # Recovered artifacts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            source_offset INTEGER,
            size INTEGER,
            method TEXT CHECK(method IN ('fs', 'carve', 'reassembled')),
            status TEXT CHECK(status IN ('FULL', 'PARTIAL', 'FRAGMENT', 'ENCRYPTED', 'UNRECOVERABLE')),
            confidence REAL,
            score REAL,
            hash_sha256 TEXT,
            tlsh_hash TEXT,
            mime_type TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    
    # Artifact block fragments mapping
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fragments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id INTEGER REFERENCES artifacts(id) ON DELETE CASCADE,
            block_offset INTEGER,
            seq INTEGER
        );
    """)
    
    # Relationship graph table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_id INTEGER REFERENCES artifacts(id) ON DELETE CASCADE,
            dst_id INTEGER REFERENCES artifacts(id) ON DELETE CASCADE,
            rel_type TEXT CHECK(rel_type IN ('duplicate', 'similar', 'fragment_of', 'same_folder')),
            score REAL
        );
    """)
    
    # LLM Summaries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            artifact_id INTEGER PRIMARY KEY REFERENCES artifacts(id) ON DELETE CASCADE,
            summary TEXT,
            entities TEXT,
            generated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"Initialized database schema at {db_path}")

def upsert_meta(db_path: str, key: str, value: str) -> None:
    """Inserts or updates a key-value pair in case_meta."""
    conn = get_connection(db_path)
    conn.execute("INSERT OR REPLACE INTO case_meta (key, value) VALUES (?, ?);", (key, value))
    conn.commit()
    conn.close()

def get_meta(db_path: str, key: str) -> Optional[str]:
    """Retrieves a value from case_meta by key."""
    conn = get_connection(db_path)
    cursor = conn.execute("SELECT value FROM case_meta WHERE key = ?;", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None

def insert_block(conn: sqlite3.Connection, offset: int, type_pred: str, entropy: float, confidence: float) -> None:
    """Inserts a predicted block into the blocks table."""
    conn.execute(
        "INSERT OR REPLACE INTO blocks (offset, type_pred, entropy, confidence) VALUES (?, ?, ?, ?);",
        (offset, type_pred, entropy, confidence)
    )

def claim_blocks(conn: sqlite3.Connection, offsets: List[int]) -> None:
    """Marks specified block offsets as claimed by filesystem recovery."""
    conn.executemany(
        "UPDATE blocks SET claimed = 1 WHERE offset = ?;",
        [(off,) for off in offsets]
    )

def insert_artifact(conn: sqlite3.Connection, **kwargs: Any) -> int:
    """Inserts an artifact record and returns its generated ID."""
    keys = list(kwargs.keys())
    values = list(kwargs.values())
    placeholders = ", ".join(["?"] * len(keys))
    columns = ", ".join(keys)
    
    sql = f"INSERT INTO artifacts ({columns}) VALUES ({placeholders});"
    cursor = conn.execute(sql, values)
    return cursor.lastrowid

def insert_fragment(conn: sqlite3.Connection, artifact_id: int, block_offset: int, seq: int) -> None:
    """Links a block offset to an artifact fragment sequence."""
    conn.execute(
        "INSERT INTO fragments (artifact_id, block_offset, seq) VALUES (?, ?, ?);",
        (artifact_id, block_offset, seq)
    )

def insert_relationship(conn: sqlite3.Connection, src_id: int, dst_id: int, rel_type: str, score: float) -> None:
    """Records an edge in the relationship graph between two artifacts."""
    conn.execute(
        "INSERT INTO relationships (src_id, dst_id, rel_type, score) VALUES (?, ?, ?, ?);",
        (src_id, dst_id, rel_type, score)
    )

def get_unclaimed_blocks(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Returns list of unclaimed blocks ordered by offset."""
    cursor = conn.execute("SELECT * FROM blocks WHERE claimed = 0 ORDER BY offset ASC;")
    return [dict(row) for row in cursor.fetchall()]
