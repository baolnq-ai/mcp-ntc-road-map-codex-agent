# AGENTS.md

<!-- ntc-code-map:start -->
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
<!-- ntc-code-map:end -->

