# Using ntc-code-map with Codex

## Automatic Setup

```bash
# Install the package
pip install ntc-code-map

# Auto-configure Codex to use ntc-code-map as an MCP server
ntc-code-map init-codex

# Inject the recommended workflow into your project's AGENTS.md
ntc-code-map init-agents
```

## What `init-codex` does

Adds an MCP server block to your Codex `config.toml`:

```toml
[mcp_servers.ntc_code_map]
command = "/path/to/ntc-code-map"
args = ["serve"]
```

## What `init-agents` does

Injects a workflow section into `AGENTS.md` that instructs Codex to:

1. Check `index_status` before reading source files
2. Rebuild with `index_repo` if stale
3. Call `repo_map(task, token_budget)` for context
4. Use `find_symbols` / `find_files` for focused follow-up
5. Use Serena symbolic tools for exact navigation

## Manual Setup

If you prefer manual configuration:

### 1. Add to Codex config.toml

Find your Codex config file (usually `~/.codex/config.toml`) and add:

```toml
[mcp_servers.ntc_code_map]
command = "ntc-code-map"
args = ["serve"]
```

### 2. Add AGENTS.md instructions

Add this to your project's `AGENTS.md`:

```markdown
## NTC Code Map workflow

Before reading source files or using broad shell search:
1. Call `ntc_code_map.index_status`.
2. If missing/stale, call `ntc_code_map.index_repo`.
3. Call `ntc_code_map.repo_map(task, token_budget=3500)`.
4. Use `ntc_code_map.find_symbols` or `find_files` for focused follow-up.
5. Then use Serena symbolic tools for exact navigation.
```

## Verifying

```bash
# Check dependencies
ntc-code-map doctor

# Test indexing
cd your-project
ntc-code-map index
ntc-code-map status
ntc-code-map repo-map "test task"
```
