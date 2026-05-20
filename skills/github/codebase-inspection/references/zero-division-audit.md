# Zero-Division Audit for NumPy Quant Code

Technique for systematically finding unprotected division-by-zero in numpy-heavy financial code.

## When to Run

- User says "排查所有的0分母保护" / "check all zero division protection"
- After major refactoring that touches math heavy code
- Before deployment of new signal/alpha strategies

## The Audit Method

### Phase 1: Harvest All Division Sites

Find every `/` operator in the target files:

```bash
# Find all division operations in core files
grep -n '/ [a-zA-Z_]' core/*.py | grep -vE '#|http|///'

# Specifically find close/close divisions (common in ret calculations)
grep -n 'close\[.*\] / close\[' core/*.py strategies/*.py
```

### Phase 2: Classify Each Site

For each division, categorize protection level:

| Protection | Pattern | Verdict |
|------------|---------|---------|
| `np.maximum(divisor, 1e-10)` | Division denominator is wrapped | ✅ **Safe** |
| `np.where(cond, ..., 0.0)` | Division only executed when `cond` guarantees safety | ✅ **Safe** |
| `+ 1e-10` | Small epsilon added to divisor | ✅ **Safe** |
| `if guard > 0:` | Python-level check before division | ✅ **Safe** |
| `try/except` | Exception catches ZeroDivisionError | ✅ **Safe** |
| Raw `a / b` | No protection visible | ⚠️ **Check context** |

### Phase 3: Context Analysis for Raw Divisions

For each raw division found, trace upstream to see if the divisor could be zero:

**Checklist:**
1. Is the divisor a count/stats variable guarded by an `if n > 0` check?
   - Example: `n_selected` guarded by `if n_selected == 0: return`
2. Is the divisor a matrix that was pre-clamped?
   - Example: `amt = np.maximum(close * volume, 1)` → `amt_win = amt[...]` is always ≥1
3. Is there a `np.where(np.isfinite(...))` catch after the division?
   - Example: `rets = a / b` then `rets = np.where(np.isfinite(rets), rets, 0.0)` — catches inf but still computes it
4. Is the divisor a scalar literal (always > 0)?
5. Is the division inside a loop with a `if t > 0` guard?

### Phase 4: Nested Call Analysis

For batch functions that take pre-computed parameters:
```python
def amihud_illiq_fast(amt, close, t, n=20):
    ill = np.abs(rets) / amt_win  # amt is caller's responsibility
```
- Check ALL callers: do they pass `np.maximum(amt, 1)` or raw `amt`?
- If any caller passes un-clamped data, the batch function is vulnerable

### Phase 5: Fix Pattern

Standard fix pattern — add `np.maximum(divisor, 1e-10)`:

```python
# Before (vulnerable)
rets = close[held, t] / close[held, t - 1] - 1

# After (protected)
rets = close[held, t] / np.maximum(close[held, t - 1], 1e-10) - 1

# For benchmark/standard computations
csi_ret[1:] = idx_close[1:] / np.maximum(idx_close[:-1], 1e-10) - 1.0
bm_ret[1:] = bm_nav[1:] / np.maximum(bm_nav[:-1], 1e-10) - 1.0
```

Use `1e-10` (not `1e-8`) for financial price computations to avoid meaningful distortion.
Use `1e-8` for volume/amount ratios where values can be small.
Use `0.01` for amount averages to avoid ratio blowup on near-zero denominators.

## Common Patterns in Quant Code

| Calculation | Typical Guard | Failure Mode |
|------------|---------------|--------------|
| `close[t] / close[t-1] - 1` (ret) | `np.maximum(close[t-1], 1e-10)` | New stock with first day close=0 |
| `idx_close[t] / idx_close[t-1]` (index ret) | `np.maximum(idx_close[t-1], 1e-10)` | CSI1000 data gap days |
| `bm_nav[t] / bm_nav[t-1]` (benchmark ret) | `np.maximum(bm_nav[t-1], 1e-10)` | Benchmark NAV collapse (theoretical) |
| `abs(zscore) / divisor` (Amihud illiq) | Pre-clamp `amt = np.maximum(amt, 1)` | Suspended stock with 0 volume |
| `score / score_sum` (weight normalization) | `if score_sum > 0` guard | All scores zero |
| `amount / lots` (price per lot) | `if lots > 0` guard | Invalid position data |

## Pitfalls

- **False negatives:** `ill = np.abs(rets) / amt_win` where `amt = np.maximum(close * volume, 1)` at line 50 but `amihud_illiq_fast()` takes `amt` as param — caller might pass unclamped data
- **False positives:** raw division inside `np.where(cond, ...)` — the division is only computed when `cond` is True, but numpy computes BOTH branches before applying the mask, so it still raises if the divisor is 0 even in the False branch
- **NaN→bool trap:** `pd.Series([True, False, np.nan]).values.astype(bool)` converts NaN to True — always use `.fillna()` first
