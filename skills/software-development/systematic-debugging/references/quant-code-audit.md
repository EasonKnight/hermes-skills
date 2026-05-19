# Quant Codebase Audit — Anti-Pattern Checklist

## When to Use

Full-project bug sweep: scan every module end-to-end, not just the file with a visible error. Common triggers: after major refactors, after batch strategy additions, or user request "检查bug".

## Audit Methodology

### 1. Map the Architecture

```
app.pyw          → GUI entry (tkinter)
core/            → Engine + utils
  backtest_utils.py   → DataLoader, BacktestEngine, TradingRules, Visualizer
  alpha_utils.py      → Factor functions, batch matrix ops
  app_utils.py        → Strategy scanning, stats parsing, live data IO
  app_live.py         → Live trading mixin (positions, realtime prices)
  app_config.py       → Color constants, path constants
  app_balance.py      → DeepSeek balance window
  data_loader.py      → Duplicate of some app_utils functions
  platform.py         → Subprocess-based batch runner (legacy)
  ui_helpers.py       → Button/label factories (unused?)
  theme.py            → Color theme (unused?)
  update_data.py      → Data download pipeline
  download_data.py    → Data download pipeline
  fetch_fundamentals.py / update_fundamentals.py → Financial data
strategies/      → Strategy files (100+)
batch_run.py     → Single-process batch runner (preferred)
run_all.py       → Delegates to batch_run or platform.run
live/            → JSON config for live trading
```

### 2. Read Every Root Module (not just the failing one)

Start with the files most likely to have bugs — largest files, frequently modified, or core engine:

1. `app.pyw` — GUI, button bindings, thread management
2. `core/backtest_utils.py` — Signal/alpha backtest engine, stats computation
3. `core/alpha_utils.py` — Factor implementations
4. `core/app_live.py` — Live trading, position aggregation
5. `batch_run.py`, `run_all.py` — Batch execution
6. `core/app_utils.py`, `core/data_loader.py` — Utility layer (check for duplication)

### 3. Anti-Patterns to Scan For

#### A. Stale/Duplicate Files
- **Check for `_`-prefixed files** like `_backtest_utils.py` that are near-duplicates of real modules with different configs (BACKTEST_START, DATA_PATH).
- **Check for duplicated functions** across modules — `scan_strategies` in both `app_utils.py` and `data_loader.py`, same function name but different filter logic.
- **Check for dead UI helpers** — `ui_helpers.py` and `theme.py` may exist alongside inline UI code in `app.pyw` that never imports them.

#### B. Dead Code
- **Computed-but-discarded variables** in long methods. Example: `show_detail()` iterates over `STAT_KEYS`, computes `tag` for each, but never uses it.
- **Unused imports** — especially in the main GUI file where imports accumulate.
- **Stale button/command references** after UI removal — check that removed widgets have their command functions and helper arrays cleaned up too.

#### C. Stats Overwriting
- **`_compute_benchmark()` overwrites `stats["夏普比率"]`** with Information Ratio (`set_benchmark()` does the same). The real Sharpe from `_compute_stats()` is lost.
- Check the dict keys: `_compute_stats` sets stats, then `_compute_benchmark` / `set_benchmark` modify them. Trace which keys get overwritten.

#### D. Edge Cases in Financial Calculations
- **Zero-price fallback**: `prev[prev == 0] = close[:, t][prev == 0]` — if `close[:, t]` is also 0, this produces inf/nan. Use `np.maximum(fallback, 0.01)` instead.
- **Low-volume distortion**: `amount_ratio` divides by `max(avg, 1)` — 1 is too high for stocks with tiny amounts. Use 0.01.
- **Limit price at t=0**: `for t in range(1, n_days)` skips t=0 in limit computation — first-day positions don't get limit-up checks.

#### E. Redundant I/O & Double Scheduling
- **Double `after()` calls**: `_update_data_status()` scheduled at 50ms AND 100ms during init.
- **Duplicate API calls**: `BacktestEngine.run()` downloads CSI1000 index, then `_compute_benchmark()` downloads it again. Check `_csi1000_idx_close` caching.

#### F. Architecture Mismatches
- **`run_all.py` → `platform.run()`** uses subprocess per strategy (slow on Windows). `batch_run.py` does single-process sequential (10-100x faster). Route to `batch_run.batch_run()`.
- **`platform.py`** with `ThreadPoolExecutor` + `subprocess.run` is legacy. Prefer `batch_run.py` for new callers.

#### G. String → Number Conversions in JSON
- `capital_pct` stored as string `"100000"` in JSON but loaded from file as same. Safe. But if manually edited as `100000` (no quotes), `float(s.get("capital_pct", "").strip())` would fail — wrap in try/except.

#### H. Zero-Division Protection Audit

**Always do this after any bug-sweep or before pushing major changes.**

Quant code is division-heavy. Unprotected zero-division causes silent NaN/inf propagation.

**Methodology for full audit:**

1. **Find ALL division operations:**
```bash
grep -rn '/ [a-zA-Z_]' core/*.py | grep -vE '#|http|///|/ n_|/ len|/ float|/ int|/ str|/ bool'
```

2. **Classify each into one of three protection patterns:**

| Protection Pattern | Example | Status |
|---|---|---|
| `np.maximum(denom, 1e-10)` | `close[:,t] / np.maximum(close[:,t-1], 1e-10)` | ✅ Safe |
| `np.where(guard, value, 0.0)` | `np.where(v > 0, r / v, 0.0)` | ⚠️ Division still evaluates! |
| `if var > 0: ... / var` | `if score_sum > 0: / score_sum` | ✅ Safe |

3. **⚠️ CRITICAL: `np.where(cond, a/b, 0)` STILL evaluates `a/b` for ALL elements!**
   - numpy evaluates both branches before masking
   - If `b` contains zeros anywhere, `a/b` produces inf/nan
   - The `np.where` only *selects* the result, it doesn't *guard* the computation
   - Safe pattern: `np.where(guard_mask, a / np.maximum(b, 1e-10), 0.0)` — guard INSIDE the division

4. **Common unprotected hotspots in quant code:**

| Pattern | File Example | Risk |
|---|---|---|
| `close[held, t] / close[held, t-1]` | benchmark return calc | Previous close = 0 for newly-traded stocks |
| `idx_close[1:] / idx_close[:-1]` | Index return calc | First index value could be 0 (ffill from no data) |
| `bm_nav[1:] / bm_nav[:-1]` | Benchmark nav return | After normalization, if base value is 0 |
| `np.abs(rets) / amt_win` | Amihud illiq | Should use pre-clamped `amt = np.maximum(close*volume, 1)` |
| `pv / pv[first_nonzero]` | NAV normalization | `first_nonzero` must be > 0 by construction — verify `np.argmax(pv > 0)` |

5. **Verify protection coverage after fix:**
```bash
# Count protected vs unprotected after changes
grep -rn '/ [a-zA-Z_]' core/*.py | grep -vE 'max|where|1e-|#|http|///|if |/ n_|/ len|/ var|/ val'
```
   - Result should be near-empty (only comments/docstrings)
   - Any remaining operational divisions need manual review

6. **Backtest engine specific (backtest_utils.py):**
- Lines 856, 939, 986 are historically unprotected — always check these three
- `_compute_benchmark()` method has the most exposure (multiple nav/price ratio calculations)
- `_csi1000_idx_close` cache check at line 1008 avoids duplicate downloads but doesn't guard div-by-zero

### 4. Verify Each Fix

```bash
# Syntax check all modified files
python -c "import py_compile; [py_compile.compile(f, doraise=True) for f in ['file1.py', 'file2.py']]"
```

### 5. File Cleanup Checklist

When removing a stale file:
- [ ] Verify no module imports it: `grep -r "import.*stale_file" core/ strategies/`
- [ ] Verify no batch_run or app.pyw references it
- [ ] Delete the file, not just its content

When removing a dead function:
- [ ] Search for all callers: `grep -rn "def function_name"` and `grep -rn "function_name("` 
- [ ] Only delete if zero callers (excluding the definition itself)
