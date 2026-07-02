from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ntc_code_map.indexer import index_repo as index_repo_impl
from ntc_code_map.indexer import index_status as index_status_impl
from ntc_code_map.query import (
    find_files_text,
    find_symbols_text,
    module_map_text,
    repo_map_text,
)


INSTRUCTIONS = """
Use ntc-code-map before reading source files.

Recommended flow:
1. Call index_status for the current repo.
2. If missing/stale, call index_repo.
3. Call repo_map(task, token_budget) before broad exploration.
4. Use find_symbols/find_files/module_map only for focused follow-up.
5. Then use Serena for exact symbol navigation and references.
Avoid full-file dumps and broad grep/find/tree before repo_map.
"""


mcp = FastMCP(
    name="ntc-code-map",
    instructions=INSTRUCTIONS,
)


@mcp.tool()
def index_repo(root: str = ".", force: bool = True) -> dict[str, Any]:
    """
    Build or rebuild the ntc-code-map SQLite index for a repository.

    Use this after large source changes or when index_status reports missing/stale index.
    """
    return index_repo_impl(root, force=force)


@mcp.tool()
def index_status(root: str = ".") -> dict[str, Any]:
    """
    Return current ntc-code-map index status for a repository.
    """
    return index_status_impl(root)


@mcp.tool()
def repo_map(task: str, root: str = ".", token_budget: int = 3500) -> str:
    """
    Create a compact task-aware repository map.

    Call this before reading files or doing broad code exploration.
    """
    return repo_map_text(task, path=root, token_budget=token_budget)


@mcp.tool()
def find_symbols(query: str, root: str = ".", limit: int = 30) -> str:
    """
    Search indexed symbols by name, path, kind, scope, or signature.
    """
    return find_symbols_text(query, path=root, limit=limit)


@mcp.tool()
def find_files(query: str, root: str = ".", limit: int = 30) -> str:
    """
    Search indexed files by path and content.
    """
    return find_files_text(query, path=root, limit=limit)


@mcp.tool()
def module_map(module_path: str, root: str = ".", token_budget: int = 2500) -> str:
    """
    Return a compact file/symbol map for one specific file or directory.
    """
    return module_map_text(module_path, path=root, token_budget=token_budget)


def run_server() -> None:
    mcp.run()


if __name__ == "__main__":
    run_server()
