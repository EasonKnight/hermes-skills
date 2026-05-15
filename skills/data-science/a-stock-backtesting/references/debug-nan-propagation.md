# NaN Propagation Bug: `0 * NaN = NaN`

## The Problem

In a vectorized backtest with a (N_stocks × N_days) price matrix, you mask invalid stocks
(those with NaN close prices) to 0:

```python
valid = (close > 0.5) & ~np.isnan(close)
shares = np.where(valid, target / close, 0.0)
current_value = shares[:, t-1] * close[:, t]   # ← BUG HERE
portfolio_value = np.sum(current_value)          # ← returns NaN
```

Even though `shares` is 0 for NaN stocks, `0.0 * NaN = NaN` in IEEE 754 arithmetic.
`np.sum()` over an array that contains even a single NaN returns NaN.

## Symptoms

- Portfolio value becomes NaN after the first rebalance
- All downstream statistics (return, Sharpe, drawdown) are NaN
- The backtest "runs" instantly with no errors — no exception is raised

## Detection

Check your price matrix early:

```python
print(f"NaN count: {np.isnan(close).sum()}")
```

With 5000 A-share stocks × 726 trading days, expect ~3000-4000 NaN entries
(from stocks listed after the start date, ffill couldn't fill the beginning).

## Fix Options

### Option A: Clean upfront (recommended)

```python
close = np.where(np.isnan(close), 0.0, close)
```

Do this **before** the validity mask. Now `0.0 * 0.0 = 0.0` everywhere, and
`valid = (close > 0.5)` correctly excludes zeroed entries.

### Option B: Use `np.nansum` everywhere

```python
portfolio_value = np.nansum(current_value)
```

Fragile — easy to miss one call site.

## Root Cause

`pandas.DataFrame.ffill(axis=1)` forward-fills NaN for existing stocks that
were suspended, but stocks that **listed after the start date** still have NaN
for their pre-listing period. These pass through `dropna(thresh=...)` because
they have enough post-listing data, but the early columns remain NaN.
