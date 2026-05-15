---
name: a-stock-backtest-framework
description: "A-share backtesting framework at ~/Desktop/a_stock_trade/. Signal-matrix driven engine, individual strategy files, comprehensive trading rules."
version: 1.0.0
author: Hermes Agent
tags: [backtest, a-share, trading, strategy]
---

# A-Stock Backtest Framework

The A-share backtesting framework at `~/Desktop/a_stock_trade/`.

## Architecture

- **`backtest_utils.py`** — shared module: DataLoader (.npz cache), BacktestEngine (signal-driven), TradingRules, Visualizer, IndexLoader (CSI 1000)
- **Individual strategy files** — e.g. `s06_momentum_daily.py`. Each has `generate_signal(close, dates)` returning bool matrix + `main()` that runs and saves.
- **`run_all.py`** — runs all strategies, generates comparison chart + summary CSV.
- **`download_data.py`** — re-downloads A-share data via akshare.

## Data Pipeline

- Source: akshare OHLCV CSV → `data/a_stock_kline_3y.csv` (961MB, ~10 years 2016-2026)
- Cache: first load generates `data/a_stock_kline_3y.npz` (binary, ~80MB, loads in 0.5s)
- After cleaning: ~2930 stocks, ~2426 trading days

## Trading Rules (TradingRules class)

| Rule | Implementation |
|------|---------------|
| Price limits | Main board 10%, ChiNext 20%, STAR 20%, ST 5% |
| Limit up/down | `close == round(prev * (1±pct), 2)` exact match |
| Suspension | `volume == 0` |
| New stocks | Blocked for 22 trading days after first appearance |
| Position cap | Max 10% per stock (configurable) |

## BacktestEngine

- **Signal matrix**: `signal[stock, t] = True` → hold this stock on day t
- **Returns**: Fixed-base (¥100M default), daily P&L / base, no compounding
- **Annualized**: Simple interest (total_ret / years), not CAGR
- **Costs**: 0.03% commission + 0.1% slippage per traded yuan
- **Position limit**: 10% cap, excess automatically converted to cash
- **Protection**: `MIN_EFFECTIVE = max(20, n_sig*0.1)` — skip rebalance when too few stocks are tradeable

## Strategy File Template

```python
def generate_signal(close, dates=None, **kw):
    # return bool matrix (N_stocks, N_days)
    signal = ...
    return signal

def main():
    # Load data, run, save results
    ...
```

Results auto-save to `results/<folder>/` with equity_curve.png + nav.csv + stats.csv.

## Key Findings (A-share 2016-2026)

- **Momentum wins**: Top 10% daily gainers (S27) +633%; 60-day new high breakout (S19) +281%
- **Mean reversion loses**: Bollinger lower band (S15) -99%; Bottom 10% daily return (S28) -97%
- **Oversold bounce works**: 5-day drop >12% weekly (S21) +366%
- **Equal weight is solid**: +134% with 0.57 Sharpe
- **Low volatility beats high volatility**: S07 +154% vs S08 -48%
- **Daily frequency beats weekly for momentum**: S06 +227% vs S05 -30%
