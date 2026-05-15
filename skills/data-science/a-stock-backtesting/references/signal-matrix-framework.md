# Signal-Matrix Backtesting Framework

## File Structure (Consolidated)

```
a_stock_trade/                      ← main project folder (git repo)
├── backtest_utils.py              ← Shared: DataLoader, BacktestEngine, Visualizer, weekly_filter, IndexLoader
├── strategy_mean_reversion.py     ← Signal: stocks that fell prev day (± weekly filter)
├── strategy_equal_weight.py       ← Signal: all stocks, every day (± weekly filter)
├── compare.py                     ← One-click multi-strategy runner
├── data/
│   └── a_stock_kline_3y.csv       ← ~400MB, kept outside git
└── results/                       ← auto-saved backtest outputs
    ├── 等权日频/
    ├── 均值回归周频/
    └── 策略对比/

## Shared Module (`backtest_utils.py`)

### DataLoader

```python
class DataLoader:
    def __init__(self, csv_path="~/Desktop/a_stock_data/a_stock_kline_3y.csv",
                 min_coverage=0.9): ...

    def load(self):
        # pivot → (N_stocks, N_days) close matrix
        # dropna(thresh=min_coverage) → remove sparse stocks
        # ffill(axis=1) → forward-fill suspended days
        # fillna(0.0) → remove residual NaN (NEW stocks)
        self.close      # ndarray float64
        self.codes      # stock code array
        self.dates      # datetime64 array
        self.names      # stock name Series
```

### BacktestEngine - Signal-Driven

```python
class BacktestEngine:
    def __init__(self, commission=0.0003, slippage=0.001,
                 initial_capital=1_000_000): ...

    def run(self, close, signal, dates, valid=None):
        """..."""

    def set_benchmark(self, benchmark_nav, benchmark_dates,
                      benchmark_name="中证1000"):
        """Attach CSI 1000 index, compute excess return stats."""

    # Output attributes:
    #   self.pv, self.daily_ret, self.nav, self.turnover
    #   self.trade_cost, self.n_sig, self.stats
    #   self._first_nav_idx       (for benchmark alignment)
    # After set_benchmark():
    #   self.benchmark_nav, self.excess_nav, self.benchmark_name
    # Stats added: 基准收益, 超额收益, 跟踪误差, 信息比率

### BacktestEngine Key Logic (the per-day loop)
### BacktestEngine Key Logic (the per-day loop)

```python
capital_deployed = False
has_cash = initial_capital

for t in range(n_days):
    sig_t = signal[:, t] & valid[:, t]
    n_sig_t = sig_t.sum()

    if t == 0:
        pv[t] = has_cash
        if n_sig_t > 0:
            alloc = has_cash / n_sig_t
            shares[:, t] = alloc / close[:, t]  # (masked & finite-checked)
            mv = sum(shares * close)
            cost = mv * cost_rate
            has_cash = 0
            pv[t] = mv - cost
            capital_deployed = True
        continue

    # t >= 1
    cur_mv = sum(shares[:, t-1] * close[:, t])
    total = has_cash + cur_mv
    pv[t] = total

    if n_sig_t == 0:
        # Clear to cash
        cost = cur_mv * cost_rate
        has_cash += cur_mv - cost
        shares[:, t] = 0
        capital_deployed = False
        pv[t] = has_cash
        continue

    if not capital_deployed:
        # Deploy from cash
        available = has_cash; has_cash = 0
        alloc = available / n_sig_t
        shares[:, t] = alloc / close[:, t]  # (masked)
        mv = sum(shares * close)
        cost = mv * cost_rate
        pv[t] = mv - cost
        capital_deployed = True
        continue

    # Normal rebalance (has_cash == 0)
    target_amt = total / n_sig_t
    target = np.where(sig_t, target_amt / close[:, t], 0.0)
    # ... finite & positive checks ...
    diff = target * close[:, t] - shares[:, t-1] * close[:, t]
    traded = np.sum(np.abs(diff))
    cost = traded * cost_rate
    pv[t] -= cost
    shares[:, t] = target
```

### Visualizer

```python
Visualizer.plot_and_save(engine, output_dir, title)     # 4-panel with benchmark, auto-saves CSV
Visualizer.print_trades(engine, n_top=10)                # recent trade log
Visualizer.plot_comparison(engines, labels, dir, title)  # multi-strategy dashboard
Visualizer.show_chart(filepath)                          # open image on Windows
```

Note: `RESULTS_BASE = os.path.expanduser("~/Desktop/a_stock_trade/results")` is defined in `backtest_utils.py`.
Strategy outputs auto-save to `os.path.join(RESULTS_BASE, folder)`.

## Strategy File Pattern

Each strategy file is a standalone script using RESULTS_BASE for output:

```python
import os
from backtest_utils import (
    DataLoader, BacktestEngine, Visualizer,
    IndexLoader, RESULTS_BASE, weekly_filter, print_stats,
    COMMISSION, SLIPPAGE,
)

def generate_signal(close, dates=None, **kwargs):
    """Return (N_stocks, N_days) bool array."""
    ...

if __name__ == "__main__":
    loader = DataLoader().load()
    idx_nav, idx_dates = IndexLoader.load(trade_dates=loader.dates)
    signal = generate_signal(loader.close, loader.dates)
    engine = BacktestEngine().run(loader.close, signal, loader.dates)
    engine.set_benchmark(idx_nav, idx_dates)
    print_stats(engine.stats)
    Visualizer.print_trades(engine)
    folder = "策略名"  # e.g. "等权日频"
    Visualizer.plot_and_save(engine, os.path.join(RESULTS_BASE, folder), "标签")
    Visualizer.show_chart(os.path.join(RESULTS_BASE, folder, "equity_curve.png"))
```

## Weekly Filter Utility

```python
def weekly_filter(dates):
    """Returns bool array: True on first trading day of each ISO week."""
    dt = pd.to_datetime(dates)
    iso = dt.isocalendar()
    week_id = iso["year"].astype(str) + "-W" + iso["week"].astype(str)
    first = np.ones(len(dt), dtype=bool)
    first[1:] = week_id[1:].values != week_id[:-1].values
    return first
```

## Cost Model

- **Commission**: 0.03% (万三) per side
- **Slippage**: 0.1% per side
- **Cost rate**: 0.0013 per unit traded (both sides combined)
- Cost applies to ALL traded amount: `cost = (buy_amount + sell_amount) * cost_rate`
- For daily rebalance of 5000 stocks at 0.85% turnover: ~0.13% daily cost drag

## Signal Contract Cheat Sheet

| Strategy | Signal Characteristics | Engine Behavior |
|----------|----------------------|-----------------|
| Daily mean reversion | signal flickers daily per stock | Buy today, sell tomorrow |
| Weekly mean reversion | signal only on Mondays | Buy Monday, clear Tue-Fri |
| Equal-weight daily | all stocks, every day True | Daily rebalance to equal weight |
| Equal-weight weekly | all stocks True on Mondays, copy prev day otherwise | Rebalance Mon, hold rest of week |
