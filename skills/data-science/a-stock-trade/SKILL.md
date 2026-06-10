---
name: a-stock-trade
category: data-science
description: A股量化交易平台 — 回测引擎、GUI桌面平台、数据管道、实盘管理。完整项目开发指南。
trigger: user asks about a_stock_trade project, app.pyw, backtest engine, stock data pipeline, quant GUI, desktop platform, A股回测, 量化桌面, or any task in ~/Desktop/a_stock_trade/
---

# A股量化交易平台 (a_stock_trade)

Complete project covering backtest engine, tkinter desktop GUI, data pipeline, and live trading management.

## Project Structure

```
a_stock_trade/
├── app.pyw                     # Main tkinter desktop app (~1309 lines)
├── core/
│   ├── backtest_utils.py       # DataLoader, BacktestEngine, Visualizer
│   ├── alpha_utils.py          # Factor function library
│   ├── runner.py               # Lightweight platform (auto-discover + CSV summary)
│   ├── app_config.py           # Color constants / path constants
│   ├── app_utils.py            # Strategy scanning, stats reading, label parsing
│   ├── app_live.py             # AppLiveMixin — live trading methods
│   ├── app_balance.py          # BalanceWindow — DeepSeek balance query
│   ├── data_loader.py          # NPZ loading / daily OHLC / fundamentals / calc_strat_positions
│   ├── update_data.py          # Incremental data update + NPZ cache build
│   ├── update_fundamentals.py  # Fundamental data download
│   └── update_data.bat         # Scheduled task batch entry
├── strategies/                 # Strategy source files (a*.py)
├── results/                    # Backtest results (per-strategy subfolders)
├── live/
│   └── strategies.json         # Live strategy configuration
├── data/                       # NPZ / CSV data files
└── bak/                        # Backups before refactoring
```

## Quick Start

```bash
cd ~/Desktop/a_stock_trade

# Batch run all strategies (single-process, data loaded once)
PYTHONIOENCODING=utf-8 python batch_run.py
PYTHONIOENCODING=utf-8 python batch_run.py --tags alpha

# Or via runner (subprocess mode, for debugging)
python -m core.runner run
python -m core.runner rank
python -m core.runner compare s76 s67

# Launch GUI
python app.pyw
```

## Key Design Rules

### Layout Modification Checklist (CRITICAL)
When removing any UI element (Frame/Text/Button), check ALL references:

```
□ 1. Creation code (widget + children + grid/pack)
□ 2. clear_detail references (delete/config)
□ 3. show_detail references (insert/config)
□ 4. Standalone methods that only serve the element
□ 5. Constructor/__init__ initializations
□ 6. All other method references (config/calls)
□ 7. row numbers — all downstream widgets must shift
□ 8. rowconfigure weights — must migrate to new row
□ 9. Grid container: tab.rowconfigure() vs self.rowconfigure() — use the RIGHT container
```

**Golden rule**: If the user says "only change X" — do ONLY X. Don't optimize adjacent code, don't remove "unused" methods, don't touch event handlers.

### File Modification Rules
- **Never use `re.sub`** to batch-delete Python code lines — surrounding indentations break
- **Never pipe `read_file` output to `write_file`** on same file — line number prefixes contaminate
- Use `patch` (old_string/new_string) for targeted edits
- Complex deletions: use Python line-by-line reading/writing
- Before any change, backup: `cp app.pyw bak/`

### Backtest Engine Configuration (core/backtest_utils.py)

| Variable | Default | Notes |
|----------|---------|-------|
| `MIN_COVERAGE` | `0.0` | Delete NPZ cache after changes |
| `BACKTEST_START` | `"2016-05-17"` | |
| `INIT_CAP` | `100_000_000` | Daily fixed trading amount |
| `COMMISSION` | `0.0003` | 0.03% |
| `SLIPPAGE` | `0.001` | 0.1% |
| `STAMP_DUTY` | `0.0005` | 0.05% stamp duty (sell only) |

### Subprocess Patterns
- **Hermes R&D**: `CREATE_NO_WINDOW + PIPE` → read stdout, display in dev_result
- **Run selected strategy**: `Popen([sys.executable, src], cwd=d, creationflags=CREATE_NEW_CONSOLE)` — NEVER `shell=True`
- **_on_close**: Must kill all three process categories (_live_procs, _sel_procs, _dev_proc)
- Every new `Popen` needs: init list + append on create + remove on finish + kill in _on_close

### Data Pipeline Rules
- A-share prefix whitelist: `{"000","001","002","003","300","301","302","303","600","601","603","605","688"}`
- Filter in BOTH `get_all_stocks()` AND `_build_cache()` — otherwise NPZ has 6691 stocks instead of ~5241
- NPZ rebuild runs in `update_data.py` after download (~35s); calls `drop_duplicates` to handle CSV dupes from force mode
- `update_data.bat` must end with `exit /b 0` for Task Scheduler
- **Safe flush pattern**: Write CSV first, THEN save progress — never the reverse (see `references/data-pipeline.md`)
- **Progress/error files**: All data scripts must clean progress+error files on completion or at start of next run — otherwise they grow unboundedly and poison subsequent runs
- **Cross-file audit**: When modifying any data script, check ALL of `update_data.py`, `download_data.py`, `update_fundamentals.py`, `data_loader.py` for the same patterns (safe flush, file cleanup, encoding consistency, log_fh try/finally) — see checklist in `references/data-pipeline.md`
- `platform.py` renamed to `runner.py` to avoid stdlib name collision

### Import/Thread Safety
- `importlib.util.spec_from_file_location` + `exec_module` is NOT thread-safe
- Live strategy runner: `max_workers = 1` — serial execution only
- matplotlib: `plt.close('all')` in every finally block (in-process mode)
- `calc_strat_positions` in `app.pyw` must delegate to `core/data_loader.calc_strat_positions`

### Stock Data Fundamentals
- Use `ak.stock_financial_abstract` (通用版), NOT `stock_financial_abstract_ths` (only covers ~50% A-shares)
- Field mapping differs: `销售毛利率`→`毛利率`, `营业总收入同比增长率`→`营业总收入增长率`, etc.
- `最新公告日期` is revision date, not first disclosure — use quarter-end + statutory delay
- Fundamental NPZ must use `(n_stocks, n_dates)` axis convention matching K-line NPZ

## GUI Color Scheme

Dark modern theme with constants in `core/app_config.py`. See `references/gui-conventions.md` for full color palette, font conventions (Noto Sans SC), DarkScrollbar implementation, and all UI patterns.

## Common Pitfalls

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| All stats show "—" | `read_stats` uses csv.reader instead of DictReader | Use DictReader |
| Strategy names show as filenames | `_parse_label` only reads first line | Read full file content |
| Chart doesn't display after layout change | rowconfigure weight on wrong row number | Fix rowconfigure after row shifts |
| Button stays gray on disable | tkinter overrides bg when state=disabled | Never set state=disabled; guard in callback |
| Click double-1 crashes on blank area | No guard for empty/total rows | identify_row → skip total → try/except |
| Live strategy stuck "⏳ 持仓计算中..." | CSV→NPZ migration missed app.pyw copy | Delegate to core.data_loader |
| `import platform` loads our file | `core/platform.py` shadows stdlib | Renamed to `core/runner.py` |
| Force update adds 0 rows | Force mode filter uses `> latest_for_stock` instead of `>= download_start` | Force mode: filter by `>= download_start`, not per-stock latest |
| Progress file poisons updates | `_clean_progress()` missing from early-exit paths | Add `_clean_progress()` on all 4 exit paths |
| Error/log files grow to GBs | Never cleaned between runs | Delete at start of each run (`os.remove` before work) |
| Crash loses data permanently | Progress saved before CSV flush | Safe flush: CSV first, progress second |

## References

- `references/gui-conventions.md` — Full tkinter GUI patterns: Treeview, color scheme, DarkScrollbar, DPI handling, startup optimization, real-time quotes
- `references/combined-positions.md` — Combined positions panel: pos_bar_lbls layout, signal.json format, proportional scaling, real-time updates
- `references/backtest-engine.md` — Engine internals: fixed-base backtest, forward-fill alpha, limit-up/down logic, position capping, cost accounting bugs
- `references/data-pipeline.md` — Data pipeline: A-share filtering, NPZ cache, progress files, scheduled tasks
- `references/fundamental-data-system.md` — Fundamental data: API selection, field mapping, disclosure date handling

## Combined Positions Panel (组合持仓)

The right column of the "实盘策略" tab shows the combined portfolio after proportional position scaling (等比缩仓).

### Bottom Bar Labels (`pos_bar_lbls` — 8 labels matching 8 POS_COLS)

| Index | Column | Content |
|-------|--------|---------|
| `[0]` | 股票代码 | `合计X只(N→X)` — stock count summary |
| `[1]` | 股票名称 | (empty) |
| `[2]` | 总手数 | total lots |
| `[3]` | 参考价 | average price per share |
| `[4]` | 总市值 | total market value |
| `[5]` | 涨跌幅 | **合计 +X.XX%** — weighted daily return rate |
| `[6]` | 涉及策略 | `分配 ¥XXX` — total allocation |
| `[7]` | 加权涨跌 | **收益 ¥+X,XXX** — daily profit amount (signed) |

Colors: red (#f85149) for gains, green (#56d364) for losses (international convention).

### signal.json Auto-Save

`_save_signal_json(adjusted=None)` method in `core/app_live.py` saves the combined positions (after proportional scaling) to `signal.json` in the project root. Format:

```json
[{"stock": "600000.SH", "volume": 300}, {"stock": "000001.SZ", "volume": 200}]
```

- `stock`: 6-digit code + exchange suffix (SH/SZ, determined by code prefix)
- `volume`: number of shares (lots × 100), NOT lots
- No positions → writes `[]`

**Save triggers**:
1. App startup → `self.after(1500, lambda: self._save_signal_json())`
2. After \"运行全部实盘\" → `refresh_combined_positions()` → `self._save_signal_json(adjusted)`
3. Any call to `refresh_combined_positions` (re-sort, manual refresh)

**Implementation pattern**: Method first checks `_pos_data` if no `adjusted` argument provided, writes empty array if no data available.
