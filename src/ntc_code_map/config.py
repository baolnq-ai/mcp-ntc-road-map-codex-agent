from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_ROOT_MARKERS = [
    ".git",
    "AGENTS.md",
    "pyproject.toml",
    "package.json",
    "pnpm-workspace.yaml",
    "yarn.lock",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
]

DEFAULT_IGNORE_DIRS = [
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "out",
    "target",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    ".ntc-code-map",
]

DEFAULT_INCLUDE_EXTS = [
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".java",
    ".kt",
    ".kts",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".hh",
    ".cs",
    ".php",
    ".rb",
    ".sh",
    ".bash",
    ".zsh",
    ".lua",
    ".dart",
    ".vue",
    ".svelte",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".env",
    ".md",
]


@dataclass(frozen=True)
class ProjectConfig:
    name: str = ""
    root: Path = Path(".")
    root_markers: list[str] = field(default_factory=lambda: list(DEFAULT_ROOT_MARKERS))

    include_exts: list[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE_EXTS))
    ignore_dirs: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_DIRS))
    max_file_bytes: int = 700_000

    default_token_budget: int = 3500
    max_files: int = 80
    max_symbols_per_file: int = 24

    config_file: Path | None = None


def _as_str_list(value: object, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list):
        return list(default)
    return [str(x) for x in value]


def _as_int(value: object, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def find_project_root(start: str | Path = ".") -> Path:
    current = Path(start).expanduser().resolve()
    if current.is_file():
        current = current.parent

    env_root = os.environ.get("NTC_CODE_MAP_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    for path in [current, *current.parents]:
        if (path / ".ntc-code-map.toml").exists():
            return path
        for marker in DEFAULT_ROOT_MARKERS:
            if (path / marker).exists():
                return path

    return current


def load_config(start: str | Path = ".") -> ProjectConfig:
    root = find_project_root(start)
    config_path = root / ".ntc-code-map.toml"

    raw: dict = {}
    if config_path.exists():
        with config_path.open("rb") as f:
            raw = tomllib.load(f)

    project = raw.get("project", {}) if isinstance(raw.get("project", {}), dict) else {}
    index = raw.get("index", {}) if isinstance(raw.get("index", {}), dict) else {}
    ranking = raw.get("ranking", {}) if isinstance(raw.get("ranking", {}), dict) else {}

    return ProjectConfig(
        name=str(project.get("name") or root.name),
        root=root,
        root_markers=_as_str_list(project.get("root_markers"), DEFAULT_ROOT_MARKERS),
        include_exts=_as_str_list(index.get("include_exts"), DEFAULT_INCLUDE_EXTS),
        ignore_dirs=_as_str_list(index.get("ignore_dirs"), DEFAULT_IGNORE_DIRS),
        max_file_bytes=_as_int(index.get("max_file_bytes"), 700_000),
        default_token_budget=_as_int(ranking.get("default_token_budget"), 3500),
        max_files=_as_int(ranking.get("max_files"), 80),
        max_symbols_per_file=_as_int(ranking.get("max_symbols_per_file"), 24),
        config_file=config_path if config_path.exists() else None,
    )


def create_default_config(path: str | Path = ".ntc-code-map.toml", name: str | None = None) -> Path:
    target = Path(path).expanduser().resolve()
    project_name = name or target.parent.name

    if target.exists():
        return target

    include = '".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".md", ".toml", ".yaml", ".yml", ".json", ".sh"'
    ignore = '".git", "node_modules", "dist", "build", ".venv", "__pycache__", ".cache", ".ntc-code-map"'
    markers = '".git", "AGENTS.md", "pyproject.toml", "package.json", "go.mod", "Cargo.toml"'

    target.write_text(
        f'''[project]
name = "{project_name}"
root_markers = [{markers}]

[index]
include_exts = [{include}]
ignore_dirs = [{ignore}]
max_file_bytes = 700000

[ranking]
default_token_budget = 3500
max_files = 80
max_symbols_per_file = 24
''',
        encoding="utf-8",
    )
    return target
