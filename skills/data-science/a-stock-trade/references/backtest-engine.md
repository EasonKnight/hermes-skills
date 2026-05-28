# Backtest Engine Internals

Key implementation details and known bugs in `core/backtest_utils.py`.

## Fixed-Base Backtest Engine Pitfalls

### Bug 1: has_cash going negative
Fix: Use `min(fixed_base, available_total)` for allocation base.

### Bug 2: Rebalance costs not deducted
Fix: Add `has_cash -= cost` after rebalance.

### Bug 3: Cost recovery effect
Fix: `has_cash = available - mv - cost`, `pv = has_cash + mv`

### Bug 4: Excess return using fixed-base NAV ratio
Fix: Use percentage returns `pct_ret[t] = pv[t]/pv[t-1]-1`

### Bug 5: alpha_mode daily rebalance on non-rebalance days
When alpha signals are forward-filled to non-rebalance days, the engine rebalances daily → fake excess returns (128% first month).

**Fix**: Compare raw alpha signal vectors: `np.array_equal(signal[:, t-1], signal[:, t])`. If identical (forward-filled), carry positions forward without rebalancing.

**Pitfall 1**: Don't compare stock selection sets — valid mask filtering changes day to day even when signals are identical.
**Pitfall 2**: `forward_fill_alpha` uses `np.maximum.accumulate(idx)` → matrix columns for non-rebalance days are the same memory reference as the rebalance day → `np.array_equal` always True.

### Bug 6: Limit-up/down buy-sell asymmetry
A-share rules: limit-up = can sell not buy, limit-down = can buy not sell. Original code blocked both.
Fix: `can_buy = ~limit_up` (can buy on limit-down), `can_sell = ~limit_down` (can sell on limit-up).

### Bug 7: max_position_pct double-counting
Position cap `excess_val` was added to `has_cash` AND included in `net_pnl` → double-counted.
Fix: Delete the `has_cash += excess_val` line. `net_pnl` handles it completely.
Symptom: Backtest first month daily returns >10%.

## Chart Layout (Visualizer.plot_and_save)
3 subplots, dark theme, 14×10 inches:
1. Strategy NAV + equal-weight benchmark (dashed) + equal-weight excess (dotted) + position count (right axis bars)
2. CSI 1000 excess curve (difference method, max drawdown annotation)
3. Equal-weight excess curve (difference method, excess drawdown annotation)

## matplotlib Figure Leak Prevention
```python
# Strategy level
finally:
    import matplotlib.pyplot as _plt
    _plt.close('all')

# Engine level
plt.close(fig)         # Precise close
plt.close('all')       # Safety net
```

## NPZ Cache
- Structure from `_build_cache()`: close, open, volume, high, low, codes, dates, names, is_st, exchange
- 5241 stocks × ~2427 days float64 = ~95MB
- `DataLoader.load()`: NPZ priority → CSV fallback → auto-rebuild NPZ
- `np.load(npz, allow_pickle=True, mmap_mode='r')` for metadata-only reads (don't load full close matrix)
- NPZ axis: `(n_stocks, n_dates)` — index with `data[field][:, t]` for time-t cross-section
