---
name: a-stock-backtest-framework
description: "A-share backtesting framework at ~/Desktop/a_stock_trade/. Signal-matrix driven engine, individual strategy files, comprehensive trading rules."
version: 2.0.0
author: Hermes Agent
tags: [backtest, a-share, trading, strategy, quantitative]
related_skills: [cn-stock-data]
---

# A-Stock Backtest Framework

The A-share backtesting framework at `~/Desktop/a_stock_trade/`.

## Architecture

```
a_stock_trade/
├── backtest_utils.py           ← Shared: DataLoader, BacktestEngine, TradingRules, Visualizer
├── s01_*.py ~ s10_*.py        ← 10 core strategies (equal weight / momentum / mean reversion / RSI / vol)
├── s11_*.py ~ s30_*.py        ← 20 extended strategies (MA cross / Bollinger / consecutive / Sharpe / price)
├── s31_new_high_strategy.py   ← Stateful trailing-stop strategy
├── s31_tune.py                 ← Parameter sweep for S31
├── run_all.py                  ← Run all strategies, generate comparison
├── download_data.py            ← Re-download data via akshare
├── data/
│   ├── a_stock_kline_3y.csv    ← Raw CSV (~960MB, 2016-2026)
│   └── a_stock_kline_3y.npz   ← Binary cache (~80MB, 0.5s load)
├── results/                    ← Auto-generated per-strategy folders
└── git_sync.bat                ← Windows Task Scheduler script
```

## BacktestEngine (signal-driven)

### Signal Matrix Pattern

Each strategy provides `generate_signal(close, dates, **kw)` returning `bool[N_stocks, N_days]`:
- `signal[stock, t] = True` → stock should be in portfolio on day t
- Engine handles: buy new signals, sell dropped signals, rebalance held stocks to equal weight

### Fixed-Base Returns (no compounding)

- `INIT_CAP = ¥100,000,000` (default, configurable)
- Daily return = (PV[t] - PV[t-1]) / fixed_base  — simple interest, not compound
- Annualized = total_ret / years  — simple, not CAGR
- Prevents the "compounding distortion" where long-running strategies show absurd percentages
- Set `fixed_base=None` to revert to traditional compound NAV

### Position Cap (10% max per stock)

- `max_position_pct = 0.10` (configurable)
- When a position exceeds 10% of total portfolio, excess is automatically sold to cash
- **Pitfall (FIXED):** Original implementation double-counted capping costs AND had cash misaligned from pv[t]. Final fix: capping adds gross excess to `has_cash`, unified cost via `traded_sum`, pv[t] recomputed as `has_cash + sum(positions)`.

### MIN_EFFECTIVE Protection

- `MIN_EFFECTIVE = max(20, n_sig * 0.1)` — if too few stocks are actually tradeable (blocked by limits/halts/new-stock rules), skip rebalance and keep current holdings
- Prevents concentration amplification (the S09 RSI bug): when n_effective is tiny, the per-stock target becomes enormous, creating a feedback loop with the position cap

### Costs

- `cost_rate = commission (0.03%) + slippage (0.1%) = 0.13%` per traded yuan
- Applied uniformly to both buy and sell sides via `traded_sum * cost_rate`

## TradingRules Class

```python
rules = TradingRules(close, open_price, volume, codes, names_arr, is_st, exchange)
```

Constructor computes all masks upfront (~O(N_stocks × N_days) each):

| Mask | Logic |
|------|-------|
| `limit_pct` | Per-stock: main=10%, chinet=20%, star=20%, st=5% |
| `limit_up/down` | `close == round(prev * (1±pct), 2)` — exact match to fen (分) |
| `suspended` | `volume == 0` |
| `newly_listed` | First non-zero close NOT on day 0 → blocked for 22 trading days |
| `limit_up_hit` | Can't buy at limit up |
| `limit_down_hit` | Can't sell at limit down |

### get_tradeable_mask(t, in_portfolio)

Returns `(can_buy, can_sell)` boolean arrays for day t:
- `can_buy = ~suspended & ~limit_up & ~newly_listed`
- `can_sell = ~suspended & ~limit_down & ~newly_listed`

### Pitfall: New Stock Detection (FIXED)

Original code flagged ALL stocks as "newly listed" if they had a non-zero close on day 0 — which is every stock that existed before the dataset's start. Fix: skip day-0-first-appearance stocks (they're not new), only flag stocks whose first non-zero appears after the dataset starts.

## DataLoader

- First run: loads CSV (961MB) → pivot close/open/volume → filter min_coverage → ffill → save `.npz`
- Subsequent runs: loads `.npz` in ~0.5s
- Fields cached: `close`, `open_price`, `volume`, `codes`, `dates`, `names_arr`, `is_st`, `exchange`
- **Pitfall (FIXED):** `self.names_arr` must be set in BOTH cache-path AND CSV-path. Originally only set in cache-path, causing AttributeError on first run.

### ST / Exchange Detection

- ST stocks: name contains "ST", "*ST", "退", "PT"
- Exchange: code prefix → "main" (10%), "star" (688, 20%), "chinet" (300, 20%)

## Adding a New Strategy

1. Create `sNN_name.py` with:
   - `generate_signal(close, dates, **kw)` returning bool matrix
   - `main()` that loads data, generates signal, runs engine, saves results
2. Add to `run_all.py`'s `STRATEGIES` list
3. Run `python sNN_name.py` individually or `python run_all.py` for full comparison

### Stateful Strategies (e.g., trailing stop)

For strategies that need per-stock state tracking (like S31's "buy at new high, sell at 10% drawdown"), the signal matrix can still express the logic — iterate stock-by-stock with a state machine, set signal=True/False per day. The engine sees only the final bool matrix.

## Key Findings (A-share 2016-2026, ¥100M fixed base)

```
 1. S27 涨幅TOP10%      +632.80%  超额夏普 1.51  ← 极致动量
 2. S21 超跌5日周频     +365.69%  超额夏普 1.16  ← 超跌反弹
 3. S25 低价股日频      +318.48%  超额夏普 1.39  ← 小市值效应
...
10. S07 低波周频        +154.08%  超额夏普 0.64  ← 风险调整最优
...
30. S15 布林带下轨      -98.98%  超额夏普 -0.02  ← 抄底毁灭
```

### Lessons
- **Momentum dominates** in A-shares (buy winners works, buy losers loses)
- **Daily frequency beats weekly** for momentum (S06 +227% vs S05 -30%)
- **Low volatility** outperforms high volatility (S07 +154% vs S08 -48%)
- **RSI oversold** without minimum signal floor creates concentration explosion (FIXED: add min_signal_count guard)
- **Bollinger band lower** buys falling knives in bear markets (worst performer)

## Excess Sharpe Ratio

All Sharpe ratios reported as **excess Sharpe** = (annualized excess return) / (tracking error), set in `set_benchmark()` by overriding the `"夏普比率"` stat key:
```python
self.stats["夏普比率"] = f"{ir:.2f}"  # ir = information ratio = excess / tracking_error
```
