from __future__ import annotations

import time
from pathlib import Path

MARKER_START = "<!-- ntc-code-map:start -->"
MARKER_END = "<!-- ntc-code-map:end -->"


AGENTS_BLOCK = f"""{MARKER_START}
## NTC Code Map + Serena workflow

For non-trivial coding tasks, optimize for correctness and low token usage.

Before reading source files or using broad shell search:

1. Call `ntc_code_map.index_status`.
2. If the index is missing or stale, call `ntc_code_map.index_repo`.
3. Call `ntc_code_map.repo_map(task, token_budget=2500-4000)`.
4. Use `ntc_code_map.find_symbols`, `find_files`, or `module_map` only for focused follow-up.
5. Then use Serena symbolic tools for exact navigation:
   - `find_symbol`
   - `get_symbols_overview` on specific files only
   - `find_referencing_symbols`
   - `find_implementations`
6. Read only the smallest relevant code slices.
7. Before editing public symbols, inspect references/callers/tests/configs.
8. Propose the smallest safe edit plan before modifying files.
9. Run the smallest relevant test/lint command first.

Avoid:
- broad `grep -R`, `find .`, `tree`, `ls -R` before repo-map
- reading whole large files
- dumping huge logs
- touching unrelated files
- creating duplicate helpers/services/providers
- changing public APIs without reference checks
{MARKER_END}
"""


def init_agents(path: str | Path = ".", dry_run: bool = False) -> dict:
    root = Path(path).expanduser().resolve()
    if root.is_file():
        root = root.parent

    target = root / "AGENTS.md"
    old = target.read_text(encoding="utf-8") if target.exists() else ""

    if MARKER_START in old and MARKER_END in old:
        before = old.split(MARKER_START, 1)[0].rstrip()
        after = old.split(MARKER_END, 1)[1].lstrip()
        new = before + "\n\n" + AGENTS_BLOCK + "\n"
        if after:
            new += "\n" + after
        action = "replaced"
    else:
        if old.strip():
            new = old.rstrip() + "\n\n" + AGENTS_BLOCK + "\n"
            action = "appended"
        else:
            new = "# AGENTS.md\n\n" + AGENTS_BLOCK + "\n"
            action = "created"

    changed = new != old
    backup = None

    if changed and not dry_run:
        if target.exists():
            backup = target.with_name(target.name + f".bak.{time.strftime('%Y%m%d-%H%M%S')}")
            backup.write_text(old, encoding="utf-8")
        target.write_text(new, encoding="utf-8")

    return {
        "path": str(target),
        "action": action if changed else "unchanged",
        "changed": changed,
        "dry_run": dry_run,
        "backup": str(backup) if backup else None,
    }
