# Session Bug Log — Backtest Framework

(Referenced by `a-stock-backtest-framework` SKILL.md — see bug fixes & edge cases section.)

## Bug 1: 0 × NaN = NaN (DataLoader)

**Symptom:** Entire portfolio NAV becomes NaN.
**Root cause:** `close` matrix has NaN entries (new stocks early period). `np.where(valid, x, 0.0)` sets entries to 0, but `0 * NaN = NaN` in numpy.
**Fix:** `close_df = close_df.ffill(axis=1).fillna(0.0)` — replace NaN with 0 after forward-fill.

## Bug 2: names_arr Missing on First Run (DataLoader)

**Symptom:** `AttributeError: 'DataLoader' object has no attribute 'names_arr'` on first CSV load.
**Root cause:** `self.names_arr` was only set inside the `if os.path.exists(cache_path):` branch, not in the CSV-load branch.
**Fix:** Add `self.names_arr = names_filtered.values` in the CSV-load path.

## Bug 3: New Stock Detection False Positives (TradingRules)

**Symptom:** 80% of stocks flagged as "newly listed" on day 0, blocking nearly all trading.
**Root cause:** `np.argmax(close[i,:] > 0)` returns 0 for stocks that existed before dataset start. The check `if first > 0 or self.close[i, 0] > 0` is True for ALL of them.
**Fix:** Only flag as new if `first == 0 and close[i, 0] > 0` → skip (not new). Only flag if `first > 0`.

## Bug 4: Position Cap Cost Double-Counting (BacktestEngine)

**Symptom:** Portfolio value decays faster than expected.
**Root cause:** Position capping added `cost_excess` to `tc[t]`, but then `tc[t] = cost` (from traded_sum) overwrote it. Separately, `has_cash += excess_val - cost_excess` deducted cost from cash, while `pv[t] -= cost` also deducted from total — double deduction.
**Fix:** Remove `cost_excess` entirely. Capping just does `has_cash += excess_val` (gross). The traded_sum from the diff between old and capped positions captures all costs.

## Bug 5: pv[t] Not Reflecting Capping Cash (BacktestEngine)

**Symptom:** `pv[t]` lower than actual cash + positions after capping.
**Root cause:** `pv[t]` was set to `total` before capping, then `pv[t] -= cost`. Capping added cash to `has_cash` but never updated `pv[t]`.
**Fix:** After capping and computing cost, set `pv[t] = has_cash + np.sum(new_pos)`.

## Bug 6: RSI Concentration Explosion (S09)

**Symptom:** 24000%+ return on fixed-base. n_effective ≈ 1-10 stocks.
**Root cause:** RSI < 30 is rare. When only 1-5 stocks are tradeable, target_amt = total / 5, position cap limits to 10% each → 50% cash. Cash keeps growing from position cap → next cycle deploys more → feedback loop.
**Fix:** Three layers:
1. `MIN_EFFECTIVE = max(20, n_sig * 0.1)` stops rebalance when too few stocks
2. RSI threshold lowered from 30 to 25
3. Min 80-stock signal count gate in strategy itself

## Pitfall: svchost / schtasks.exe Through MSYS

On Windows, schtasks.exe path parsing breaks in MSYS bash (paths like `/c/Users/...` get transformed). **Always use Python subprocess or cmd.exe /c with proper Windows paths** for task registration.
