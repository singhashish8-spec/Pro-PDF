"""SQLite-backed Markups List (Blueprint v2, Section 4 / 7.6).

One database per PDF, next to the file, mirroring the in-memory
MarkupDocument so the Markups List panel can sort/query it and so it
serves as an audit trail independent of the JSON autosave journal.
"""

from __future__ import annotations

import sqlite3

from app.models.markup import MarkupObject

_COLUMNS = (
    "id",
    "type",
    "page_index",
    "author",
    "created_at",
    "modified_at",
    "text",
    "value",
    "unit",
    "layer",
)


def db_path_for(pdf_path: str) -> str:
    return pdf_path + ".pdfpro-markups.db"


def _connect(pdf_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path_for(pdf_path))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS markups (
            id TEXT PRIMARY KEY,
            type TEXT,
            page_index INTEGER,
            author TEXT,
            created_at TEXT,
            modified_at TEXT,
            text TEXT,
            value REAL,
            unit TEXT,
            layer TEXT
        )"""
    )
    return conn


def _row_for(obj: MarkupObject) -> tuple:
    return (
        obj.id,
        obj.type,
        obj.page_index,
        obj.author,
        obj.created_at,
        obj.modified_at,
        obj.text,
        obj.measurement.value if obj.measurement else None,
        obj.measurement.unit if obj.measurement else None,
        obj.layer,
    )


def sync_all(pdf_path: str, objects: list[MarkupObject]) -> None:
    """Full resync: simple and correct at internal-alpha object counts."""
    conn = _connect(pdf_path)
    try:
        with conn:
            conn.execute("DELETE FROM markups")
            conn.executemany(f"INSERT INTO markups VALUES ({','.join('?' * len(_COLUMNS))})", [_row_for(o) for o in objects])
    finally:
        conn.close()


def list_markups(pdf_path: str, order_by: str = "page_index", descending: bool = False) -> list[dict]:
    if order_by not in _COLUMNS:
        order_by = "page_index"
    direction = "DESC" if descending else "ASC"
    conn = _connect(pdf_path)
    try:
        cursor = conn.execute(f"SELECT * FROM markups ORDER BY {order_by} {direction}")
        return [dict(zip(_COLUMNS, row)) for row in cursor.fetchall()]
    finally:
        conn.close()
