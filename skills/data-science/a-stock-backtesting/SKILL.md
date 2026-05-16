---
name: a-stock-backtesting
title: A-Share Stock Strategy Backtesting
description: Vectorized backtesting of A-share stock strategies — signal generation, portfolio simulation, cost accounting, trading rules (limit up/down, suspension, new stocks), position capping, fixed-base return, and result visualization on large price matrices (5000+ stocks × 700+ days)
trigger: user asks to backtest, backtest,回测, run strategy on A-share data, evaluate trading strategy
tags: [finance, stocks, a-share, backtesting, quantitative, numpy, pandas]
---

> ⚠️ **已合并到 `a-share-strategy-development`**。该技能包含最新项目结构（`core/` + `strategies/` 子目录）、完整的 import 路径（`from core.backtest_utils import ...`）、30 策略全量排名、固定基准分配（无 has_cash 双重计数）、涨跌停双向拦截、暗色主题图表。本技能保留旧版参考，实际开发请用 `a-share-strategy-development`。

## Data Prerequisites

Relies on a CSV with columns `股票代码,股票名称,date,close[,open,high,low,volume]`.
Typical size: 5000 stocks × 726 days ≈ 3.7M rows, ~400MB CSV.

## Architecture: Shared Module + Signal Matrix

Each strategy produces a **signal matrix** (`bool[N_stocks, N_days]`) where `signal[stock, t]=True` means the stock belongs in the equal-weight portfolio at close of day `t`. The shared engine handles all rebalancing, cost, and P&L logic.

```
backtest_utils.py  → DataLoader, BacktestEngine, TradingRules, Visualizer, IndexLoader
s01_*.py           → just generate_signal() + main() — saves to results/S01-.../
s02_*.py
...
run_all.py         → imports all s*.py, runs all, compares
```

### Signal Contract

```python
signal[stock, t] = True  → stock is in equal-weight portfolio at close of day t

Engine behavior:
  True→False: sell the stock
  False→True: buy the stock
  True→True: hold and rebalance to equal weight
  All False on day 0: capital stays as cash until first signal day
  All False on later day: clear all positions to cash; next signal redeploys
```

### File-Per-Strategy Pattern

Each strategy is an independent `.py` file with its own `main()`, saving to its own results folder:

```
results/
├── S01-等权日频/    (equity_curve.png, nav.csv, daily.csv, stats.csv)
├── S02-等权周频/
└── ...
```

`run_all.py` dynamically imports `generate_signal` from each file:

```python
STRATEGIES = [
    ("S01 等权日频", __import__("s01_equal_weight_daily",
                               fromlist=["generate_signal"]).generate_signal, {}),
    ...
]
```

## NPZ Caching (60× Speedup)

Cache the cleaned matrix as `.npz` for ~0.15s loads instead of ~10s CSV parse:

```python
self.cache_path = os.path.splitext(csv_path)[0] + ".npz"

# Fast path
data = np.load(self.cache_path, allow_pickle=True)  # allow_pickle for string arrays
self.close = data["close"]          # float64 (N_stocks, N_days)
self.open_price = data["open"]
self.volume = data["volume"]
self.codes = data["codes"]           # object (stock codes)
self.dates = data["dates"]
self.names = pd.Series(data["names"], index=pd.Index(self.codes, name="股票代码"))
self.is_st = data["is_st"]           # bool
self.exchange = data["exchange"]     # str (main/chinet/star)

# Slow path: CSV → pivot → clean → cache
np.savez_compressed(self.cache_path,
                    close=self.close, open=self.open_price, volume=self.volume,
                    codes=self.codes, dates=self.dates, names=names_filtered.values,
                    is_st=self.is_st, exchange=self.exchange)
```

**Key**: `allow_pickle=True` required for string arrays. Delete `.npz` to force regeneration after CSV refresh. Add to `.gitignore`.

## Weekly Signal Filtering

```python
from pandas import to_datetime
dt = to_datetime(dates)
weeks = dt.isocalendar().year.astype(str) + "-W" + dt.isocalendar().week.astype(str)
first_of_week = np.ones(len(dt), dtype=bool)
first_of_week[1:] = weeks[1:].values != weeks[:-1].values
signal[:, ~first_of_week] = False
```

For weekly-hold strategies, forward-fill through non-Monday days:
```python
for t in range(1, n_days):
    if not first_of_week[t]:
        signal[:, t] = signal[:, t-1]
```

## Trading Rules (涨跌停 / 停牌 / ST / 新股)

The `TradingRules` class enforces realistic trading constraints. Pass to `engine.run()`:

```python
rules = TradingRules(close, open_price, volume, codes,
                     names_arr, is_st, exchange)
engine.run(close, signal, dates, trading_rules=rules)
```

### Price Limits by Board

| Board | Code Prefix | Limit |
|-------|------------|-------|
| 主板 | 600/601/603/605/000/001/002 | 10% |
| 创业板 | 300 | 20% |
| 科创板 | 688 | 20% |
| ST/*ST | any (name contains ST/退/PT) | 5% |

Detection: `names.str.contains("ST|退|PT", na=False)`

### Limit Hit Detection — 0.5% Tolerance Required (float32 Precision Fix 2026-05-15)

```python
limit_up   = round(prev_close * (1 + limit_pct), 2)
limit_down = round(prev_close * (1 - limit_pct), 2)
# Must use tolerance — see explanation below
is_limit_up   = (close[t] >= limit_up * 0.995) & ~suspended
is_limit_down = (close[t] <= limit_down * 1.005) & ~suspended
```

**CRITICAL (2026-05-15 fix)**: Do NOT use exact `==`. The `close` array is float32 (loaded from CSV with `dtype="float32"`) while `limit_up`/`limit_down` are float64 (from `np.round(prev * 1.10, 2)`). Exact `==` comparison between float32 and float64 fails due to precision — e.g. `float32(14.26) → 14.260000228881836`, which never equals `float64(14.26)`. This caused **~99% of limit-up cases to be missed** (2,529 vs 109,553 over the full dataset). Use `>= limit_up * 0.995` for limit-up and `<= limit_down * 1.005` for limit-down.

**Impact of this fix**: All momentum/buy-the-top strategies that were buying limit-up stocks had inflated IRs that collapsed after the fix (S27 went from IR 1.11 to nan). Robust strategies (low-price, low-vol, equal-weight) were unaffected.

See `a-share-strategy-development` references/limit-tolerance-fix-2026-05.md for full reproduction and verification scripts.

### Suspension Detection

```python
self.suspended = (volume == 0)  # zero trading volume = no transactions
```

Held stocks that become suspended stay in portfolio (forced hold).

### Newly Listed Stock Filter

Exclude stocks for 22 trading days (~1 month) after IPO listing:

```python
for i in range(n_stocks):
    first = np.argmax(close[i, :] > 0)
    if first == 0 and close[i, 0] > 0:
        continue  # already trading before data start — NOT new
    end = min(first + 22, n_days)
    newly_listed[i, first:end] = True
```

Only stocks whose first data point appears AFTER the dataset's start date are treated as newly listed. Without this check, ALL stocks that were trading before the data range (which is almost all of them) get incorrectly blocked for the first 22 days.

### get_tradeable_mask

```python
def get_tradeable_mask(self, t, in_portfolio):
    can_buy  = ~suspended & ~limit_up & ~newly_listed
    can_sell = ~suspended & ~limit_down & ~newly_listed
    return can_buy, can_sell
```

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Signal=True, not held, limit-up | Don't buy |
| Signal=True, held, limit-up | Hold current (can't add) |
| Signal=False, held, limit-down | Forced hold (can't sell) |
| Signal=False, held, suspended | Forced hold |
| Signal=True, not held, suspended | Don't buy |
| Newly listed (first 22 days) | Can't buy or sell |
| All signals blocked on deploy | Capital stays as cash |

## Effective Signal Logic (Normal Rebalance)

When trading constraints block some trades, recalculate the achievable target. **This is the most bug-prone part of the engine — handle carefully:**

```python
effective_sig = signal.copy()
effective_sig[~held & ~can_buy] = False       # new entries blocked
forced_hold = held & ~can_sell & ~signal
effective_sig[forced_hold] = True              # forced hold

n_effective = effective_sig.sum()

# PROTECTION: too few effective stocks → don't rebalance
MIN_EFFECTIVE = max(20, int(n_sig * 0.1))
if n_effective < MIN_EFFECTIVE:
    achievable = shares[:, t-1].copy()  # stay put — prevents blowup
```

Without this protection, when many stocks are blocked (e.g., limit-up on a strong day), `n_effective` becomes tiny, `target_amt = total / tiny_number` concentrates the entire portfolio into a handful of stocks, causing extreme daily returns and eventual blowup.

## Position Size Cap (Individual Stock Limit)

Limit each stock to a maximum percentage of total portfolio (`default: 10%`):

```python
def __init__(self, ..., max_position_pct=0.10):
    self.max_position_pct = max_position_pct

# During rebalance:
if self.max_position_pct < 1.0:
    pos_val = achievable * close[:, t]
    max_val_arr = np.full(n_stocks, total * self.max_position_pct)
    over = pos_val > max_val_arr
    if over.any():
        excess_val = np.sum(pos_val[over] - max_val_arr[over])
        achievable[over] = max_val_arr[over] / close[:, t][over]
        has_cash += excess_val  # excess → cash (cost handled by traded_sum)
```

**Bug to avoid**: Do NOT subtract cost from excess_val here (`has_cash += excess_val - cost_excess`). The `traded_sum` computed afterward already includes the capping trades, so subtracting cost here would double-count it.

## Fixed-Base Return (Prevent Compounding)

Instead of compounding returns (which can give misleadingly large numbers over long periods), use a fixed base:

```python
def __init__(self, ..., fixed_base=INIT_CAP):
    self.fixed_base = fixed_base  # None = traditional compounding

# Return computation:
if fixed_base is not None:
    daily_ret[t] = (pv[t] - pv[t-1]) / fixed_base   # simple interest
    nav = 1.0 + (pv - pv[base_idx]) / fixed_base
    ann_ret = total_ret / years                      # simple annualization
else:
    daily_ret[t] = pv[t] / pv[t-1] - 1.0             # compounding
    nav = pv / pv[base_idx]
    ann_ret = (1 + total_ret) ** (1/years) - 1
```

This ensures returns are always relative to the initial capital, preventing compound amplification over long time series.

## Cost Accounting

| Cost | Formula | Typical |
|------|---------|---------|
| Commission | traded_amount × 0.0003 | 万三 per side |
| Slippage | traded_amount × 0.001 | 0.1% per side |
| **Total** | traded × (0.0003 + 0.001) | 0.13% per side |

`traded = buy_amount + sell_amount` (both sides combined). Using `max(buy, sell)` under-estimates costs by ~2×.

### Common Pitfalls

1. **Cost double-counting from position capping**: When capping generates sales, the `traded_sum` already includes those sales. Do NOT add a separate `cost_excess` to `tc[t]` — it will be overwritten by `tc[t] = cost` and causes the cost to be deducted from both `has_cash` and `pv[t]`. Let the unified `traded_sum × cost_rate` handle everything.

2. **pv[t] must reflect cash from capping**: After capping adds `excess_val` to `has_cash`, set `pv[t] = has_cash + sum(new_pos)`. The old pattern `pv[t] = total - cost` doesn't include the new cash, causing portfolio value to diverge from actual holdings.

## Strategy Signal Generation Techniques

### Full 10-Strategy Results (2016-2026, ¥100M fixed base)

*Only S01-S10 were backtested. S11-S36 (composite indicators, Bollinger, N-day high/low, etc.) have code written but results not yet generated. See `run_all.py` to batch-execute.*

| Rank | ID | Strategy | Total Return | Ann. Return | Sharpe | Max DD | Info Ratio |
|------|----|----------|-------------|-------------|--------|--------|-----------|
| 1 | S06 | 动量日频 | +239.78% | 24.22% | 0.73 | -50.12% | 0.62 |
| 2 | S07 | 低波周频 | +154.01% | 15.55% | 0.64 | -41.34% | 0.61 |
| 3 | S02 | 等权周频 | +134.49% | 13.58% | 0.49 | -48.86% | 0.72 |
| 4 | S01 | 等权日频 | +134.16% | 13.55% | 0.49 | -48.88% | 0.72 |
| 5 | S03 | 均值回归周频 | +11.80% | 1.19% | 0.14 | -35.81% | 0.01 |
| 6 | S04 | 均值回归日频 | +3.18% | 0.32% | 0.02 | -61.03% | -0.05 |
| 7 | S05 | 动量周频 | -29.45% | -2.97% | -0.21 | -64.60% | -0.34 |
| 8 | S08 | 高波周频 | -48.05% | -4.85% | -0.34 | -75.80% | -0.58 |
| 9 | S10 | RSI超买周频 | -80.79% | -8.16% | -0.72 | -87.10% | -0.95 |
| 10 | S09 | RSI超卖周频 | +24677%* | — | 0.91 | -82.37% | 0.03 |

*\*S09 RSI oversold returns are spurious due to concentration blowup (see "RSI Oversold safety" below).*

#### Composite & Stateful Strategies (Design Patterns)

Signal generators that combine multiple conditions for more selective entries (code exists as `s31_*.py` ~ `s36_*.py`, not yet backtested):

```python
# S32: Uptrend pullback — MA5>MA10>MA20 + price near MA20 + up today
ma5 = _ma(close, 5); ma10 = _ma(close, 10); ma20 = _ma(close, 20)
uptrend = (ma5 > ma10) & (ma10 > ma20)
near_ma20 = np.abs(close / ma20 - 1.0) < 0.02
ret = ...; up_today = ret > 0
signal = uptrend & near_ma20 & up_today

# S33: Volatility squeeze — 10d vol < 20d vol×0.7 + 5d high
vol10 = _vol(close, 10); vol20 = _vol(close, 20)
squeeze = (vol10 < vol20 * 0.7) & (vol20 > 0)

# S34: Bull flag — 5d gain>3% + 2d consolidation (<2% pullback) + up today
up5 = (close[:, t] / close[:, t-4] - 1.0) > 0.03
max_pullback = np.maximum(np.abs(ret_d1), np.abs(ret_d2))
flag = (max_pullback < 0.02)
signal = up5 & flag & up_today

# S35: Double bottom bounce — N-day low + hold M days
for s in np.where(at_low)[0]:
    signal[s, t:t+hold_days] = True
```

#### Stateful Per-Stock Strategies (S31)

For strategies needing position-level state tracking (e.g., "buy at 60-day high, sell at 10% drawdown from peak"), iterate stock-by-stock with a state machine:

```python
for s in range(n_stocks):
    in_pos = False; peak = 0.0
    for t in range(n_days):
        if not in_pos:
            if t >= lookback and prices[t] >= np.nanmax(window):
                signal[s, t] = True; in_pos = True; peak = prices[t]
        else:
            signal[s, t] = True
            peak = max(peak, prices[t])
            if prices[t] <= peak * (1 - stop_loss):
                signal[s, t] = False; in_pos = False
```

The engine sees only the final bool matrix — any state machine logic hidden inside `generate_signal()` works transparently.

### Parameter Tuning Methodology

For strategies with knobs (lookback, hold_days, threshold %), run a grid search to find the excess-Sharpe-maximizing combination:

```python
for lb in [5, 10, 15, 20, 30]:
    for hd in [3, 5, 8, 10, 15]:
        signal = generate_signal(close, dates, lookback=lb, hold_days=hd)
        e = BacktestEngine(...)
        e.run(close, signal, dates, trading_rules=rules)
        e.set_benchmark(idx_nav, idx_dates)
        sharpe = float(e.stats["夏普比率"])
        results.append((sharpe, lb, hd, ...))
results.sort(key=lambda x: -x[0])
```

S35 tuning example (N-day low × hold days):

```
Best: L5H15 → excess Sharpe 0.71, ann 15.4%, dd -48.5%
  2nd: L5H10 → excess Sharpe 0.68, ann 17.4%, dd -47.7%
  3rd: L5H8  → excess Sharpe 0.67, ann 21.0%, dd -47.6%
```

Pattern: shorter lookback (L=5) = more signals + smoother equity curve; longer hold (H=15) = bounce fully materialized. Longer lookbacks (L=20+) create rare signals → concentration blowups (-90%+ DD).

### Basic: Level & Return Filters

### Momentum (Percentile-Based)

```python
ret[:, 1:] = close[:, 1:] / close[:, :-1] - 1.0
for t in range(1, close.shape[1]):
    r = ret[:, t]
    thr = np.nanpercentile(r[r != 0], 80)  # top 20%
    signal[:, t] = (r >= thr) & (close[:, t] > 0.5)
```

Use `np.nanpercentile` and filter zeros — stale-price stocks at 0.0 distort the threshold.

### RSI Oversold — CRITICAL Safety Note

RSI < 30 strategies produce extreme and deceptive returns. Root cause:

```
1. RSI < 30 fires rarely → only 5-50 stocks per week have signal
2. Position cap (10%) limits each to 10% → only ~50% deployed
3. Remaining 50% sits in cash
4. Oversold bounces on the few held stocks are large (10-20%+)
5. Growth triggers cap → sold to cash → cash grows → next rebalance
   deploys MORE cash (because total grew)
6. Over 2426 trading days this feedback loop produces astronomical returns
```

The return is technically real (the strategy picks good bounces) but the 82% max drawdown means one wrong week wipes it out. S09 implementation fixes: threshold RSI < 25 (not 30) + minimum 80 stocks per signal week (skip weeks with fewer). Without `MIN_EFFECTIVE` guard in the engine (see above), same feedback loop can affect any strategy with very few effective signals.

### Full Signal Catalog by Technique

*Note: S11-S36 strategies below exist as code (`s11_*.py` ~ `s36_*.py`) but have NOT been backtested yet. The signal code examples are proven design patterns ready for `generate_signal()` use.*

#### Level & Return Filters (S25, S26, S27, S28)

```python
# Price percentile (low-price / high-price)
for t in range(close.shape[1]):
    c = close[:, t]; valid = c > 0.5
    thr = np.nanpercentile(c[valid], 20)
    signal[:, t] = (c <= thr) & valid

# Return percentile (top/bottom 10%)
for t in range(1, close.shape[1]):
    r = ret[:, t]; valid = (r != 0) & (close[:, t] > 0.5)
    thr = np.nanpercentile(r[valid], 90)
    signal[:, t] = (r >= thr) & valid

# Consecutive up/down (S17, S18)
up = ret > 0
for t in range(3, close.shape[1]):
    signal[:, t] = up[:, t-2] & up[:, t-1] & up[:, t]

# Acceleration/deceleration (S29, S30)
for t in range(2, close.shape[1]):
    signal[:, t] = (ret[:, t] > ret[:, t-1]) & (ret[:, t] > 0)  # accelerate
```

#### Moving Averages (S11-S14)

```python
def _ma(close, w):
    ma = np.zeros_like(close)
    for t in range(w-1, close.shape[1]):
        ma[:, t] = np.nanmean(close[:, t-w+1:t+1], axis=1)
    return ma

ma5, ma10, ma20 = _ma(close,5), _ma(close,10), _ma(close,20)
signal = (ma5 > ma10) & (ma10 > ma20)  # bullish alignment
signal = (ma5 < ma10) & (ma10 < ma20)  # bearish alignment
signal = (ma5 > ma20)                   # golden cross
signal = (ma5 < ma20)                   # death cross
```

#### Bollinger Bands (S15, S16)

```python
def _bollinger(close, w=20, k=2.0):
    lower, upper = np.zeros_like(close), np.zeros_like(close)
    for t in range(w-1, close.shape[1]):
        m = np.nanmean(close[:, t-w+1:t+1], axis=1)
        s = np.nanstd(close[:, t-w+1:t+1], axis=1)
        lower[:, t] = m - k*s; upper[:, t] = m + k*s
    return lower, upper

lower, upper = _bollinger(close, 20, 2.0)
signal = close < lower    # S15 — oversold (loses -99%)
signal = close > upper    # S16 — momentum (+228%)
```

#### N-day High/Low (S19, S20)

```python
for t in range(20, close.shape[1]):
    high20 = np.nanmax(close[:, t-19:t+1], axis=1)
    signal[:, t] = (close[:, t] == high20)  # S19 — new high (+281%)
    low20 = np.nanmin(close[:, t-19:t+1], axis=1)
    signal[:, t] = (close[:, t] == low20)   # S20 — new low (+244%)
```

#### Multi-day Return (S21, S22)

```python
ret5 = close[:, t] / close[:, t-5] - 1.0
signal = (ret5 < -0.12)   # S21 — 5d drop >12% (+366%)
signal = (ret5 > 0.12)    # S22 — 5d rise >12% (-96%)
```

#### 60-day Sharpe Ratio (S23, S24)

```python
for t in range(60, close.shape[1]):
    chunk = close[:, t-59:t+1]
    ret60 = chunk[:, 1:] / chunk[:, :-1] - 1.0
    sharpe = np.nanmean(ret60, axis=1) / (np.nanstd(ret60, axis=1) + 1e-8)
    thr = np.nanpercentile(sharpe, 20)  # bottom 20% = low sharpe (reverse)
    signal[:, t] = (sharpe <= thr)
```

### RSI (Relative Strength Index)

```python
def _rsi(close, w=14):
    rsi = np.zeros_like(close)
    ret = np.zeros_like(close)
    with np.errstate(divide="ignore", invalid="ignore"):
        ret[:, 1:] = np.where(close[:, :-1] > 0, close[:, 1:] / close[:, :-1] - 1.0, 0.0)
    for t in range(w, close.shape[1]):
        c = ret[:, t-w+1:t+1]
        gain = np.where(c > 0, c, 0); loss = np.where(c < 0, -c, 0)
        avg_gain = np.nanmean(gain, axis=1); avg_loss = np.nanmean(loss, axis=1)
        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss > 0)
        rsi[:, t] = 100 - 100 / (1 + rs)
    return rsi
```

### Volatility (Rolling Standard Deviation)

```python
for t in range(window, close.shape[1]):
    vol[:, t] = np.nanstd(ret[:, t-window+1:t+1], axis=1)
```

## Benchmark Comparison (CSI 1000)

Download via akshare, align to strategy dates:

```python
idx_nav, idx_dates = IndexLoader.load(trade_dates=loader.dates)
engine.run(close, signal, loader.dates)
engine.set_benchmark(idx_nav, idx_dates)
# Stats added: 基准收益, 超额收益, 跟踪误差, 信息比率
```

Alignment: `reindex(..., method="ffill")`, normalize to 1.0 at strategy's first non-zero day. Excess NAV = strategy NAV / benchmark NAV.

## Visualization

### 4-Panel Chart (with benchmark)

1. NAV overlay: strategy + benchmark + excess
2. Drawdown: strategy vs benchmark
3. Excess return curve
4. Holdings count

### Chinese Font (Windows)

```python
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei',
                                           'Noto Sans SC', 'KaiTi']
matplotlib.rcParams['axes.unicode_minus'] = False
```

### Multi-Strategy Comparison

Dark-theme chart (`#0f172a` / `#1e293b`) overlaying all strategy NAVs, drawdowns, metrics table (right panel), and return-vs-risk scatter (bottom-right).

## Windows Scheduled Task (替代 Hermes Cron)

```bat
schtasks /create /tn "【家中】repo-name git同步 每日" ^
         /tr "cmd /c C:\path\to\git_sync.bat" ^
         /sc daily /st 21:00 /f
```

Use Python `subprocess.run()` to create tasks if MSYS bash mangles the quoting:
```python
import subprocess
subprocess.run(["schtasks", "/create", "/tn", "任务名",
                "/tr", "cmd /c C:\\path\\to\\script.bat",
                "/sc", "daily", "/st", "21:00", "/f"])
```

## Known Bugs Fixed (Historical Record)

| Bug | Symptom | Fix |
|-----|---------|-----|
| NaN propagation | `0 × NaN = NaN` poisons all portfolio values | `fillna(0.0)` in DataLoader |
| Old cache missing fields | `AttributeError: no attribute 'open_price'` | Delete `.npz`, regenerate with new fields |
| names_arr not saved in cache | `Length of values (5198) != Length of index (4952)` | `names_filtered = names.reindex(codes)` before save |
| New stock detection wrong | 80%+ stocks blocked as "newly listed" | Skip stocks with first price at index 0 |
| Cost double-count from capping | tc[t] overwritten by `tc[t] = cost` after `tc[t] += cost_excess` | Remove separate cost_excess, let traded_sum handle all |
| pv[t] stale after capping | Portfolio value diverges from actual holdings | `pv[t] = has_cash + sum(new_pos)` after capping |
| Limit tolerance too wide | 1.5% tolerance flagged 8.5% stocks as limit-up | Exact `==` match only |

## Pitfalls

### 1. NaN propagation: `0 × NaN = NaN`

Even after `np.where(valid, value, 0)`, if `close` contains NaN, `0.0 × NaN = NaN` poisons sums. Fix: clean at DataFrame level before `.values`.

### 2. First-day deploy when day 0 has no signal

Track `capital_deployed` flag and `has_cash` balance. Wait for first signal day, then deploy from cash.

### 3. Clear/re-deploy cash cycle with `capital_deployed` flag

After clearing on a non-signal day, save cash in `has_cash`. On re-deploy, use `has_cash`, NOT `initial_capital` (which would reset P&L).

**Critical sub-case**: If your BacktestEngine tracks a `capital_deployed` flag to skip initial deploy on subsequent days, it MUST be reset to `False` when all positions are cleared to cash. Without this reset:

```python
# Day 5: signal fires → capital_deployed = True
# Day 6-9: no signals → clear positions, has_cash = total
#   BUG: capital_deployed stays True
# Day 10: signal fires again
#   capital_deployed=True → skip deploy from has_cash
#   "total" at this point may not include has_cash
#   → target_amt = 0 for all stocks → all-zero portfolio
```

Fix: in the clear-to-cash path, always set `capital_deployed = False`.

```python
if n_sig == 0:
    has_cash = total = (positions * close[:, t]).sum()
    positions[:] = 0
    pv[t] = has_cash
    capital_deployed = False  # ← MUST reset
    continue
```

This is especially important for **weekly strategies** where signal gaps of 2-5 days are common, and the first signal may not appear until day 5+ (e.g. first Monday of data range).

### 4. RSI oversold / small-signal strategy blowup

S09 (RSI < 30) produced 24677% over 10 years. Root cause: rare signal → few effective stocks → `n_effective` tiny → `target_amt = total / tiny` concentrates portfolio → cap fires repeatedly → cash accumulates → next day the larger cash-inflated total makes the cap higher → feedback loop. The 82% max drawdown shows the enormous risk. **Do not use in production without position-level stop-losses.**

**Two-layer fix**: (1) Tighten threshold to RSI < 25 and require minimum 80 stocks per signal week; (2) Engine-level `MIN_EFFECTIVE = max(20, n_sig * 0.1)` guard prevents rebalancing when too few stocks are available. After the fix, S09 returned a modest -6% over 10 years.

### 5. Caching: `.npz` requires `allow_pickle=True`

Because codes/names are string arrays (object dtype), `np.load()` defaults to `allow_pickle=False` and raises `ValueError: Object arrays cannot be loaded when allow_pickle=False`.

## Output Structure

```
a_stock_trade/
├── backtest_utils.py
├── s01_equal_weight_daily.py  ...  s10_rsi_overbought_weekly.py
├── s11_ma_golden_cross.py     ...  s30_momentum_deceleration.py
├── run_all.py                 ← imports all s*.py dynamically
├── data/
│   ├── a_stock_kline_3y.csv
│   └── a_stock_kline_3y.npz       ← auto-generated cache
└── results/
    ├── S01-等权日频/
    ├── S02-等权周频/
    ├── ...
    └── 30策略对比/              ← run_all.py output
```

## References

- `references/debug-nan-propagation.md` — NaN pitfall reproduction
- `references/weekly-signal-filtering.md` — daily-to-weekly conversion
- `references/signal-matrix-framework.md` — shared module architecture
- `references/benchmark-comparison.md` — CSI 1000 integration
- `references/strategy-rankings-2026.md` — latest 10-strategy rankings
