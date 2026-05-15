# 集中度放大效应排查记录（S09 案例）

## 初始现象

RSI超卖周频策略（S09）总收益 24677%，超额夏普仅 0.91，回撤 -82%。

## 排查步骤

### 第一步：检查 RSI 计算

```python
def _rsi(close, w=14):
    rsi = np.zeros_like(close)
    ret = np.zeros_like(close)
    mask = close[:, :-1] != 0
    with np.errstate(divide="ignore", invalid="ignore"):
        ret[:, 1:] = np.where(mask, close[:, 1:] / close[:, :-1] - 1.0, 0.0)
    for t in range(w, close.shape[1]):
        c = ret[:, t-w+1:t+1]
        g = np.where(c > 0, c, 0); l = np.where(c < 0, -c, 0)
        ag = np.nanmean(g, axis=1); al = np.nanmean(l, axis=1)
        rs = np.divide(ag, al, out=np.zeros_like(ag), where=al > 0)
        rsi[:, t] = 100 - 100 / (1 + rs)
    return rsi
```

RSI 分布正常：mean=49.9, std=16.8, 12.89% < 30。计算无误。

### 第二步：检查信号量

```python
# 仅看周一（信号生成日）
mon_counts = [signal[:, t].sum() for t in np.where(first)[0] if t >= 14]
# 结果：median=23, 45% 的周一信号<20只
```

信号量太少！45% 的周一只有不到 20 只股票触发 RSI<30。

### 第三步：追踪组合 P&L

手动复现 BacktestEngine 逻辑发现：当 `n_effective < MIN_EFFECTIVE` 时保持持仓不动，但少量持仓不断反弹→超限→套现→再投，形成正反馈。

### 第四步：修复

RSI 阈值从 30 降到 25，且加 `if mask.sum() >= 80` 保护。

修复后：总收益 -5.68%，超额夏普 -0.05。结果合理。

---

# S35 参数调优记录

## 调优目标

寻找 `lookback`（低点回看窗口）和 `hold_days`（低点后持有天数）的最优组合。

## 参数空间

- lookback: [5, 10, 15, 20, 30]
- hold_days: [3, 5, 8, 10, 15]
- 共 25 种组合

## 结果排名

```
 1. L5H15: 超额夏普 0.71  年化 15.39%  回撤 -48.46%  日均 2807 只
 2. L5H10: 超额夏普 0.68  年化 17.38%  回撤 -47.69%
 3. L5H8:  超额夏普 0.67  年化 20.95%  回撤 -47.56%
 4. L15H15:超额夏普 0.66  年化 12.27%  回撤 -48.83%
 5. L5H5:  超额夏普 0.61  年化 23.57%  回撤 -43.24%
 6. L5H3:  超额夏普 0.58  年化 12.89%  回撤 -46.63%
...
25. L30H3: 超额夏普 0.00  年化 130089%  回撤 -92.31%
```

## 关键规律

1. **回看窗口越短越好**（L5 > L10 > L15 > L20 > L30）——捕捉小幅回调成功率更高
2. **持有期越长越平滑**（H15 > H10 > H8）——给反弹足够时间兑现
3. **长窗口+短持有暴雷**（L30H3: 130089%收益但回撤-92%）——信号太稀有，集中度爆炸
4. 最优：L5H15（5日低点，持有15日）

---

# Python文件名冲突排查

## 现象

执行 `python s01_equal_weight_daily.py` 时报错：
```
AttributeError: module 'platform' has no attribute 'python_implementation'
```

## 根因

`backtest_utils.py`（或其依赖 pandas）内部 `import platform` 加载了当前目录下的 `platform.py`（我们创建的平台生成脚本），而非 Python 标准库 `platform` 模块。

## 修复

```bash
mv platform.py gen_platform.py
```

## 预防

策略目录下的 `.py` 文件不要使用 Python 标准库模块名：
os, sys, time, math, json, csv, re, pathlib, platform, io, base64, subprocess, datetime, random, itertools, collections, typing, etc.
