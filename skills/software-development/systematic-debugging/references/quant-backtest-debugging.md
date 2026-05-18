# Debugging Quant Backtest Anomalies

For the `a_stock_trade` project specifically. Use alongside `systematic-debugging` SKILL.md phases.

## Workflow: Abnormal NAV → Root Cause

### 1. Check the Pattern

Read `nav.csv` and `daily.csv`. Look for these red flags:

| Pattern | Likely Cause |
|---------|-------------|
| Huge spike in first month (e.g. +128% in 10 days), then flatline | alpha_mode daily rebalancing bypassing frequency filter |
| NAV oscillates wildly (±5-15% daily) after a fix | `excess_val` + `net_pnl` double-counting; or signal-unchanged check too strict |
| NAV climbs steadily with 0% turnover but position values unchanged | Position matrix not tracking price changes; fix entered but shares copy working |
| NAV diverges from benchmark by implausible amount | Look-ahead bias or missing trading cost in one path |

### 2. Compare w_ret vs daily_return

Run this diagnostic:
```python
pos = load_positions('results/S108-*/position_matrix.npz')
held = pos[:, t] > 0
w_ret = np.sum(pos[held, t] * close[held, t] / close[held, t-1] - 1) / pos[held, t].sum()
csv_ret = daily.iloc[t].daily_return
# If they differ significantly → PV engine issue
```

### 3. Check Position Matrix for Stale Data

```python
np.allclose(pos[:, 2:11].sum(axis=0), pos[:, 2].sum())
# True → positions not tracking daily price changes
```

### 4. Verify Shares Carry-Forward

After a fix that should carry forward shares on non-rebalance days:
```python
stock_idx = np.where(ld.codes == '300459')[0][0]
print(f"shares[4]={eng.shares[s,4]:.4f}")
print(f"shares[5]={eng.shares[s,5]:.4f}")
print(f"copy of day4? {eng.shares[s,5] == eng.shares[s,4]}")
```
If `copy of day4? False`, the fix is NOT being entered.

### 4b. Check Expected vs Actual pos_value

```python
shares_d4 = eng.shares[s, 4]
for t in range(5, 10):
    exp = shares_d4 * close[s, t]
    act = pv[s, t]
    print(f"  Day {t}: expected={exp:.0f} actual={act:.0f} diff={act-exp:.0f}")
```
If `diff != 0`, the shares are changing OR the signal-unchanged check needs fixing.

## Root Causes Found in Debugging Sessions

### Bug: `excess_val` + `net_pnl` Double-Counting (May 2026)

**Symptom:** Even after fixing alpha_mode daily rebalancing, monthly/weekly strategies still showed +11-14% daily returns on non-rebalance days. Position values were constant despite changing stock prices.

**Root cause:** In the "正常再平衡" section, two separate code paths both add cash from the `max_position_pct` cap:

1. **Line 815:** `has_cash += excess_val` — adds the cap-released cash directly
2. **Lines 822-823:** `net_pnl = sum(cur_pos) - sum(new_pos)` THEN `has_cash += net_pnl` — net_pnl also accounts for the cap because `sum(new_pos)` is AFTER capping (smaller than alloc_base)

The excess is counted TWICE: once via `excess_val` (+15M) and once via `net_pnl` (+7M instead of -8M). This inflates PV by the full excess amount on every rebalance day.

**Fix:** Remove `has_cash += excess_val` at line 815. The cap effect is fully handled by `net_pnl` because `sum(new_pos)` reflects the capped positions.

**Trace:** Stock 1920 (300459):
- Day 4 close=5.22 → shares=1,915,708, pos=10M (capped)
- Day 5 close=5.01 → expected pos=9.6M, but actual=10M (shares recalculated by engine)
- After fix: pos=9.6M (correct mark-to-market) ✓

**Verification diff=0 check:**
```python
# Key indicator that fix is working
Day 5: expected=9597702 actual=9597702 diff=0
Day 6: expected=9501916 actual=9501916 diff=0
```

### Bug: Signal-Unchanged Check Too Strict (May 2026)

**Symptom:** alpha_mode fix's `np.array_equal(prev_held, curr_sig_bool)` was never True on weekly/monthly strategies, so daily rebalancing continued.

**Root cause:** `prev_held` (from `shares[:, t-1] > 0`) reflects positions AFTER trading-rule filtering (limit up/down, suspension). `curr_sig_bool` (from `_alpha_to_weights`) reflects ALL stocks with alpha > 0. When 3 out of 36 stocks were filtered by trading rules on day 0, `prev_held` had 33 stocks while `curr_sig_bool` had 36. `np.array_equal` returned False.

**Fix:** Compare raw alpha signals instead of derived stock sets:
```python
# BEFORE (broken):
prev_held = shares[:, t-1] > 0
curr_sig_bool = sig_t.copy()
if np.array_equal(prev_held, curr_sig_bool): ...

# AFTER (working):
prev_sig = signal[:, t-1]
curr_sig = signal[:, t]
if np.array_equal(prev_sig, curr_sig): ...
```
Comparing raw `signal` (the float alpha matrix) is robust because `forward_fill_alpha` copies exact values from rebalance day to non-rebalance days. No trading-rule filtering affects the raw alpha.

### Bug: alpha_mode Daily Rebalancing (Prior Session)

**Symptom:** Monthly/weekly strategy shows 128% in first month, then flatlines.

**Root cause:** `BacktestEngine(alpha_mode=True)` in "正常再平衡" recalculates positions EVERY day via `alloc_base * weights / close[t]`, ignoring the strategy's `weekly_filter`/`monthly_filter`. This causes:
1. Day 1 rebalance captures all P&L via `net_pnl` line 808-809
2. Cash continually reset to ~0
3. PV stays artificially inflated
4. `index_returns` adds phantom returns on top

**Fix:** In "正常再平衡" section, check if raw alpha signal == previous day:
```python
if self.alpha_mode and t > 0:
    if np.array_equal(signal[:, t-1], signal[:, t]):
        # Signal unchanged → carry forward, skip rebalance
        pv[t] = has_cash + sum(shares[:, t-1] * close[:, t])
        shares[:, t] = shares[:, t-1].copy()
        continue
```

### Bug: Limit Up/Down Symmetry (May 2026)

**Symptom:** Positions stuck longer than expected; abnormal turnover.

**A-share rules:**
- 涨停 (limit up): can SELL (take profit), cannot BUY
- 跌停 (limit down): can BUY (bottom-fish), cannot SELL

Original code blocked both directions for both states. Fix in `get_tradeable_mask()`:
```python
can_buy  = ~suspended & ~limit_up & ~new_stock       # limit-down OK to buy
can_sell = ~suspended & ~limit_down & ~new_stock      # limit-up OK to sell
```

## Verification After Fix

After fixing engine code, verify by re-running the affected strategy:

```bash
PYTHONIOENCODING=utf-8 python -c "
from strategies.s108_lowprice_rsi_neutral_monthly import main
main()
"
```

Checklist:
- First month daily returns should be ±5% max (not 5-16%)
- Turnover should be 0% on non-rebalance days
- `diff=0` for shares-carry-forward days
- NAV should show reasonable CAGR (8-12% for CSI1000 strategies)
- Position values should change daily (tracking price changes)

## Key Files

- `core/backtest_utils.py` — BacktestEngine, TradingRules, _alpha_to_weights, Visualizer
- `core/alpha_utils.py` — batch computation functions (vol_n_batch, decay_linear_batch, zscore_rank_matrix, forward_fill_alpha)
- `core/update_fundamentals.py` — fundamental data downloader
- `results/<FOLDER>/daily.csv` — daily_return, turnover, trade_cost
- `results/<FOLDER>/nav.csv` — NAV series
- `results/<FOLDER>/position_matrix.npz` — daily position values (for deep inspection)
- `results/<FOLDER>/stats.csv` — summary statistics
