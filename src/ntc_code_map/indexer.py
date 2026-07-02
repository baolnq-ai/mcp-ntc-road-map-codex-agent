from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Iterable

from ntc_code_map.config import ProjectConfig, load_config
from ntc_code_map.storage import (
    clear_symbols,
    connect,
    count_files,
    count_symbols,
    db_path,
    get_meta,
    init_db,
    insert_symbol,
    mark_indexed,
    reset_index,
    set_meta,
)
from ntc_code_map.symbols import FileRecord, extract_symbols


def normalize_rel_path(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def file_ext(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix:
        return suffix
    if path.name.startswith("."):
        return path.name.lower()
    return ""


def is_ignored(path: Path, cfg: ProjectConfig) -> bool:
    try:
        rel = path.relative_to(cfg.root)
    except ValueError:
        return True

    ignore_dirs = set(cfg.ignore_dirs)
    return any(part in ignore_dirs for part in rel.parts)


def should_index_file(path: Path, cfg: ProjectConfig) -> bool:
    if is_ignored(path, cfg):
        return False

    ext = file_ext(path)
    if ext not in set(cfg.include_exts):
        return False

    try:
        size = path.stat().st_size
    except OSError:
        return False

    if size <= 0:
        return False

    if size > cfg.max_file_bytes:
        return False

    return True


def iter_source_files(cfg: ProjectConfig) -> Iterable[Path]:
    ignore_dirs = set(cfg.ignore_dirs)

    for dirpath, dirnames, filenames in os.walk(cfg.root):
        current = Path(dirpath)

        dirnames[:] = [name for name in dirnames if name not in ignore_dirs and not name.startswith(".ntc-code-map")]

        if is_ignored(current, cfg):
            continue

        for filename in filenames:
            path = current / filename
            if should_index_file(path, cfg):
                yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()


def index_repo(path: str | Path = ".", force: bool = True) -> dict:
    cfg = load_config(path)
    started = time.time()

    conn = connect(cfg)
    init_db(conn)

    if force:
        reset_index(conn)
    else:
        clear_symbols(conn)

    indexed = 0
    skipped_unreadable = 0
    total_bytes = 0
    records: list[FileRecord] = []

    for file_path in iter_source_files(cfg):
        rel = normalize_rel_path(cfg.root, file_path)

        try:
            text = read_text(file_path)
            stat = file_path.stat()
        except OSError:
            skipped_unreadable += 1
            continue

        ext = file_ext(file_path)
        total_bytes += int(stat.st_size)

        conn.execute(
            """
            INSERT INTO files(path, ext, size, mtime, sha1, content)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                ext = excluded.ext,
                size = excluded.size,
                mtime = excluded.mtime,
                sha1 = excluded.sha1,
                content = excluded.content
            """,
            (
                rel,
                ext,
                int(stat.st_size),
                float(stat.st_mtime),
                sha1_text(text),
                text,
            ),
        )

        records.append((rel, file_path, text))
        indexed += 1

    symbol_source, symbols = extract_symbols(cfg, records)

    for sym in symbols:
        insert_symbol(
            conn,
            path=sym["path"],
            name=sym["name"],
            kind=sym["kind"],
            line=int(sym["line"]),
            scope=sym.get("scope", ""),
            signature=sym.get("signature", ""),
        )

    set_meta(conn, "symbol_source", symbol_source)
    mark_indexed(conn, cfg.root)
    conn.commit()

    file_count = count_files(conn)
    symbol_count = count_symbols(conn)
    conn.close()

    return {
        "root": str(cfg.root),
        "db": str(db_path(cfg)),
        "indexed_files": indexed,
        "total_files_in_db": file_count,
        "symbols": symbol_count,
        "symbol_source": symbol_source,
        "skipped_unreadable": skipped_unreadable,
        "total_bytes": total_bytes,
        "seconds": round(time.time() - started, 3),
    }


def index_status(path: str | Path = ".") -> dict:
    cfg = load_config(path)
    conn = connect(cfg)
    init_db(conn)

    meta = get_meta(conn)
    file_count = count_files(conn)
    symbol_count = count_symbols(conn)

    ext_rows = conn.execute(
        """
        SELECT ext, COUNT(*) AS n
        FROM files
        GROUP BY ext
        ORDER BY n DESC, ext ASC
        LIMIT 30
        """
    ).fetchall()

    kind_rows = conn.execute(
        """
        SELECT kind, COUNT(*) AS n
        FROM symbols
        GROUP BY kind
        ORDER BY n DESC, kind ASC
        LIMIT 30
        """
    ).fetchall()

    conn.close()

    indexed_at = float(meta.get("indexed_at", "0") or 0)
    age_seconds = round(time.time() - indexed_at, 1) if indexed_at else None

    return {
        "root": str(cfg.root),
        "db": str(db_path(cfg)),
        "indexed": bool(indexed_at),
        "age_seconds": age_seconds,
        "files": file_count,
        "symbols": symbol_count,
        "symbol_source": meta.get("symbol_source"),
        "extensions": {str(row["ext"]): int(row["n"]) for row in ext_rows},
        "symbol_kinds": {str(row["kind"]): int(row["n"]) for row in kind_rows},
        "config_file": str(cfg.config_file) if cfg.config_file else None,
    }
