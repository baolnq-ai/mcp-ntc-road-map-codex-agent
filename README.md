# ntc-code-map

**Portable MCP code-map server for token-efficient coding agents.**

`ntc-code-map` builds a lightweight index of your repository's files and symbols, then serves a compact, task-aware code map over the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). Coding agents like [Codex](https://openai.com/codex) use it to understand project structure **before** reading files — saving thousands of tokens per session.

## Why?

LLM coding agents waste tokens on broad `grep`, `find`, and full-file reads to orient themselves. `ntc-code-map` compresses this into a single ranked map call:

| Without ntc-code-map | With ntc-code-map |
|---|---|
| Agent reads 10+ files to understand structure | Agent gets a ranked map in ~3500 tokens |
| Broad `grep -R`, `tree`, `ls -R` | One `repo_map(task)` call |
| No symbol awareness | Symbol-level navigation + references |

## Quick Start

### 1. Install

```bash
pip install ntc-code-map
```

### 2. Initialize in your project

```bash
cd your-project

# Create config
ntc-code-map init

# Build the index
ntc-code-map index

# Check status
ntc-code-map status
```

### 3. Use with Codex

```bash
# Auto-configure Codex MCP integration
ntc-code-map init-codex

# Auto-inject workflow into AGENTS.md
ntc-code-map init-agents
```

That's it! Codex will now use `ntc-code-map` automatically.

## MCP Tools

When running as an MCP server, these tools are available:

| Tool | Description |
|---|---|
| `index_status` | Check if the repo index exists and is fresh |
| `index_repo` | Build/rebuild the SQLite index |
| `repo_map` | Task-aware ranked map of relevant files + symbols |
| `find_symbols` | Search symbols by name, kind, scope, signature |
| `find_files` | Search files by path and content |
| `module_map` | Compact map for a specific file or directory |

### Recommended agent workflow

```
1. index_status    → is the index fresh?
2. index_repo      → rebuild if stale
3. repo_map(task)  → get ranked context
4. find_symbols()  → focused follow-up
5. Serena tools    → exact symbol navigation
```

## CLI Reference

```bash
ntc-code-map init             # Create .ntc-code-map.toml
ntc-code-map index            # Index source files + symbols
ntc-code-map status           # Show index status
ntc-code-map repo-map "task"  # Generate task-aware map
ntc-code-map find-symbols "query"
ntc-code-map find-files "query"
ntc-code-map module-map src/
ntc-code-map serve            # Start MCP server (stdio)
ntc-code-map init-codex       # Configure Codex MCP
ntc-code-map init-agents      # Inject workflow into AGENTS.md
ntc-code-map doctor           # Check dependencies
ntc-code-map version
```

## Configuration

Create `.ntc-code-map.toml` in your project root:

```toml
[project]
name = "my-project"
root_markers = [".git", "pyproject.toml", "package.json"]

[index]
include_exts = [".py", ".ts", ".js", ".go", ".rs", ".java", ".md"]
ignore_dirs = [".git", "node_modules", "dist", "build", ".venv"]

[ranking]
default_token_budget = 3500
max_files = 80
max_symbols_per_file = 24
```

## How it works

1. **Index**: Scans source files, extracts symbols using [ctags](https://ctags.io/) (with regex fallback), stores everything in a local SQLite database (`.ntc-code-map/index.db`).

2. **Score**: When `repo_map(task)` is called, it scores every file against the task description using symbol names, file paths, and content matching.

3. **Map**: Returns a compact Markdown map with ranked files, their symbols (kind, line, signature), and next-step recommendations — all within the token budget.

## Dependencies

- Python ≥ 3.11
- `mcp` ≥ 1.0.0 (for MCP server)
- Optional: `ctags` for better symbol extraction (falls back to regex)

## Development

```bash
git clone https://github.com/ntc-ai/ntc-code-map.git
cd ntc-code-map
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE)
