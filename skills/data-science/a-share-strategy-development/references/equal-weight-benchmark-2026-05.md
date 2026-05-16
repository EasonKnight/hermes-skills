# Equal-Weight Weekly Benchmark (2026-05-16)

## Architecture (as of 2026-05-16)

**The benchmark is now computed automatically inside `BacktestEngine.run()`**
via `_compute_benchmark(close, dates)`. No external call needed.

### Code Location

`core/backtest_utils.py` → `BacktestEngine._compute_benchmark()`

### Old vs New Flow

```python
# ❌ OLD (removed from all 53 strategy files + platform.py)
idx_nav, idx_dates = IndexLoader.load(trade_dates=dates)
engine.run(...)
engine.set_benchmark(idx_nav, idx_dates)

# ✅ NEW (automatic, single call)
engine = BacktestEngine(...)
engine.run(close, signal, dates, trading_rules=rules, valid=valid)
# ^-- _compute_benchmark() fires at the end of run()
```

### Excess Calculation: Difference Method

```python
# OLD (ratio method)
self.excess_nav = self.nav / aligned       # nav/aligned - 1 = ratio-based excess
excess_ret = self.excess_nav[-1] - 1.0     # e.g. 2.4748/1.9653-1 = 25.92%
ann_excess = (1 + excess_ret) ** (1/y) - 1 # compounded

# NEW (difference method)
self.excess_nav = 1 + self.nav - aligned   # 1 + (nav-1) - (aligned-1)
excess_ret = self.nav[-1] - aligned[-1]    # e.g. 2.4748 - 1.9653 = 50.95pp
ann_excess = excess_ret / years            # simple annualized
```

### Why Difference over Ratio

- More intuitive: "strategy returned 50pp more than benchmark" vs "strategy returned 25.9% more than benchmark"  
- IR = ann_excess / tracking_error stays consistent because daily excess already uses subtraction
- The ratio method inflates small numbers and compresses large ones, misleading comparison

### Benchmark Algorithm

```
1. Load CSI1000 constituent list from data/csi1000_cons.csv (via load_csi1000_codes())
2. Filter close matrix: CSI1000 stocks AND close > 0.5
3. For each weekly-rebalance day t:
   a. Mark the first trading day of each week using weekly_filter(dates)
   b. On rebalance day: portfolio = filtered stocks
   c. Between rebalances: hold the same portfolio
   d. Daily portfolio return = equal-weighted mean of all held stock returns

NAV = cumprod(1 + daily_return)
```

### Stock Pool: CSI1000 Constituents

**Updated 2026-05-16**: Benchmark now filters to CSI1000 stocks only (matching the default pool used by most strategies).

Previously the benchmark used ALL stocks (close > 0.5 on the A-share market, ~2930 stocks), which gave +96.53% total return. This was inconsistent with strategies that filter to CSI1000 (~284 stocks).

The CSI1000 pool gives +93.97% total return over the same period — slightly lower because CSI1000 underperformed the broader market.

```python
# Filter applied inside _compute_benchmark()
csi_set = load_csi1000_codes()
csi_mask = np.array([str(c).strip()[:6] in csi_set for c in self.engine_codes], dtype=bool)
valid = valid & csi_mask[:, np.newaxis]  # close > 0.5 AND CSI1000
```

- If csi1000_cons.csv is missing, the benchmark falls back to all-stock pool
- The benchmark also computes CSI1000 price index excess (via akshare, for chart subplot 2)
- See `references/negative-cash-fix-2026-05.md` for the related bug fix

### Performance

For period 2021-05-17 ~ 2026-05-15 (1211 trading days, ~284 CSI1000 stocks):
- Total return: +93.97% (~14.2% annualized, CSI1000 pool)
- Computation time: ~0.2s (from .npz cache)

### CSI1000 Index Excess (Chart Subplot 2)

In addition to the main equal-weight benchmark, `_compute_benchmark()` also downloads the
CSI1000 price index (000852) via akshare for the chart's second subplot:

```python
try:
    import akshare as ak
    df = ak.stock_zh_index_daily(symbol="sh000852")
    # align to engine dates, normalize to first trade day
    self.csi1000_nav = csi_vals
    self.csi1000_excess_nav = 1 + self.nav - csi_vals
except Exception:
    self.csi1000_nav = None
    self.csi1000_excess_nav = None  # chart shows "数据不可用"
```

This is separate from the main equal-weight benchmark — it uses the actual CSI1000 price index.
The chart displays it in subplot 2 (orange line) with its own drawdown annotation.
If akshare fails (no network), the subplot shows "数据不可用" and is hidden.

### set_benchmark() — Still Exists for Manual Override

```python
engine.set_benchmark(custom_nav, custom_dates, benchmark_name="自定义")
```

Can override the auto-computed benchmark if a non-equal-weight comparison is needed.
Rarely used — the auto-computed equal-weight benchmark is the standard.

### Dependencies Removed

- `IndexLoader` class — no longer imported or used anywhere (kept as dead code in backtest_utils.py)
- `akshare` is still used for downloading CSI1000 price index (chart subplot 2), but no longer required for the main benchmark
