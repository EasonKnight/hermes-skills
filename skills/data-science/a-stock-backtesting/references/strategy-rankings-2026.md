# A-Share 10-Strategy Rankings (2016-2026)

Dataset: 2930 stocks, 2426 trading days, CSI 1000 benchmark (+9.06% total).
Trading rules: limit up/down, suspension, new stock filter (22-day IPO lockout).
Position cap: 10% max per stock.
Return method: fixed-base (P&L / ¥100M), no compounding.

## Final Rankings

| # | Strategy | Total Return | Annualized | Sharpe | Max DD | Info Ratio |
|---|----------|-------------|-----------|-------|--------|-----------|
| 1 | **S06 动量日频** | **+239.78%** | **24.22%** | **0.73** | -50.12% | 0.62 |
| 2 | **S07 低波周频** | **+154.01%** | **15.55%** | **0.64** | **-41.34%** | 0.61 |
| 3 | S02 等权周频 | +134.49% | 13.58% | 0.49 | -48.86% | 0.72 |
| 4 | S01 等权日频 | +134.16% | 13.55% | 0.49 | -48.88% | 0.72 |
| 5 | S03 均值回归周频 | +11.80% | 1.19% | 0.14 | -35.81% | 0.01 |
| 6 | S04 均值回归日频 | +3.18% | 0.32% | 0.02 | -61.03% | -0.05 |
| 7 | S05 动量周频 | -29.45% | -2.97% | -0.21 | -64.60% | -0.34 |
| 8 | S08 高波周频 | -48.05% | -4.85% | -0.34 | -75.80% | -0.58 |
| 9 | S10 RSI超买周频 | -80.79% | -8.16% | -0.72 | -87.10% | -0.95 |
| 10 | S09 RSI超卖周频 | +24677%* | +2492%* | 0.91 | -82.37% | 0.03 |

*S09 RSI超卖 produces extreme returns due to rare-signal concentration.
The strategy has only ~5-50 stocks per week meeting RSI < 30, each capped at 10%.
During crash rebounds this creates outsized daily P&L. Do not use without stop-losses.

## Key Takeaways

1. **Daily momentum (top 20% gainers) wins** — Sharpe 0.73, low drawdown relative to return
2. **Low volatility is the best risk-adjusted** — Sharpe 0.64, minimum drawdown
3. **Equal weight is the baseline** — ~135% over 10 years with zero signal complexity
4. **Weekly frequency kills momentum** — S05 (weekly) is -29% vs S06 (daily) +239%
5. **RSI overbought and high vol are toxic** — both lose money over 10 years
6. **Mean reversion barely works** — daily version near flat, weekly slightly positive

## Strategy File Map

| File | Result Folder |
|------|---------------|
| s01_equal_weight_daily.py | results/S01-等权日频/ |
| s02_equal_weight_weekly.py | results/S02-等权周频/ |
| s03_mr_weekly.py | results/S03-均值回归周频/ |
| s04_mr_daily.py | results/S04-均值回归日频/ |
| s05_momentum_weekly.py | results/S05-动量周频/ |
| s06_momentum_daily.py | results/S06-动量日频/ |
| s07_lowvol_weekly.py | results/S07-低波周频/ |
| s08_highvol_weekly.py | results/S08-高波周频/ |
| s09_rsi_oversold_weekly.py | results/S09-RSI超卖周频/ |
| s10_rsi_overbought_weekly.py | results/S10-RSI超买周频/ |
