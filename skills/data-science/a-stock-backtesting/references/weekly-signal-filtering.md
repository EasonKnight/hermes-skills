# Weekly Signal Filtering from Daily Data

## The Problem

A mean reversion strategy that trades daily has enormous turnover costs (187%
of capital in transaction costs over 3 years). Converting to weekly trading
drops costs to ~40% and reduces max drawdown from 78% to 17%.

## Strategy: Only trade on the first trading day of each ISO week

The signal logic stays the same (buy stocks that fell the previous day), but
only on Mondays (or the first trading day after a holiday).

## Implementation

```python
import numpy as np
from pandas import to_datetime

def generate_weekly_signals(close, dates):
    """Generate daily return + signal matrix, then filter to weekly only."""
    n_stocks, n_days = close.shape
    
    # 1. Compute daily returns
    ret = np.zeros_like(close)
    mask = (close[:, :-1] != 0) & ~np.isnan(close[:, :-1])
    with np.errstate(divide="ignore", invalid="ignore"):
        ret[:, 1:] = np.where(mask, close[:, 1:] / close[:, :-1] - 1.0, 0.0)
    
    # 2. Daily signal: buy stocks that fell yesterday
    signal = np.zeros_like(close, dtype=bool)
    signal[:, 1:] = ret[:, :-1] < 0.0
    
    # 3. Weekly filter: ISO week number change → first trading day of week
    dt = to_datetime(dates)
    weeks = dt.isocalendar().year.astype(str) + "-W" + dt.isocalendar().week.astype(str)
    first_of_week = np.ones(len(dt), dtype=bool)
    first_of_week[1:] = weeks[1:].values != weeks[:-1].values
    
    # Zero out signals on non-first-of-week days
    signal[:, ~first_of_week] = False
    
    return ret, signal
```

## Caveats

- **ISO week boundaries**: `isocalendar().week` follows ISO 8601 (Mon-Sun).
  Week 1 is the week containing the first Thursday of the year. This correctly
  handles year-end transitions (Dec 30-31 might be week 1 of next year).

- **Holiday handling**: If Monday is a holiday, the first trading day of the
  week is Tuesday. The `week number change` pattern correctly identifies it
  because `weeks[t] != weeks[t-1]` will be True.

- **Performance drop**: Gross return drops from +46% (daily) to +29% (weekly)
  because the strategy has fewer reversion opportunities. But net return
  improves dramatically because costs drop 5×.

## Alternatives

| Variation | Logic | Use Case |
|-----------|-------|----------|
| Weekly close-to-close | Buy on Monday if previous Friday was down | Standard weekly reversion |
| Monthly rebalance | Trade on first trading day of month | Maximum cost reduction |
| Bi-weekly | Trade every 2 weeks | Middle ground |
