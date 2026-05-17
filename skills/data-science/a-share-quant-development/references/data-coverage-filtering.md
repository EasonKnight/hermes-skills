# 数据覆盖率过滤（MIN_COVERAGE）

## 问题

CSV 原始数据有 ~5,203 只 A 股，但 NPZ 缓存加载后只剩 ~2,930 只。

## 原因

`core/backtest_utils.py` 中 `MIN_COVERAGE = 0.9`（默认 90%）：

```python
MIN_COVERAGE = 0.9
# ...
min_days = int(close_df.shape[1] * self.min_coverage)
keep = close_df.dropna(thresh=min_days).index
```

2426 个交易日 × 0.9 = 2183 天。上市不足 9 年的股票（2019 年后 IPO）全部被过滤。A 股近年大量新股，所以去除近一半。

## 覆盖率分布（2026-05 数据）

| 阈值 | 股票数 | 可承受的上市时长 |
|------|--------|------------------|
| 90% | 2,930 | 上市 ≥ 9 年 |
| 50% | 4,112 | 上市 ≥ 5 年 |
| 30% | 4,849 | 上市 ≥ 2 年 |
| 0%  | 5,203 | 无限制 |

## 修复

设 `MIN_COVERAGE = 0.0` 纳入全部股票。引擎自动处理上市前的 NaN 值。

## 重要

**修改 MIN_COVERAGE 后必须删除 `data/a_stock_kline_3y.npz` 缓存**，否则下次加载仍用旧缓存。

```bash
rm ~/Desktop/a_stock_trade/data/a_stock_kline_3y.npz
```

下次 `DataLoader().load()` 会从 CSV 重新构建并写入新 NPZ（~48秒）。
