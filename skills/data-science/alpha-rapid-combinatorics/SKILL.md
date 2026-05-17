---
name: alpha-rapid-combinatorics
title: Alpha策略快速组合研发 — 数学排列组合 + 快速批量迭代
description: 不追求复杂逻辑，通过数据字段的排列组合 + 基础数学运算快速批量构建因子信号，8分钟内提交一批结果
trigger: 研发策略|开发alpha|创建策略|快速因子|组合因子|批量研发
tags: [alpha, factor, combinatorics, quant, csi1000]
---

# Alpha 快速组合研发方法论

## 核心理念

> **不要构造复杂逻辑。把数据字段当乐高块，用基础数学运算做排列组合，快速生成 → 回测 → 筛选。全部用 Alpha 模式（`generate_alpha()` 返回 float z-score），不用布尔信号。使用 `amihud_illiq_fast(amt, close, t, n)` 代替 `amihud_illiq(close, volume, t, n)` 避免循环内矩阵重复计算。**

研发节奏：每批 1~3 个策略，8 分钟超时，全部保留不做硬性过滤（只剩选股 <10 只或负收益才删）

## 可用数据字段与因子函数（从 alpha_utils 导入）

### 原生字段
```
close     收盘价   (N_stocks, N_days)   shape[0]=5203, shape[1]=2426
open      开盘价
high      最高价
low       最低价
volume    成交量
dates     日期数组 (N_days,)
```

### 预制因子函数（alpha_utils.py 中已实现）
```python
zscore_rank(values, valid_mask=None)      → 横截面 rank 转 z-score [-3, 3]
decay_linear(x, t, d)                     → d 日线性衰减加权平均
amihud_illiq_fast(amt, close, t, n=20)    → Amihud 非流动性（需预计算 amt=close*volume）
vol_n(close, t, n=60)                     → n 日收益率波动率
ret_n(close, t, n=20)                     → n 日区间收益率
amount(close, volume)                     → 成交额矩阵 = close × volume
amount_ratio(close, volume, t, n=20)      → 当日成交额 / n 日均成交额
price_position(close, t, n=60)            → 当前价在 n 日区间内的分位 [0,1]
alpha_amihud(close, volume, t, lookback)  → rank(amihud_Nd) → z-score（封装版）
alpha_vwap(close, volume, t)              → VWAP 偏差因子
high_52week_ratio(close, t, n=252)        → 52 周高位比例
volume_confirmed_ret(close, volume, t)    → 成交量确认动量
```

### 预制常量（backtest_utils.py）
```python
COMMISSION = 0.0003     # 万三
SLIPPAGE = 0.001        # 0.1% 滑点
INIT_CAP = 100_000_000  # 1 亿固定基准
MIN_COVERAGE = 0.0      # 不限制，CSV 含全部 5203 只 A 股
BACKTEST_START = "2016-05-17"  # 10 年回测起点
```

## 基础数学运算清单（优先使用）

### 单字段
```
-值          → 取负（反转方向）
abs(值)      → 绝对值
```

### 双字段
```
A / B        → 比率
A - B        → 差值
A * B        → 交互项（乘法复合）
A + B        → 等权复合（各自原始值相加，经 decay+zscore 后自动归一）
```

### 时序（手写无需导入）
```python
np.nanmean(x[:, start:t+1], axis=1)   → N 日均值
np.nanstd(x[:, start:t+1], axis=1)    → N 日标准差
x[:, t] / x[:, t-n] - 1               → N 日收益率
np.nanmean(x[:, t-4:t+1], axis=1)     → 5 日均值
np.nanmean(x[:, max(0,t-19):t+1], axis=1) → 20 日均值
```

## Alpha 模式标准框架（唯一模板）

```python
LABEL="A??? 策略名周频"; FOLDER="A???-策略名周频"; FREQ="weekly"; TAGS=["alpha","tag1","tag2"]; POOL="csi1000"
import sys,os; sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
import numpy as np
from core.backtest_utils import *
from core.alpha_utils import zscore_rank, decay_linear  # + 其他所需函数
DECAY=20; STOCK_POOL="csi1000"
def generate_alpha(close,dates=None,volume=None,**kw):
    """一句话描述因子逻辑"""
    n_s,n_d=close.shape; a=np.zeros((n_s,n_d)); f=weekly_filter(dates); h=np.zeros((n_s,n_d))
    for t in range(20,n_d):  # 起始值=所需最长的 lookback
        vld=close[:,t]>0.5
        # ← 因子计算
        h[:,t]=...
        if not f[t]:
            if t>0: a[:,t]=a[:,t-1]
            continue
        s=decay_linear(h,t,DECAY); v=close[:,t]>0.5; a[:,t]=zscore_rank(s,v)
    return a
def main():
    l=LABEL; print("="*60); print(f"  {l}"); print("="*60)
    ld=DataLoader().load(); c=ld.close; d=ld.dates
    p=stock_pool_mask(ld.codes,STOCK_POOL); v=(c>0.5)&p[:,None]
    print(f"[生成] {l}..."); al=generate_alpha(c,d,volume=ld.volume); al[~v]=-np.inf; print(f"  日均选股: {(al>0).sum(axis=0).mean():.0f}")
    r=TradingRules(c,ld.open_price,ld.volume,ld.codes,ld.names_arr,ld.is_st,ld.exchange)
    eng=BacktestEngine(COMMISSION,SLIPPAGE,alpha_mode=True); eng.run(c,al,d,trading_rules=r,valid=v)
    print_stats(eng.stats); Visualizer.print_trades(eng); Visualizer.plot_and_save(eng,os.path.join(RESULTS_BASE,FOLDER),l); print("="*60)
if __name__=="__main__": main()
```

## 快速组合模式（Alpha 模式）

### 模式1：比率型因子
```python
amt5=np.nanmean(close[:,t-4:t+1]*volume[:,t-4:t+1],axis=1)
amt20=np.nanmean(close[:,max(0,t-19):t+1]*volume[:,max(0,t-19):t+1],axis=1)
h[:,t]=amt5/np.maximum(amt20,1e-8)
```

### 模式2：复合因子（加法）
```python
from core.alpha_utils import zscore_rank, decay_linear, amihud_illiq_fast
amt=np.maximum(close*volume,1) if volume is not None else np.ones((n_s,n_d))  # 预计算一次
for t in range(20,n_d):
    vld=close[:,t]>0.5
    # 两个因子直接相加（原始值），经 decay_linear+zscore_rank 后自动归一化
    f1 = ...  # 因子1原始值
    f2 = amihud_illiq_fast(amt, close, t, 20)  # 因子2
    h[:,t] = f1 + f2  # 等权复合
```

### 模式3：交互因子（乘法）
```python
h[:,t] = (-cv) * mom  # 稳定 × 动量 → 乘积交互
```

### 模式4：大小盘杠铃（成交额作为规模代理）
```python
az = zscore_rank(close[:,t]*volume[:,t], vld)  # 成交额 z-score
h[:,t] = (az**2) * target_factor  # 杠铃权重 × 因子
```

### 模式5：分位均衡（按成交额分10组，组内分别 z-score）
```python
amt=close[:,t]*volume[:,t]; amt[~vld]=-np.inf
pcts=np.percentile(amt[vld], np.linspace(10,100,10))
dec=np.searchsorted(pcts, amt)  # 0-9
sc=np.zeros(n_s)
for d in range(10):
    m=(dec==d)&vld
    if m.sum()<3: continue
    r=raw[m]; rk=np.argsort(np.argsort(r)).astype(float)
    sc[m]=(rk-rk.mean())/(rk.std()+1e-10)
h[:,t]=sc
```

## ⚡ 性能要点（矩阵外提原则）

**循环内绝对不要重复计算 `close * volume`（5203×2426）。** 这是最常见的性能灾难。

```python
# ❌ 错误：每次迭代算全量矩阵
for t in range(2426):
    amt = close[:,t] * volume[:,t]  # O(1) 还好
    amihud = amihud_illiq(close, volume, t, 20)  # ❌ 内部又算 close*volume 全矩阵！

# ✅ 正确：预计算 amt 一次，传进去
amt = np.maximum(close * volume, 1)  # 循环前算一次
for t in range(2426):
    amihud = amihud_illiq_fast(amt, close, t, 20)  # 只切片，不重复乘
```

同样适用于任何用到 `close * volume` 的全矩阵运算。不同 lookback 长度的策略各自写一个循环就够了——100 个策略各自循环，也比 1 个策略循环里算 2426 次矩阵乘法快得多。

## 🛡️ 反过拟合理念：现金按中证1000指数计收益

**问题：** 策略可以故意在下跌日降低仓位（如选股少、信号弱），躲避大跌、制造虚假的"稳定收益"。

**解决：** `BacktestEngine` 新增 `index_returns` 参数。提供中证1000日收益率数组后，引擎自动将每日未投入股票的现金部分（`1亿 - 股票市值`）按指数收益率计算，确保总名义仓位始终是1亿。

```
每日真实收益 = 股票部分收益 × (股票市值/1亿) + 中证1000收益 × (1 - 股票市值/1亿)
```

引擎会自动从 akshare 下载中证1000指数数据（缓存，`_compute_benchmark` 复用）。策略代码无需修改。

## 研发流程（8分钟/批）

```
1. 选定 1~3 个字段 → 确定运算 → 写好代码（3分钟）
2. 本地回测运行（2分钟）
3. 检查结果：选股>10只、正收益（2分钟）
4. 如果OK保留，否则删掉（1分钟）
```

## 命名规范

- 文件名: `aXXX_描述_频率.py`（如 `a312_stable_illiq_weekly.py`）
- LABEL: `A312 稳定非流动组合周频`
- FOLDER: `A312-稳定非流动组合周频`

## 换手率控制

- 默认 DECAY=20（高平滑，低换手）
- 换手率铁律 < 10%
- 调高 DECAY 至上限 20 仍超 10% → 因子噪声太大，直接换因子
- 换手率 = 调仓金额 / 固定基准（日换手）

## 失败策略处理

- 选股 < 10 只 → 直接删除
- 负收益 → 直接删除
- 换手率 > 10%（DECAY=20 后仍超）→ 因子噪声大，删除
- 其他结果全部保留，不做硬性指标过滤
