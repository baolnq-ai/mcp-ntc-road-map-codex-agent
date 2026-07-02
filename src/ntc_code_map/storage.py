from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from ntc_code_map.config import ProjectConfig


def index_dir(root: Path) -> Path:
    path = root / ".ntc-code-map"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path(cfg: ProjectConfig) -> Path:
    return index_dir(cfg.root) / "index.db"


def connect(cfg: ProjectConfig) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(cfg))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            ext TEXT NOT NULL,
            size INTEGER NOT NULL,
            mtime REAL NOT NULL,
            sha1 TEXT NOT NULL,
            content TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            line INTEGER NOT NULL,
            scope TEXT NOT NULL DEFAULT '',
            signature TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
        CREATE INDEX IF NOT EXISTS idx_files_ext ON files(ext);

        CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(path);
        CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
        CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
        """
    )


def reset_index(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM meta;
        DELETE FROM symbols;
        DELETE FROM files;
        """
    )


def clear_symbols(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM symbols")


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO meta(key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_meta(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM meta ORDER BY key").fetchall()
    return {str(row["key"]): str(row["value"]) for row in rows}


def mark_indexed(conn: sqlite3.Connection, root: Path) -> None:
    set_meta(conn, "root", str(root))
    set_meta(conn, "indexed_at", str(time.time()))
    set_meta(conn, "schema_version", "2")


def insert_symbol(
    conn: sqlite3.Connection,
    *,
    path: str,
    name: str,
    kind: str,
    line: int,
    scope: str = "",
    signature: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO symbols(path, name, kind, line, scope, signature)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            path,
            name,
            kind,
            max(1, int(line or 1)),
            scope or "",
            signature or "",
        ),
    )


def count_files(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM files").fetchone()
    return int(row["n"] if row else 0)


def count_symbols(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM symbols").fetchone()
    return int(row["n"] if row else 0)
