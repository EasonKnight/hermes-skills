# 10 A-Share Strategy Implementations & Results

All strategies use the same shared framework (`backtest_utils.py`):
- **Data**: 4952 stocks, 726 trading days (2023-05-16 ~ 2026-05-15)
- **Benchmark**: CSI 1000 (中证1000, +33.25%)
- **Cost**: commission 0.03% + slippage 0.1% per side = 0.13%
- **Cache**: first run ~10s (CSV parse), subsequent ~0.15s (.npz)

## Strategy Code Pattern

Each strategy is an independent file with:
1. A `generate_signal(close, dates, **kw)` → `bool[N_stocks, N_days]` function
2. A `main()` that loads data → generates signal → runs engine → saves results

Results auto-save to `results/SXX-策略名/` with chart + CSV.

## Implemented Strategies

### S01 等权日频 (`s01_equal_weight_daily.py`)
```python
def generate_signal(close, dates=None, **kw):
    return close > 0.5   # all valid stocks, every day
```
- **Total Return**: +66.68%  **Ann**: 18.82%  **Sharpe**: 0.80  **Max DD**: -32.62%

### S02 等权周频 (`s02_equal_weight_weekly.py`)
```python
# Signal only on Monday, hold between Mondays
first = weekly_filter(dates)
signal[:, first] = valid[:, first]
for t in range(1, n_days):
    if not first[t]:
        signal[:, t] = signal[:, t-1]
```
- **Total Return**: +66.80%  **Ann**: 18.85%  **Sharpe**: 0.80  **Max DD**: -32.62%
- *Nearly identical to daily — daily rebalance adds negligible turnover for equal weight*

### S03 均值回归周频 (`s03_mr_weekly.py`)
```python
# Signal: stock fell on previous trading day, only on Mondays
ret[:, 1:] = close[:, 1:] / close[:, :-1] - 1.0
signal[:, 1:] = ret[:, :-1] < 0.0
signal[:, ~weekly_filter(dates)] = False
```
- **Total Return**: +6.01%  **Ann**: 1.99%  **Sharpe**: 0.36  **Max DD**: -10.24%
- *Lowest drawdown but barely beats cash*

### S04 均值回归日频 (`s04_mr_daily.py`)
```python
# Signal: stock fell yesterday, every day
ret[:, 1:] = close[:, 1:] / close[:, :-1] - 1.0
signal[:, 1:] = ret[:, :-1] < 0.0
```
- **Total Return**: +46.44%  **Ann**: 13.74%  **Sharpe**: 0.63  **Max DD**: -35.04%

### S05 动量周频 (`s05_momentum_weekly.py`) ⚠️ Weak
```python
ret[:, 5:] = close[:, 5:] / close[:, :-5] - 1.0  # 5-day return
# On each Monday, pick top 20% by return
for t in first_of_week[d]ays:
    signal[:, t] = (ret[:, t] >= percentile(ret, 80)) & valid
```
- **Total Return**: +8.98%  **Ann**: 2.94%  **Sharpe**: 0.24  **Max DD**: -44.65%
- *Weekly momentum fails — window is too wide, misses the quick move*

### S06 动量日频 (`s06_momentum_daily.py`) ★ BEST
```python
ret[:, 1:] = close[:, 1:] / close[:, :-1] - 1.0
for t in range(1, n_days):
    signal[:, t] = (ret[:, t] >= percentile(ret, 80)) & valid
```
- **Total Return**: +120.38%  **Ann**: 30.56%  **Sharpe**: 1.11  **Max DD**: -28.51%
- *Daily momentum crushes everything — buy yesterday's top 20%, sell tomorrow*

### S07 低波周频 (`s07_lowvol_weekly.py`) ★ Best Risk-Adjusted
```python
vol[:, t] = std(ret[:, t-19:t+1], axis=1)  # 20-day vol
# Pick bottom 20% by vol on Monday, hold for week
signal[:, t] = (vol[:, t] <= percentile(vol, 20)) & valid
```
- **Total Return**: +54.85%  **Ann**: 15.90%  **Sharpe**: 0.91  **Max DD**: -21.59%
- *Best Sharpe after S06, lowest drawdown among top performers*

### S08 高波周频 (`s08_highvol_weekly.py`) ⚠️
```python
signal[:, t] = (vol[:, t] >= percentile(vol, 80)) & valid
```
- **Total Return**: +10.11%  **Ann**: 3.30%  **Sharpe**: 0.27  **Max DD**: -48.89%
- *High vol alone is not a signal — too much noise*

### S09 RSI超卖周频 (`s09_rsi_oversold_weekly.py`)
```python
# RSI(14) < 30 → oversold buy signal
rsi[:, t] = 100 - 100 / (1 + avg_gain/avg_loss)
signal[:, t] = (rsi[:, t] < 30) & valid
```
- **Total Return**: +34.87%  **Ann**: 10.62%  **Sharpe**: 0.52  **Max DD**: -36.55%
- *Oversold bounce works modestly*

### S10 RSI超买周频 (`s10_rsi_overbought_weekly.py`) ⚠️ WORST
```python
signal[:, t] = (rsi[:, t] > 70) & valid  # overbought → buy? bad idea
```
- **Total Return**: -36.93%  **Ann**: -14.40%  **Sharpe**: -0.52  **Max DD**: -61.27%
- *Buying overbought stocks is a losing trade — they revert*

## Rankings

| Rank | Strategy | Total Return | Ann Return | Sharpe | Max DD |
|------|----------|-------------|-----------|--------|--------|
| 🥇 | S06 动量日频 | +120.38% | 30.56% | 1.11 | -28.51% |
| 🥈 | S02 等权周频 | +66.80% | 18.85% | 0.80 | -32.62% |
| 🥉 | S01 等权日频 | +66.68% | 18.82% | 0.80 | -32.62% |
| 4 | S07 低波周频 | +54.85% | 15.90% | 0.91 | -21.59% |
| 5 | S04 均值回归日频 | +46.44% | 13.74% | 0.63 | -35.04% |
| 6 | S09 RSI超卖周频 | +34.87% | 10.62% | 0.52 | -36.55% |
| 7 | S08 高波周频 | +10.11% | 3.30% | 0.27 | -48.89% |
| 8 | S05 动量周频 | +8.98% | 2.94% | 0.24 | -44.65% |
| 9 | S03 均值回归周频 | +6.01% | 1.99% | 0.36 | -10.24% |
| 10 | S10 RSI超买周频 | -36.93% | -14.40% | -0.52 | -61.27% |

## Key Takeaways

1. **Daily momentum dominates** — buying yesterday's top 20% gainers (S06) has Sharpe 1.11, ann return 30.56%. The strategy captures intra-week trend continuation.

2. **Frequency matters more than signal** — The same signal (momentum) goes from +120% (daily) to +9% (weekly). Weekly rebalancing misses the short-term moves that drive returns.

3. **Low vol is the best defensive factor** — S07 achieves 15.9% ann with only -21.6% drawdown. Low-vol stocks tend to have steady positive drift without crashes.

4. **Equal weight is the baseline to beat** — S01/S02 (+66%) outperforms most active strategies without any signal at all.

5. **Mean reversion works daily, fails weekly** — S04 (+46%) vs S03 (+6%). The weekly version misses too many reversion opportunities.

6. **RSI overbought (>70) is a destroyer of capital** — S10 loses 37%. Buying into strength that's already extreme is a trap.

## Typical Runtime

| Phase | Time |
|-------|------|
| .npz load (cached) | 0.10s |
| CSI 1000 download | 0.2s |
| Signal generation | 0.01-0.05s |
| Backtest engine | 0.1s |
| Chart save | 0.3s |
| **Total per strategy** | **~0.7s** |
| **All 10 (run_all.py)** | **~8s** |
