# BacktestEngine 回测引擎修改记录

## 现金按中证1000指数计收益（防过拟合）

### 改动文件
`core/backtest_utils.py` — `BacktestEngine` 类

### 新增参数
```python
BacktestEngine(..., index_returns=None)
```
- `index_returns`: ndarray (N_days,) 中证1000日收益率数组
- 不传则自动从 akshare 下载 `sh000852`

### 逻辑（`run()` 方法中主循环后）

```python
# 每日的 cash_part = 1亿 - 昨日股票市值
# pv[t] 加上 cash_part × 中证1000日收益率
for t in range(1, n_days):
    prev_stock_mv = np.sum(shares[:, t-1] * close[:, t-1])
    cash_part = max(0, self.fixed_base - prev_stock_mv)
    if cash_part > 0 and np.isfinite(self.index_returns[t]):
        pv[t] += cash_part * self.index_returns[t]
```

### 缓存机制
- 首次加载时存 `self._csi1000_idx_close = idx_close`
- `_compute_benchmark()` 中检查 `hasattr(self, "_csi1000_idx_close")`，有则直接复用
- 避免 akshare 重复下载

### 影响
- 策略即使有大量"空仓"日，现金部分仍按指数走，无法通过低仓位躲大跌
- 适用于验证策略的真实风险调整后收益

## amihud_illiq_fast 优化

### 改动文件
`core/alpha_utils.py`

### 新增函数
```python
def amihud_illiq_fast(amt, close, t, n=20):
    """amihud_illiq 的预计算成交额版"""
    start = max(0, t - n)
    if t - start < 5:
        return np.zeros(close.shape[0])
    rets = close[:, start+1:t+1] / np.maximum(close[:, start:t], 1e-10) - 1
    amt_win = amt[:, start+1:t+1]
    ill = np.abs(rets) / amt_win
    return np.nanmean(ill, axis=1)
```

### 使用方式
```python
amt = np.maximum(close * volume, 1)  # 循环前算一次
for t in range(20, n_d):
    ill = amihud_illiq_fast(amt, close, t, 20)  # 循环内只切片
```

### 已优化的 8 个策略
a212, a213, a215, a219, a264, a268, a269, a280

## MIN_COVERAGE 变更

### 改动文件
`core/backtest_utils.py` — 模块常量

### 当前值
```python
MIN_COVERAGE = 0.0  # 不限制，纳入全部 5203 只 A 股
```

### 影响
- CSV 中有 5203 只股票
- 覆盖率 90% 时只保留 2930 只（需上市 >9 年）
- 设为 0 后全部保留
- **必须删除 NPZ 缓存**：`rm data/a_stock_kline_3y.npz`

## batch_run.py 单进程批量运行器

### 文件位置
`/c/Users/Mayn/Desktop/a_stock_trade/batch_run.py`

### 用法
```bash
python batch_run.py                       # 全部策略
python batch_run.py --tags alpha          # 按标签
python batch_run.py --names a212 a219     # 按名字
python batch_run.py --freq weekly         # 按频率
```

### 核心流程
1. `DataLoader().load()` — 加载数据 1 次
2. `importlib` 动态导入策略模块
3. 调用 `module.generate_alpha(c, d, volume=v)` — 共享同一份数据
4. `BacktestEngine.run()` + `Visualizer.plot_and_save()`
5. 汇总到 `results/_summary_batch.csv` + 年化排名打印

### 与 platform.py run 的区别
| 特性 | platform.py run | batch_run.py |
|------|----------------|--------------|
| 运行方式 | 子进程隔离 | 单进程 |
| 数据加载 | 每个策略 1 次 | 总共 1 次 |
| 隔离性 | 高（进程隔离） | 低（共享模块） |
| 速度 | 100 策略 ≈ 5 分钟 | 100 策略 ≈ 2-3 分钟 |
