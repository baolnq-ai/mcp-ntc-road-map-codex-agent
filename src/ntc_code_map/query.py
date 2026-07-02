from __future__ import annotations

import re
from pathlib import Path

from ntc_code_map.config import load_config
from ntc_code_map.storage import connect, count_files, count_symbols, init_db

STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "task",
    "code",
    "file",
    "fix",
    "add",
    "use",
    "using",
    "where",
    "how",
    "what",
    "why",
    "when",
    "then",
    "true",
    "false",
    "project",
    "repo",
    "source",
    "class",
    "function",
}


def clean_terms(query: str) -> list[str]:
    terms = re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,}|[0-9]{2,}", query.lower())
    return [term for term in terms if term not in STOP_WORDS][:20]


def score_text(terms: list[str], *chunks: str) -> int:
    score = 0

    for index, chunk in enumerate(chunks):
        text = (chunk or "").lower()
        weight = max(1, 8 - index * 2)

        for term in terms:
            count = text.count(term)
            if count:
                score += min(count, 20) * weight

    return score


def ensure_indexed(path: str | Path = ".") -> None:
    cfg = load_config(path)
    conn = connect(cfg)
    init_db(conn)
    files = count_files(conn)
    symbols = count_symbols(conn)
    conn.close()

    if files <= 0:
        raise RuntimeError("Index is empty. Run: ntc-code-map index .")

    if symbols <= 0:
        raise RuntimeError("Symbol index is empty. Run: ntc-code-map index .")


def find_symbols_text(query: str, path: str | Path = ".", limit: int = 30) -> str:
    cfg = load_config(path)
    ensure_indexed(path)

    terms = clean_terms(query)
    if not terms:
        terms = [query.lower().strip()]

    conn = connect(cfg)
    rows = conn.execute(
        """
        SELECT path, line, kind, name, scope, signature
        FROM symbols
        ORDER BY path, line
        """
    ).fetchall()
    conn.close()

    scored = []
    for row in rows:
        s = score_text(
            terms,
            str(row["name"]),
            str(row["path"]),
            str(row["kind"]),
            str(row["scope"]),
            str(row["signature"]),
        )
        if s > 0:
            scored.append((s, row))

    scored.sort(key=lambda item: (-item[0], str(item[1]["path"]), int(item[1]["line"])))

    out = [f"# Symbol search: {query}"]
    for score, row in scored[:limit]:
        sig = f" :: {row['signature']}" if row["signature"] else ""
        scope = f" scope={row['scope']}" if row["scope"] else ""
        out.append(f"- score={score:03d} {row['path']}:{row['line']} [{row['kind']}] {row['name']}{scope}{sig}")

    return "\n".join(out) if len(out) > 1 else f"No symbols found for: {query}"


def find_files_text(query: str, path: str | Path = ".", limit: int = 30) -> str:
    cfg = load_config(path)
    ensure_indexed(path)

    terms = clean_terms(query)
    if not terms:
        terms = [query.lower().strip()]

    conn = connect(cfg)
    rows = conn.execute(
        """
        SELECT path, ext, size, content
        FROM files
        ORDER BY path
        """
    ).fetchall()
    conn.close()

    scored = []
    for row in rows:
        s = score_text(
            terms,
            str(row["path"]),
            str(row["ext"]),
            str(row["content"]),
        )
        if s > 0:
            scored.append((s, row))

    scored.sort(key=lambda item: (-item[0], str(item[1]["path"])))

    out = [f"# File search: {query}"]
    for score, row in scored[:limit]:
        out.append(f"- score={score:03d} size={row['size']:>7} ext={row['ext']} {row['path']}")

    return "\n".join(out) if len(out) > 1 else f"No files found for: {query}"


def module_map_text(module_path: str, path: str | Path = ".", token_budget: int = 2500) -> str:
    cfg = load_config(path)
    ensure_indexed(path)

    module_path = module_path.strip().strip("/")
    max_chars = max(1200, token_budget * 4)

    conn = connect(cfg)
    files = conn.execute(
        """
        SELECT path, ext, size
        FROM files
        WHERE path = ? OR path LIKE ?
        ORDER BY path
        LIMIT 300
        """,
        (module_path, f"{module_path}/%"),
    ).fetchall()

    symbols = conn.execute(
        """
        SELECT path, line, kind, name, scope, signature
        FROM symbols
        WHERE path = ? OR path LIKE ?
        ORDER BY path, line
        LIMIT 1000
        """,
        (module_path, f"{module_path}/%"),
    ).fetchall()
    conn.close()

    if not files and not symbols:
        return f"No indexed module found for: {module_path}"

    out = [
        f"# Module map: {module_path}",
        "",
        "## Files",
    ]

    for row in files:
        out.append(f"- {row['path']} size={row['size']} ext={row['ext']}")

    out.append("")
    out.append("## Symbols")

    for row in symbols:
        sig = f" :: {row['signature']}" if row["signature"] else ""
        scope = f" scope={row['scope']}" if row["scope"] else ""
        out.append(f"- {row['path']}:{row['line']} [{row['kind']}] {row['name']}{scope}{sig}")

        if len("\n".join(out)) > max_chars:
            out.append("")
            out.append("... truncated by token_budget")
            break

    return "\n".join(out)


def repo_map_text(task: str, path: str | Path = ".", token_budget: int = 3500) -> str:
    """
    Create a compact task-aware repository map.

    This is the main context compression layer. Agents should call this before
    reading files or using broad search.
    """
    cfg = load_config(path)
    ensure_indexed(path)

    terms = clean_terms(task)
    max_chars = max(1200, token_budget * 4)

    conn = connect(cfg)

    files = conn.execute(
        """
        SELECT path, ext, size, content
        FROM files
        ORDER BY path
        """
    ).fetchall()

    symbols = conn.execute(
        """
        SELECT path, line, kind, name, scope, signature
        FROM symbols
        ORDER BY path, line
        """
    ).fetchall()

    conn.close()

    symbols_by_path: dict[str, list] = {}
    symbol_blob_by_path: dict[str, str] = {}

    for row in symbols:
        p = str(row["path"])
        symbols_by_path.setdefault(p, []).append(row)

        blob = " ".join(
            [
                str(row["name"] or ""),
                str(row["kind"] or ""),
                str(row["scope"] or ""),
                str(row["signature"] or ""),
            ]
        )
        symbol_blob_by_path[p] = symbol_blob_by_path.get(p, "") + " " + blob

    priority_markers = [
        "main",
        "index",
        "server",
        "app",
        "cli",
        "command",
        "router",
        "route",
        "controller",
        "service",
        "provider",
        "plugin",
        "adapter",
        "config",
        "settings",
        "env",
        "test",
        "spec",
        "readme",
        "agent",
    ]

    scored_files = []

    for row in files:
        p = str(row["path"])
        ext = str(row["ext"])
        content = str(row["content"] or "")
        symbol_blob = symbol_blob_by_path.get(p, "")

        score = score_text(
            terms,
            p,
            symbol_blob,
            content,
        )

        low_path = p.lower()

        # Generic architecture boost.
        for marker in priority_markers:
            if marker in low_path:
                score += 10

        # Prefer source files over docs/config when task matches code.
        if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}:
            score += 4

        if score > 0:
            scored_files.append((score, row))

    if not scored_files:
        # Fallback generic map for vague tasks.
        for row in files:
            p = str(row["path"])
            low_path = p.lower()
            score = 0

            for marker in priority_markers:
                if marker in low_path:
                    score += 10

            if score > 0:
                scored_files.append((score, row))

    scored_files.sort(key=lambda item: (-item[0], str(item[1]["path"])))

    out = [
        "# NTC Code Map",
        f"Project: {cfg.name}",
        f"Root: {cfg.root}",
        f"Task: {task}",
        f"Token budget: {token_budget}",
        "",
        "## How to use this map",
        "- Use this map before reading source files.",
        "- Inspect listed symbols with Serena `find_symbol` or `get_symbols_overview`.",
        "- Check references/callers with Serena before editing public symbols.",
        "- Read only the smallest relevant slices.",
        "",
        "## Relevant files and symbols",
    ]

    max_files = max(5, min(cfg.max_files, 80))
    max_symbols = max(4, min(cfg.max_symbols_per_file, 32))

    for score, row in scored_files[:max_files]:
        p = str(row["path"])
        out.append("")
        out.append(f"### {p}  score={score} size={row['size']} ext={row['ext']}")

        file_symbols = symbols_by_path.get(p, [])

        if not file_symbols:
            continue

        for sym in file_symbols[:max_symbols]:
            sig = f" :: {sym['signature']}" if sym["signature"] else ""
            scope = f" scope={sym['scope']}" if sym["scope"] else ""
            out.append(f"- L{sym['line']} [{sym['kind']}] {sym['name']}{scope}{sig}")

            if len("\n".join(out)) > max_chars:
                out.append("")
                out.append("... truncated by token_budget")
                return "\n".join(out)

    out.append("")
    out.append("## Next recommended steps")
    out.append("1. Use Serena `find_symbol` on the most relevant symbols above.")
    out.append("2. Use Serena `find_referencing_symbols` before changing public symbols.")
    out.append("3. Use `ntc-code-map module-map <path>` only for the specific module you need.")
    out.append("4. Avoid broad grep/find/full-file reads unless this map is insufficient.")

    return "\n".join(out)
