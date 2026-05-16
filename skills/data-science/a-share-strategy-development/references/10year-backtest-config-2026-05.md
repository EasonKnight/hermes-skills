# 10年回测配置与新上市股票处理

## 配置变更

2026-05-16 将回测从5年(2021-05-17)改为10年(2016-05-17)：

```
BACKTEST_START = "2016-05-17"  # 在 core/backtest_utils.py 第24行
```

## 新上市股票导致的问题

在10年回测中，CSI1000成分股数从2016年的399只增长到2026年的775只。新股上市首日其前一日收盘价 = 0，计算收益率时 `close[t]/close[t-1] - 1 = inf/0 - 1 = inf`，污染了等权基准的均值计算。

### 症状
- 等权基准(等权周频)计算后 NAV 出现大量 inf (2417/2426天)
- stats 中`基准收益: inf%`, `超额收益: -inf%`, `跟踪误差: nan%`

### 修复

在 `_compute_benchmark()` 的日收益率计算后增加 `np.isfinite` 过滤：

```python
returns = close[held, t] / close[held, t-1] - 1
# 排除上市首日（前一日close=0导致inf）
returns = np.where(np.isfinite(returns), returns, 0.0)
daily_ret[t] = np.nanmean(returns)
```

只需修改 `BacktestEngine._compute_benchmark()` 中的收益率计算行。

## 执行命令

```bash
USERPROFILE="C:\Users\Mayn" python -m core.platform run
```

10年回测约需 3-5 分钟（52个策略 x 2426交易日）。单个策略约 2-8 秒。
