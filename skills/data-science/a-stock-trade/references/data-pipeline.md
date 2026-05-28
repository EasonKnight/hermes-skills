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

## Scheduled Tasks (Windows)

- `core/update_data.bat` must end with `exit /b 0` — otherwise Task Scheduler reports exit code 2
- Batch files run via schtasks need absolute Python paths (`C:\Users\Mayn\AppData\Local\Programs\Python\Python311\python.exe`), not bare `python`
- Batch files with Chinese characters in echo statements corrupt when run via schtasks (UTF-8 vs GBK) — use ASCII-only English
- `chcp 65001 >nul` at top of batch file for Unicode in `%date%/%time%`

## stdlib Name Collision

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
