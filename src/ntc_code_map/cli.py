from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

from ntc_code_map import __version__
from ntc_code_map.agents import init_agents
from ntc_code_map.codex_config import upsert_mcp_block
from ntc_code_map.config import create_default_config, load_config
from ntc_code_map.indexer import index_repo, index_status
from ntc_code_map.query import find_files_text, find_symbols_text, module_map_text, repo_map_text


def print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_version(_: argparse.Namespace) -> int:
    print(f"ntc-code-map {__version__}")
    return 0


def cmd_root(args: argparse.Namespace) -> int:
    cfg = load_config(args.path)
    print(cfg.root)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    cfg = load_config(args.path)
    data = asdict(cfg)
    data["root"] = str(cfg.root)
    data["config_file"] = str(cfg.config_file) if cfg.config_file else None

    print("NTC Code Map Config")
    print("===================")
    for key, value in data.items():
        print(f"{key}: {value}")

    return 0


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path).expanduser().resolve() / ".ntc-code-map.toml"
    created = not target.exists()
    path = create_default_config(target, name=args.name)
    print(("created: " if created else "exists:  ") + str(path))
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    result = index_repo(args.path, force=not args.no_force)
    print_json(result)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    result = index_status(args.path)
    print_json(result)
    return 0


def cmd_find_symbols(args: argparse.Namespace) -> int:
    print(find_symbols_text(args.query, path=args.path, limit=args.limit))
    return 0


def cmd_find_files(args: argparse.Namespace) -> int:
    print(find_files_text(args.query, path=args.path, limit=args.limit))
    return 0


def cmd_module_map(args: argparse.Namespace) -> int:
    print(module_map_text(args.module_path, path=args.path, token_budget=args.token_budget))
    return 0


def cmd_repo_map(args: argparse.Namespace) -> int:
    print(repo_map_text(args.task, path=args.path, token_budget=args.token_budget))
    return 0


def cmd_init_agents(args: argparse.Namespace) -> int:
    result = init_agents(args.path, dry_run=args.dry_run)
    print_json(result)
    return 0


def cmd_init_codex(args: argparse.Namespace) -> int:
    result = upsert_mcp_block(
        config_path=args.config,
        command=args.command,
        dry_run=args.dry_run,
    )
    print_json(result)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config(args.path)

    checks = []
    checks.append(("python", sys.version.split()[0], True))
    checks.append(("sqlite3", sqlite3.sqlite_version, True))

    rg = shutil.which("rg")
    checks.append(("ripgrep/rg", rg or "not found", bool(rg)))

    ctags = shutil.which("ctags")
    checks.append(("ctags", ctags or "not found", bool(ctags)))

    print("NTC Code Map Doctor")
    print("===================")
    for name, value, ok in checks:
        status = "OK" if ok else "WARN"
        print(f"{status:4} {name:12} {value}")

    print()
    print(f"root:        {cfg.root}")
    print(f"config_file: {cfg.config_file or 'default config'}")
    print(f"project:     {cfg.name}")
    print(f"cwd:         {Path.cwd()}")
    print(f"home:        {Path.home()}")

    return 0 if rg else 1


def cmd_serve(_: argparse.Namespace) -> int:
    # Important: do not print anything to stdout before starting MCP stdio.
    from ntc_code_map.server import run_server

    run_server()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ntc-code-map",
        description="Portable code-map MCP server for token-efficient coding agents.",
    )

    sub = parser.add_subparsers(dest="command")

    p_version = sub.add_parser("version", help="Show version")
    p_version.set_defaults(func=cmd_version)

    p_root = sub.add_parser("root", help="Print detected project root")
    p_root.add_argument("path", nargs="?", default=".")
    p_root.set_defaults(func=cmd_root)

    p_config = sub.add_parser("config", help="Print resolved project config")
    p_config.add_argument("path", nargs="?", default=".")
    p_config.set_defaults(func=cmd_config)

    p_init = sub.add_parser("init", help="Create .ntc-code-map.toml in a project")
    p_init.add_argument("path", nargs="?", default=".")
    p_init.add_argument("--name", default=None)
    p_init.set_defaults(func=cmd_init)

    p_index = sub.add_parser("index", help="Index source files and symbols into SQLite")
    p_index.add_argument("path", nargs="?", default=".")
    p_index.add_argument("--no-force", action="store_true", help="Do not reset index before indexing")
    p_index.set_defaults(func=cmd_index)

    p_status = sub.add_parser("status", help="Show current index status")
    p_status.add_argument("path", nargs="?", default=".")
    p_status.set_defaults(func=cmd_status)

    p_find_symbols = sub.add_parser("find-symbols", help="Search indexed symbols")
    p_find_symbols.add_argument("query")
    p_find_symbols.add_argument("--path", default=".")
    p_find_symbols.add_argument("--limit", type=int, default=30)
    p_find_symbols.set_defaults(func=cmd_find_symbols)

    p_find_files = sub.add_parser("find-files", help="Search indexed files")
    p_find_files.add_argument("query")
    p_find_files.add_argument("--path", default=".")
    p_find_files.add_argument("--limit", type=int, default=30)
    p_find_files.set_defaults(func=cmd_find_files)

    p_module_map = sub.add_parser("module-map", help="Show compact map for a file or directory")
    p_module_map.add_argument("module_path")
    p_module_map.add_argument("--path", default=".")
    p_module_map.add_argument("--token-budget", type=int, default=2500)
    p_module_map.set_defaults(func=cmd_module_map)

    p_repo_map = sub.add_parser("repo-map", help="Create compact task-aware repository map")
    p_repo_map.add_argument("task")
    p_repo_map.add_argument("--path", default=".")
    p_repo_map.add_argument("--token-budget", type=int, default=3500)
    p_repo_map.set_defaults(func=cmd_repo_map)

    p_init_agents = sub.add_parser("init-agents", help="Create/update AGENTS.md with ntc-code-map workflow")
    p_init_agents.add_argument("path", nargs="?", default=".")
    p_init_agents.add_argument("--dry-run", action="store_true")
    p_init_agents.set_defaults(func=cmd_init_agents)

    p_init_codex = sub.add_parser("init-codex", help="Install/update Codex MCP config for ntc-code-map")
    p_init_codex.add_argument("--config", default=None, help="Path to Codex config.toml")
    p_init_codex.add_argument("--command", default=None, help="Path to ntc-code-map executable")
    p_init_codex.add_argument("--dry-run", action="store_true", help="Print planned config without writing")
    p_init_codex.set_defaults(func=cmd_init_codex)

    p_doctor = sub.add_parser("doctor", help="Check local dependencies")
    p_doctor.add_argument("path", nargs="?", default=".")
    p_doctor.set_defaults(func=cmd_doctor)

    p_serve = sub.add_parser("serve", help="Run MCP server")
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
