# Negative Cash Bug (Fixed-base Rebalancing)

## Bug Discovered: 2026-05-16

### Root Cause

In `BacktestEngine.run()`, the fixed-base rebalancing logic had three bugs:

**1. Rebalance allocation ignored actual portfolio value**

```python
# OLD (broken)
target_amt = self.fixed_base / n_effective  # Always allocates 100M
```

When a stock dropped and the strategy rebalanced, `net_pnl = cur_pos - new_pos` was negative → `has_cash` went negative → NAV could go below 0 → drawdown > 100%.

**2. Redeploy allocation also ignored actual cash**

Same issue in the `if not capital_deployed:` branch — used `self.fixed_base` directly.

**3. Trading cost not deducted in rebalance branch**

```python
# OLD (cost recorded but not subtracted)
cost = traded_sum * self.cost_rate
tc[t] = cost
pv[t] = has_cash + np.sum(new_pos)
```

Initial entry and no-signal branches correctly subtracted cost, but the rebalance branch didn't.

### Fix Applied

Three changes in `core/backtest_utils.py`:

```python
# 1. Rebalance: use available funds
available_total = max(has_cash + cur_mv, 0)
alloc_base = min(self.fixed_base, available_total)
target_amt = alloc_base / n_effective

# 2. Redeploy: use actual cash
alloc_base = min(self.fixed_base, available)
alloc = alloc_base / n_buy

# 3. Cost deduction
has_cash -= cost
```

### Before/After Comparison (for s18_consecutive_down)

| Metric | Before Fix | After Fix |
|--------|:----------:|:---------:|
| Total Return | -75.85% | -94.21% |
| Annualized | -15.34% | -19.06% |
| Max Drawdown | **-104.98%** | **-95.45%** |
| Negative NAV days | Yes | No |

The strategy returned MORE before the fix because:
1. Cost was not deducted in rebalance (returns overstated)
2. `has_cash` went negative, allowing leveraged-like buying

### Affected Strategies

All strategies with negative returns or high drawdowns were affected to some degree. The fix reduces returns and drawdowns for losing strategies (more realistic), and slightly improves IR for winning strategies (costs now correctly deducted).

### Verification

```python
# Check that NAV never goes negative
import pandas as pd
nav = pd.read_csv('results/<strategy>/nav.csv')
vals = nav.iloc[:, 1]  # second column = NAV values
assert (vals >= 0).all(), "Negative NAV detected!"
```

### Bug #4: `has_cash = 0.0` + `max_position_pct` cap → cash disappears (断崖式下跌)

**Discovered**: 2026-05-16, during S118 debugging

**Root Cause**: When redeploying from cash (`if not capital_deployed:`), `has_cash = 0.0` was set BEFORE the allocation computation. If `max_position_pct` (10% = 10M per stock) capped the per-stock amount below what `alloc_base` assumed, the excess cash was simply lost.

**Example with S118** (2024-03-04, sig=2 stocks):
```
has_cash_before = 130M
alloc_base = min(100M, 130M) = 100M
alloc_per_stock = 100M / 2 = 50M
max_position_pct → cap at 10M/stock
mv = 2 × 10M = 20M

# OLD (broken): has_cash was already set to 0.0
pv[t] = mv - cost = 20M - 26K ≈ 20M  # 110M vanished!

# FIX: keep remaining cash
has_cash = available - mv = 130M - 20M = 110M
pv[t] = has_cash + mv - cost = 130M - cost  # Correct!
```

**Impact**: Single-day NAV cliff drops of -84.70% (S118, 2024-03-04). Strategies with few signals (5-20 stocks) were most affected because `max_position_pct` limits each stock to 10M, so total deployment = min(100M, n_buy × 10M).

**Fix** (3 lines changed in `core/backtest_utils.py`):

```python
# 4a. Don't zero has_cash before computing allocation
# OLD: has_cash = 0.0
# FIX: just keep it, remaining cash = available - mv - cost

# 4b. After computing mv, save remaining cash AND cost permanently
has_cash = available - mv - cost  # was: has_cash = 0.0
pv[t] = has_cash + mv  # = available - cost; was: pv[t] = mv - cost
```

**Cost recovery note**: The cost MUST be subtracted from `has_cash`, not just from `pv[t]`. If cost is only in `pv[t]` (`pv[t] = mv - cost`), the next day `pv[t+1] = has_cash + cur_mv` recovers the cost because `has_cash` is still at the pre-cost level. This creates the **cost recovery effect** — the strategy appears to outperform the benchmark by the cost amount on every rebalance day.

### Bug #5: t=0 deployment indentation (shares/mv/cost outside `if n_buy > 0:`)

**Discovered**: 2026-05-16, during code audit

**Root Cause**: In the `t == 0` deployment section, lines setting `shares[:, t]`, `mv`, `cost`, `tc[t]`, `pv[t]`, and `capital_deployed` were OUTSIDE the `if n_buy > 0:` block, meaning they always executed even when no stocks could be bought (using stale `target` variable from the previous iteration or uninitialized).

**Fix**: Moved shares/mv/cost/pv/turnover/capital_deployed inside the `if n_buy > 0:` block (extra indentation level).

### Bug #6: Cost recovery effect (cost not embedded in has_cash)

**Discovered**: 2026-05-16, during s02 equal-weight excess debugging

**Root Cause**: Cost was deducted from `pv[t]` but `has_cash` remained at the pre-cost value. On day t+1, `pv[t+1] = has_cash + cur_mv` used the full pre-cost cash, so the cost "recovered" — the strategy appeared to gain back the cost on the next day as excess performance.

**Example** (s02 equal-weight, 284 stocks):
```python
Day 0: has_cash = 100M → buy 100M stocks, pay 130K cost
  has_cash = 100M - 100M = 0    # Correct: cash spent
  pv[0] = 0 + 100M - 130K = 99.87M  # Cost deducted, 净值 ≈ 0.9987

Day 1: stocks up 0.67%
  cur_mv = 100.67M
  pv[1] = has_cash + cur_mv = 0 + 100.67M = 100.67M  # 净值 ≈ 1.0067

# ⚠️ 净值从 0.9987 → 1.0067 = +0.80% return
# 但股票只涨了 0.67%！多出的 0.13% 是成本回收！
```

**Fix**: Subtract cost from `has_cash`, not just from `pv[t]`:
```python
# OLD: has_cash = available - mv (cost only in pv, recovers next day)
has_cash = available - mv
pv[t] = has_cash + mv - cost  # cost in pv but not in has_cash

# NEW: has_cash = available - mv - cost (cost embedded, never recovers)
has_cash = available - mv - cost
pv[t] = has_cash + mv  # = available - cost ✓
```

### Bug #7: Excess NAV uses fixed-base returns vs benchmark percentage returns

**Discovered**: 2026-05-16, during s02 equal-weight excess debugging

**Root Cause**: `excess_nav = 1 + nav - bm_nav` where `nav` uses fixed-base returns (`(pv-chg)/100M`) and `bm_nav` uses percentage returns (`cumprod(1+avg_stock_ret)`). When pv > 100M, fixed-base returns are amplified relative to percentage returns, making the strategy appear to outperform the benchmark.

**Example** (s02 at pv=114M on 2024-09-13):
```python
# Strategy: pv 114M → 113M (-0.94% of current value)
daily_ret = (113M - 114M) / 100M = -0.94%  # fixed-base (-0.83% of 114M)

# Benchmark: average stock return = -1.01%
excess = -0.94% - (-1.01%) = +0.07%  # Strategy "outperformed"!

# Reality: both hold same stocks, strategy lost 0.94% of base,
# benchmark lost 1.01% of current value — the fixed base (100M)
# vs current value (114M) mismatch creates the illusion.
```

**Affects**: All strategies with nav > 1.0 (i.e., all profitable strategies). s02 equal-weight showed 702/1211 days with excess > 0 and 7.5% max positive excess — all spurious.

**Fix**: Compute excess using percentage returns for both strategy and benchmark:
```python
# In _compute_benchmark():
# Strategy percentage returns
pct_ret = np.zeros(N_days)
for t in range(base_idx + 1, N_days):
    if self.pv[t-1] > 0:
        pct_ret[t] = self.pv[t] / self.pv[t-1] - 1
strat_pct_nav = np.cumprod(1 + pct_ret)
strat_pct_nav = strat_pct_nav / strat_pct_nav[base_idx]

# Excess using percentage NAV
self.excess_nav = 1 + strat_pct_nav - bm_nav  # not 1 + self.nav - bm_nav

# Also fix stats: excess_ret = self.excess_nav[-1] - 1.0
```

**Verification**: After fix, s02 equal-weight excess consistently ≤ 1.0 on cost-free days (small positive excess persists from daily rebalancing vs benchmark's weekly hold, which is a real strategy effect not a calculation bug).

### Updated Full Fix Locations (core/backtest_utils.py, BacktestEngine.run())

| Bug | Lines | Change |
|-----|-------|--------|
| 1. Rebalance allocation | ~620+ | `alloc_base = min(fixed_base, available_total)` |
| 2. Redeploy allocation | ~580+ | `alloc_base = min(fixed_base, available)` |
| 3. Cost deduction | ~660+ | `has_cash -= cost` |
| 4a. has_cash zeroing | ~577 | Removed `has_cash = 0.0` |
| 4b+c. Cost in has_cash | ~598 | `has_cash = available - mv - cost; pv[t] = has_cash + mv` |
| 5. t=0 indentation | ~540 | Moved inside `if n_buy > 0:` |
| 6. Cost recovery | ~598 | Same as 4b+c — cost embedded in has_cash |
| 7. Excess NAV methodology | ~761 (in _compute_benchmark) | Use `strat_pct_nav` not `self.nav` |

