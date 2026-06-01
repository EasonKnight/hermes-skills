# Data Pipeline for a_stock_trade

## A-Share Code Filtering

All A-share data downloads must filter to these prefixes:

```python
A_PREFIXES = {"000","001","002","003","300","301","302","303",
              "600","601","603","605","688"}
```

Apply in BOTH `get_all_stocks()` AND `_build_cache()`. Without filtering: NPZ has 6,691 stocks (includes B-shares/bonds/funds). With filtering: ~5,241 A-shares.

## NPZ Cache

`core/update_data.py:_build_cache()` rebuilds NPZ from CSV after download:

```python
np.savez_compressed(CACHE_NPZ,
    close=close, open=open_, volume=volume,
    high=high, low=low,
    codes=codes, dates=dates,
    names=names_arr, is_st=is_st, exchange=exchange)
```

Structure matches `DataLoader._load_data()` output. ~35s build time for 5,241×2,427 matrix.

## Progress File Traps

`_update_progress.txt` tracks each stock's last update date. If you manually delete CSV data, must also delete progress file:

```bash
rm data/_update_progress.txt   # Delete first
python core/update_data.py     # Then re-run
```

Otherwise update skips all "completed" stocks → 0 new rows.

## Safe Flush Pattern (CRITICAL)

**Golden rule**: Write data to CSV FIRST, then record progress SECOND. Never the reverse.

If progress is saved before CSV flush and the program crashes in between:
- Progress file says "done" → stock skipped on resume
- Data never reached CSV → permanently lost

Correct pattern (used in `update_data.py`):
```python
# Step 1: Write to CSV
df_out.to_csv(OUTPUT_CSV, mode="a", ...)
# Step 2: Only after successful write, record progress
save_batch_progress(done_buffer)
```

Wrong pattern (fixed in `download_data.py` 2026-06-01):
```python
# BUG: progress saved before CSV flush
save_progress(code, name, status, len(data))  # ← done first
buffer.extend(data)  # ← data still in memory, not on disk
```

## Data Pipeline Files — Cross-File Consistency Checklist

When adding a new data file or modifying data pipeline behavior, audit ALL of these:

| File | Pattern to Check |
|------|-----------------|
| `update_data.py` | `_clean_progress()` on all exits; error file cleaned at start; `log_fh` in try/finally; CSV encoding `utf-8-sig` both read and write; force mode filter `>= download_start` |
| `download_data.py` | Progress saved AFTER CSV flush (not before); progress+error files cleaned on completion; `log_fh` in try/finally; stock prefix filtering consistent with update_data.py |
| `update_fundamentals.py` | Error file cleaned at start; `_build_cache` calls `drop_duplicates` before pivoting; `load_existing_codes` handles incremental skip |
| `data_loader.py` | `load_stock_name_map` has NPZ→JSON→CSV fallback; `_build_stock_map_from_csv` exists as CSV fallback |

**Common trap patterns** found 2026-06-01 across all 3 update scripts:
1. Progress/error files appended to but NEVER deleted → infinite growth + stale state
2. File handles (`log_fh`) opened without try/finally → leak on exception
3. CSV written with `utf-8-sig` but read with plain `utf-8` → encoding drift
4. NPZ cache built without `drop_duplicates` → force-re-download creates duplicates in cache

## Scheduled Tasks (Windows)

`core/platform.py` shadows stdlib `platform` module. When akshare/pandas calls `import platform`, it loads the project file → `AttributeError: module 'platform' has no attribute 'python_implementation'`.

**Fix**: Renamed to `core/runner.py`. Update all references: `app.pyw` (CLI commands), `batch_run.py`, `run_all.py`. Remove `sys.path.pop(0)` workarounds from `download_data.py`, `update_data.py`, `fetch_fundamentals.py`, `update_fundamentals.py`.

## NPZ→CSV Fallback Principle

Every data-loading point must: NPZ first (fast) → CSV fallback (slow but always works):

| Load Point | Function | Fallback Chain |
|------------|----------|----------------|
| Backtest data | `DataLoader.load()` | NPZ → CSV → auto-rebuild NPZ |
| Stock name map | `load_stock_name_map()` | NPZ → JSON cache → CSV (via `_build_stock_map_from_csv`) |
| Status bar | `_update_data_status()` | NPZ → CSV |
| Fundamental expansion | `expand_to_daily()` | K-line NPZ → K-line CSV |
| Fundamental loading | `load_fundamentals()` | NPZ → None (caller handles) |

## Stock Code Leading Zeros

NPZ cache strips leading zeros (code "19" = 000019). Every display path must restore with `code.zfill(6)`:
- `calc_strat_positions()`
- `refresh_combined_positions()`
- `refresh_live_strat_detail()`

## Quantity Units

- Backtest/position matrix: 手 (1手 = 100股)
- Broker export (table.xls): 股 (1股 = 1 unit)
- Do NOT mix units — converts incorrectly.

## Broker Export Format

Broker-exported `table.xls` is NOT Excel — it's GBK-encoded Tab-separated text:
```python
pd.read_csv("table.xls", sep="\t", encoding="gbk")
```
