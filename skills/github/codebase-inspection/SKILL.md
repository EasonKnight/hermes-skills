---
name: codebase-inspection
description: "Analyze codebases: LOC/language metrics (pygount) AND systematic bug hunting through code audit."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [LOC, Code Analysis, pygount, Codebase, Metrics, Repository, Auditing, Bug Hunting]
    related_skills: [github-repo-management, systematic-debugging]
prerequisites:
  commands: [pygount]
---

# Codebase Inspection

Two modes: **LOC metrics** (pygount) and **systematic bug hunting** (code audit).

Use LOC metrics when asked about code size, language breakdown, or file counts.
Use bug hunting when asked to "check for bugs", "review code quality", or "audit the codebase".

---

## When to Use

- User asks for LOC (lines of code) count
- User wants a language breakdown of a repo
- User asks about codebase size or composition
- User wants code-vs-comment ratios
- General "how big is this repo" questions

## Prerequisites

```bash
pip install --break-system-packages pygount 2>/dev/null || pip install pygount
```

## 1. Basic Summary (Most Common)

Get a full language breakdown with file counts, code lines, and comment lines:

```bash
cd /path/to/repo
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
  .
```

**IMPORTANT:** Always use `--folders-to-skip` to exclude dependency/build directories, otherwise pygount will crawl them and take a very long time or hang.

## 2. Common Folder Exclusions

Adjust based on the project type:

```bash
# Python projects
--folders-to-skip=".git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache"

# JavaScript/TypeScript projects
--folders-to-skip=".git,node_modules,dist,build,.next,.cache,.turbo,coverage"

# General catch-all
--folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party"
```

## 3. Filter by Specific Language

```bash
# Only count Python files
pygount --suffix=py --format=summary .

# Only count Python and YAML
pygount --suffix=py,yaml,yml --format=summary .
```

## 4. Detailed File-by-File Output

```bash
# Default format shows per-file breakdown
pygount --folders-to-skip=".git,node_modules,venv" .

# Sort by code lines (pipe through sort)
pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
```

## 5. Output Formats

```bash
# Summary table (default recommendation)
pygount --format=summary .

# JSON output for programmatic use
pygount --format=json .

# Pipe-friendly: Language, file count, code, docs, empty, string
pygount --format=summary . 2>/dev/null
```

## 6. Interpreting Results

The summary table columns:
- **Language** — detected programming language
- **Files** — number of files of that language
- **Code** — lines of actual code (executable/declarative)
- **Comment** — lines that are comments or documentation
- **%** — percentage of total

Special pseudo-languages:
- `__empty__` — empty files
- `__binary__` — binary files (images, compiled, etc.)
- `__generated__` — auto-generated files (detected heuristically)
- `__duplicate__` — files with identical content
- `__unknown__` — unrecognized file types

---

# Systematic Bug Hunting (Code Audit)

## When to Use

- User says "检查bug" / "check for bugs" / "code review"
- User asks to review a codebase for potential issues before they manifest
- Before a major refactor or deployment
- Periodic codebase health check

## Workflow

### Phase 1: Map the Codebase

```
1. List all files ────> wc -l, identify entry points, core modules
2. Read entry points ──> app.pyw, main.py, CLI entry, __main__
3. Read core modules ──> engine, data loader, config, utilities
4. Check duplicates ───> look for *_bak*, _* prefix copies, near-identical files
```

**Key questions per module:**
- What does this module do?
- What other modules import it?
- Is there a stale/unused copy? (check `_backtest_utils.py` vs `backtest_utils.py` etc.)

### Phase 2: Read Every Core File

For each core file, scan for these anti-patterns in order:

**A. Dead Code**
- Variables assigned but never read
- Loop iterations that compute values but discard them
- Tag/class assignments never used by the UI
- Functions never called anywhere

**B. Value Overwrite / Misleading Labels**
- A dict key set in one function, then overwritten in another
- Comments say one thing, code does another
- Label says "夏普比率" but value is actually "信息比率"

**C. Stale Duplicate Files**
- Two files with very similar names (one prefixed `_`)
- Different config values (BACKTEST_START, DATA_PATH, etc.)
- Different import paths — check which one is actually imported

**D. Duplicated Logic**
- Same function defined in two different files
- Same data loaded/downloaded multiple times in one run
- Same algorithm implemented in two places with subtle differences

**E. Cross-Module Inconsistency**
- `scan_strategies()` in module A filters differently than in module B
- Same function name, different behavior
- Config values computed differently (expanduser vs app_config)

**F. Data Flow Issues**
- NaN→bool conversion behavior (`np.nan.astype(bool)` → True!)
- Forward-fill vs backwards-fill assumptions
- Cache invalidation — does cache detect config changes?
- Data alignment — do arrays align by index or by position?

### Phase 3: Trace Critical Paths

For a quant backtest project, trace these critical paths:

```
Strategy file ──> generate_alpha/signal ──> BacktestEngine.run()
                                               │
                                    ┌──────────┼──────────┐
                                    v          v          v
                              _compute_stats  TradingRules  _compute_benchmark
                                                    │
                                                    v
                                              get_tradeable_mask()
```

**Check at each node:**
- Does the signal actually get filtered by frequency?
- Does the benchmark computation crash gracefully if data is missing?
- Does the max drawdown date get computed correctly?
- Does the position matrix save the right data?

### Phase 4: Edge Case Analysis

Per file, ask:
- What happens at t=0? t=1? t=N-1?
- What happens when a list/set is empty?
- What happens when a file doesn't exist?
- What happens with single-stock strategy?
- What happens during concurrent access?
- What happens with NaN, inf, negative values?

## Common Bug Categories in Quant Projects

| Category | Pattern | Example |
|----------|---------|---------|
| Stale duplicates | `_file.py` + `file.py` with different configs | `_backtest_utils.py` BACKTEST_START=2016 vs 2021 |
| Value overwrite | Dict key set, then overwritten by unrelated function | 夏普比率 → 信息比率 |
| Dead loop | Loop body computes but doesn't use result | `show_detail()` STAT_KEYS loop |
| Double call | Same I/O scheduled twice | `_update_data_status()` via two after() calls |
| Redundant import | Module-level + function-level duplicate | `import subprocess` |
| Duplicated logic | Same scan/load function in two files | `scan_strategies()` in app_utils + data_loader |
| Over-aggressive constraint | MIN_EFFECTIVE=20 on small portfolio locks rebalance | Strategy with 30 stocks needs 80% alive = deadlock |
| Float precision | Round-to-2 vs financial real-time | Price computation with floats vs Decimal |

## When to Create vs Fix vs Flag

| Severity | Action |
|----------|--------|
| 🟢 Cosmetic | Mention in report, no fix needed |
| 🟡 Medium | Fix if user asks, or flag for attention |
| 🔴 Critical | Fix immediately, explain why |
| ⚠️ Ambiguous | Present with tradeoffs, let user decide |

## Reference File

For quant backtest-specific debugging patterns (NAV anomalies, alpha_mode rebalancing bugs, limit up/down rules), see the `systematic-debugging` skill's reference:
- `references/quant-backtest-debugging.md`

---

## Pitfalls

1. **Always exclude .git, node_modules, venv** — without `--folders-to-skip`, pygount will crawl everything and may take minutes or hang on large dependency trees.
2. **Markdown shows 0 code lines** — pygount classifies all Markdown content as comments, not code. This is expected behavior.
3. **JSON files show low code counts** — pygount may count JSON lines conservatively. For accurate JSON line counts, use `wc -l` directly.
4. **Large monorepos** — for very large repos, consider using `--suffix` to target specific languages rather than scanning everything.
