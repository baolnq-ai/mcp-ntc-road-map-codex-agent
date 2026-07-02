from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path


SERVER_NAME = "ntc_code_map"


def default_codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def resolve_executable(command: str | None = None) -> str:
    if command:
        return str(Path(command).expanduser().resolve())

    found = shutil.which("ntc-code-map")
    if found:
        return str(Path(found).resolve())

    raise RuntimeError("Cannot find `ntc-code-map` in PATH. Activate venv or install package first.")


def build_mcp_block(command: str) -> str:
    return f'''[mcp_servers.{SERVER_NAME}]
command = {json.dumps(command)}
args = ["serve"]
startup_timeout_sec = 20
tool_timeout_sec = 180
required = true
'''


def upsert_mcp_block(
    config_path: str | Path | None = None,
    command: str | None = None,
    dry_run: bool = False,
) -> dict:
    path = Path(config_path).expanduser().resolve() if config_path else default_codex_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    exe = resolve_executable(command)
    block = build_mcp_block(exe)

    old = path.read_text(encoding="utf-8") if path.exists() else ""

    pattern = re.compile(
        rf"(?ms)^\[mcp_servers\.{re.escape(SERVER_NAME)}\]\n.*?(?=^\[|\Z)"
    )

    if pattern.search(old):
        new = pattern.sub(block.rstrip() + "\n\n", old).rstrip() + "\n"
        action = "replaced"
    else:
        new = old.rstrip() + "\n\n" + block if old.strip() else block
        action = "added"

    changed = new != old

    backup = None
    if changed and not dry_run:
        if path.exists():
            backup = path.with_name(path.name + f".bak.{time.strftime('%Y%m%d-%H%M%S')}")
            backup.write_text(old, encoding="utf-8")
        path.write_text(new, encoding="utf-8")

    return {
        "config": str(path),
        "server": SERVER_NAME,
        "command": exe,
        "action": action if changed else "unchanged",
        "changed": changed,
        "dry_run": dry_run,
        "backup": str(backup) if backup else None,
        "block": block,
    }
