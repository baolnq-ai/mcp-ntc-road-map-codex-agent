from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ntc_code_map.config import ProjectConfig


FileRecord = tuple[str, Path, str]


def _kind_name(obj: dict) -> str:
    kind = obj.get("kindName") or obj.get("kind") or "symbol"
    kind = str(kind).strip()

    mapping = {
        "c": "class",
        "f": "function",
        "m": "member",
        "p": "prototype",
        "v": "variable",
        "i": "interface",
        "e": "enum",
    }
    return mapping.get(kind, kind)


def _ctags_symbols(cfg: ProjectConfig, records: list[FileRecord]) -> list[dict]:
    if not shutil.which("ctags"):
        return []

    if not records:
        return []

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=True) as f:
        for rel, _, _ in records:
            f.write(rel + "\n")
        f.flush()

        cmd = [
            "ctags",
            "--output-format=json",
            "--fields=+nksS",
            "-f",
            "-",
            "-L",
            f.name,
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cfg.root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=90,
            )
        except Exception:
            return []

    if proc.returncode != 0 or not proc.stdout.strip():
        return []

    allowed = {rel for rel, _, _ in records}
    symbols: list[dict] = []

    for line in proc.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        path = str(obj.get("path") or "").replace("\\", "/")
        name = str(obj.get("name") or "").strip()

        if not path or not name or path not in allowed:
            continue

        try:
            line_no = int(obj.get("line") or 1)
        except Exception:
            line_no = 1

        scope = obj.get("scope") or ""
        signature = obj.get("signature") or obj.get("pattern") or ""

        symbols.append(
            {
                "path": path,
                "name": name,
                "kind": _kind_name(obj),
                "line": line_no,
                "scope": str(scope)[:200],
                "signature": str(signature)[:300],
            }
        )

    return symbols


def _patterns_for_ext(ext: str) -> list[tuple[str, str]]:
    if ext == ".py":
        return [
            ("class", r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("function", r"^\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ]

    if ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte"}:
        return [
            ("class", r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)"),
            ("function", r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)"),
            ("function", r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*="),
            ("method", r"^\s*(?:async\s+)?([A-Za-z_$][A-Za-z0-9_$]*)\s*\([^)]*\)\s*\{"),
        ]

    if ext in {".java", ".kt", ".kts", ".cs"}:
        return [
            ("class", r"^\s*(?:public|private|protected|internal|open|final|abstract|sealed|\s)*(?:class|interface|enum|record)\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("method", r"^\s*(?:public|private|protected|internal|static|final|async|override|\s)+[A-Za-z0-9_<>\[\],?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        ]

    if ext == ".go":
        return [
            ("function", r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\("),
            ("type", r"^\s*type\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)"),
        ]

    if ext == ".rs":
        return [
            ("function", r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("type", r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("impl", r"^\s*impl(?:<[^>]+>)?\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ]

    if ext in {".c", ".h", ".cpp", ".hpp", ".cc", ".hh"}:
        return [
            ("class", r"^\s*(?:class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)"),
            ("function", r"^\s*[A-Za-z_][A-Za-z0-9_:\<\>\*&\s]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{?"),
        ]

    if ext in {".sh", ".bash", ".zsh"}:
        return [
            ("function", r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{?"),
        ]

    return []


def _fallback_symbols(records: list[FileRecord]) -> list[dict]:
    symbols: list[dict] = []

    for rel, path, text in records:
        patterns = _patterns_for_ext(path.suffix.lower())
        if not patterns:
            continue

        for line_no, line in enumerate(text.splitlines(), 1):
            for kind, pattern in patterns:
                match = re.search(pattern, line)
                if not match:
                    continue

                symbols.append(
                    {
                        "path": rel,
                        "name": match.group(1),
                        "kind": kind,
                        "line": line_no,
                        "scope": "",
                        "signature": line.strip()[:300],
                    }
                )
                break

    return symbols


def extract_symbols(cfg: ProjectConfig, records: list[FileRecord]) -> tuple[str, list[dict]]:
    ctags = _ctags_symbols(cfg, records)
    if ctags:
        return "ctags-json", ctags

    return "fallback-regex", _fallback_symbols(records)
