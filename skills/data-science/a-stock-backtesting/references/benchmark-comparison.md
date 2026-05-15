# Benchmark Comparison (CSI 1000 Index)

## Data Source

CSI 1000 (中证1000, index code `000852`) via akshare:

```python
import akshare as ak
df = ak.stock_zh_index_daily(symbol="sh000852")
# Columns: date, open, close, high, low, volume
```

The API returns data from ~2005 to present. For the 3-year backtest window (~726 trading days), download is ~0.2s.

## Alignment to Strategy Calendar

Stock and index trading calendars differ slightly (some half-day holidays, etc). Strategy dates come from the A-share K-line data which naturally follows the trading calendar.

```python
# Strategy dates: loader.dates  (ndarray of datetime64)
# Index dates:    df["date"]    (from akshare)

td = pd.to_datetime(loader.dates)
idx_df = df.set_index("date")
aligned = idx_df.reindex(td, method="ffill")     # forward-fill holidays
close_prices = aligned["close"].values
```

## Normalization

Both strategy NAV and benchmark NAV must start at 1.0 at the **same date** for excess NAV to be meaningful.

For mean reversion strategies, capital is not deployed on day 0 (no signal). The effective start is `first_nonzero` - the first day with a non-zero portfolio value.

```python
# In set_benchmark:
base = engine._first_nav_idx               # first non-zero portfolio day
aligned = aligned / aligned[base]           # benchmark normalized to base
excess_nav = engine.nav / aligned           # strategy / benchmark
```

## Statistics Computed

| Metric | Formula | Notes |
|--------|---------|-------|
| 基准收益 | `(aligned[-1] - 1) * 100%` | Total return of index |
| 超额收益 | `(excess_nav[-1] - 1) * 100%` | Cumulative excess return |
| 跟踪误差 | `std(excess_daily_ret) * sqrt(245)` | Annualized tracking error |
| 信息比率 | `ann_excess_ret / tracking_error` | Risk-adjusted alpha |

Where `excess_daily_ret[t] = strategy_ret[t] - benchmark_ret[t]` on days with non-zero strategy return.

## Comparison Dashboard

`Visualizer.plot_comparison()` uses a dark theme (`#0f172a` background) with:
- Color palette: `["#2563eb", "#dc2626", "#16a34a", "#f59e0b", "#8b5cf6", "#06b6d4"]`
- 12 metrics displayed in alternating-row table
- CSV export via `comparison.csv`

## Common Issues

1. **Index data not available**: No proxy issues with akshare's East Money API for index data (unlike stock K-line).
2. **Date mismatch at edges**: If index has fewer trading days than strategy (early/late holidays), ffill handles gaps but the very first/last day may differ. This is negligible for 700+ day windows.
3. **Dividend adjustment**: CSI 1000 is a total return index (price + reinvested dividends). Strategy uses raw close prices (adjustment depends on akshare's `qfq` flag). This creates a small structural alpha that favors the index in up markets.
