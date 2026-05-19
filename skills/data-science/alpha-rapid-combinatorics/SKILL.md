---
name: alpha-rapid-combinatorics
title: Alpha 快速组合生成器 — 按既定方法生产 alpha，不评判质量
description: 不追求复杂逻辑，通过数据字段的排列组合 + 基础数学运算快速批量构建因子信号，8分钟内提交一批结果。你的工作是生产 alpha，不是筛选 alpha。
trigger: 研发策略|开发alpha|创建策略|快速因子|组合因子|批量研发
tags: [alpha, factor, combinators, quant, csi1000, generator]
---

# Alpha 快速组合生成器

## 核心理念（最重要，贯穿始终）

> **你就是个 alpha 工厂。拿字段 → 排列组合 → 写代码 → 输出文件名。回测由系统自动执行。效果好坏不是你的工作。**

核心原则：
- **效率优先**：快速写出代码，不要花时间分析表现
- **创新导向**：勇于尝试不同的字段组合，不要纠结"这个因子有没有意义"
- **不评判质量**：负收益、高换手、大回撤全部保留，系统自动过滤
- **只写代码，不跑回测**：写完策略文件保存到 strategies/ 即完成，回测由 APP 自动发起

**你的交付物 = 策略文件**。策略文件包含完整的 main()，被 Python 子进程调用执行回测。

## 项目数据规格

```
项目路径: C:\Users\Mayn\Desktop\a_stock_trade
数据: data/a_stock_kline_3y.npz（5203只股票 × 2426个交易日）
股票池: CSI1000（变量 POOL="csi1000"）
策略输出: strategies/aXXX_描述_频率.py
结果输出: results/<FOLDER>/（引擎自动保存 stats.csv + equity_curve.png）
引擎配置: backtest_utils.py 中 COMMISSION=0.0003, SLIPPAGE=0.001, STAMP_DUTY=0.0005, INIT_CAP=1亿
- buy_cost_rate = 佣金+滑点 = 0.0013（仅买入）
- sell_cost_rate = 佣金+滑点+印花税 = 0.0018（卖出含印花税）
核心用途: alpha 模式（float z-score）@ 周频
```

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

### 预制因子函数
```python
# 基础工具
zscore_rank(values, valid_mask=None)        → 横截面 rank 转 z-score [-3, 3]
decay_linear(x, t, d)                       → d 日线性衰减加权平均（整数窗口天数）★ 标准平滑方式
ret_n(close, t, n=20)                       → n 日区间收益率
vol_n(close, t, n=60)                       → n 日收益率波动率
amount(close, volume)                       → 成交额矩阵 = close × volume
amount_ratio(close, volume, t, n=20)        → 当日成交额 / n 日均成交额
price_position(close, t, n=60)              → 当前价在 n 日区间内的分位 [0,1]
ts_rank(x, t, n)                            → 时间序列 rank
ts_sum, ts_max, ts_min                      → 时间序列聚合
delta(x, n), delay(x, n)                    → 差分 / 延迟
correlation, covariance                     → 滚动相关系数
signedpower(x, n)                           → sign(x) × |x|ⁿ
scale(x)                                    → 缩放至 sum(|x|) = 1
rank_pct(x)                                 → 截面分位数排名

# 非流动性因子（已验证有效 ★）
amihud_illiq_fast(amt, close, t, n=20)      → Amihud 非流动性（需预计算 amt=close*volume）
alpha_amihud(close, volume, t, lookback)     → rank(amihud_Nd) → z-score（封装版）

# 价格位置 / 量价
alpha_vwap(close, volume, t)                 → VWAP 偏差因子
high_52week_ratio(close, t, n=252)           → 52 周高位比例
volume_confirmed_ret(close, volume, t)       → 成交量确认动量
alpha_volume_confirmed_momentum              → 封装版

# 隔夜 / 日内
overnight_ret(close, open_price, t)          → 隔夜收益
alpha_overnight                              → 封装版

# 高阶矩
skewness(close, t, n), kurtosis(close, t, n) → 偏度 / 峰度
alpha_skewness                               → 封装版

# 下行风险 / 收益质量
downside_vol(close, t, n)                    → 下行波动率
upside_potential(close, t, n)                → 上行潜力
alpha_gain_loss                              → 封装版

# 基本面因子（需 load_fundamentals 配合）
alpha_fund_roe, alpha_fund_eps               → ROE / EPS
alpha_fund_bp                                → 市净率倒数（价值因子）
alpha_fund_quality                           → 质量综合
alpha_fund_eps_growth_price                  → 动量+基本面复合
```

**注**：`alpha_smooth` 已废弃，统一使用 `decay_linear`。`alpha101_005` 等 Alpha101 示例因子也可用。

## 代码模板（全矩阵向量化模式 — 零 Python 循环）

**核心思想**：用 `*_batch` 函数一次性算完整个 `(N_stocks, N_days)` alpha 矩阵，全部用 numpy 矩阵运算，没有 `for t in range`。

```python
LABEL="A??? 策略名周频"; FOLDER="A???-策略名周频"; FREQ="weekly"; TAGS=["alpha","类别"]; POOL="csi1000"
import sys,os; sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
import numpy as np
from core.backtest_utils import *
from core.alpha_utils import (
    ret_n_batch, vol_n_batch, decay_linear_batch, zscore_rank_matrix,
    amihud_illiq_batch, amount_ratio_batch, forward_fill_alpha,
)
DECAY=20; STOCK_POOL="csi1000"

def generate_alpha(close, dates=None, volume=None, **kw):
    """
    一句话描述因子逻辑。
    全矩阵向量化计算：零 Python for 循环，全部 numpy 矩阵运算。
    """
    n_s, n_d = close.shape
    f = weekly_filter(dates)
    vld = close > 0.5
    amt = np.maximum(close * volume, 1) if volume is not None else np.ones((n_s, n_d))

    # ── 全矩阵批处理计算原始因子 ──
    # 用 *_batch 函数一次性算完 (N_s, N_d) 因子矩阵
    h = ...  # 例如: h = ret_n_batch(close, 20) + vol_n_batch(close, 60)

    # ── decay 平滑 + z-score（全矩阵操作） ──
    h_smooth = decay_linear_batch(h, DECAY)
    a = zscore_rank_matrix(h_smooth, vld)

    # ── 周频 forward-fill（向量化，无循环） ──
    a_weekly = np.where(f, a, -np.inf)
    a = forward_fill_alpha(a_weekly, f)

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

### 批处理函数速查

| 函数 | 计算内容 | 技术 |
|------|---------|------|
| `ret_n_batch(close, n)` | N 日收益率 (N_s, N_d) | 全量矩阵除法 |
| `vol_n_batch(close, n)` | 滚动波动率 | `sliding_window_view` |
| `amihud_illiq_batch(amt, close, n)` | Amihud 非流动性 | `sliding_window_view` |
| `amount_ratio_batch(close, vol, n)` | 成交额/均值 | `sliding_window_view` |
| `price_position_batch(close, n)` | 价格分位 [0,1] | `sliding_window_view` |
| `decay_linear_batch(x, d)` | 线性衰减加权MA | `sliding_window_view` |
| `zscore_rank_matrix(values, mask)` | 逐日 z-score | 向量化双 argsort |
| `forward_fill_alpha(a, f)` | 周频 forward-fill | 索引前向填充 |

## 快速组合模式（全矩阵批处理）

### 模式1：比率型因子
```python
ret20 = ret_n_batch(close, 20)
vol60 = vol_n_batch(close, 60)
h = ret20 / np.maximum(vol60, 1e-10)  # 动量/波动率 = 动量强度
```

### 模式2：复合因子（加法）
```python
amihud20 = amihud_illiq_batch(amt, close, 20)
vol60 = vol_n_batch(close, 60)
h = amihud20 + (-vol60)  # 非流动性 + 低波，经 decay+zscore 自动归一
```

### 模式3：交互因子（乘法）
```python
h = ret_n_batch(close, 20) * amount_ratio_batch(close, volume, 20)  # 动量 × 放量
```

### 模式4：大小盘杠铃（成交额作为规模代理）
```python
amt_t = close * volume if volume is not None else np.ones((n_s, n_d))
amt_z = zscore_rank_matrix(-amt_t, vld)  # 低成交额=高分
lv = -vol_n_batch(close, 60)
h = (amt_z**2) * lv  # 杠铃权重 × 因子
```

### 模式5：分位均衡（按成交额分组，组内 z-score）
```python
# 需要逐日 loop（无法全矩阵化），保留简洁版
amt_t = close * volume if volume is not None else np.ones((n_s, n_d))
a = np.full((n_s, n_d), -np.inf)
for t in range(20, n_d):
    vld_t = close[:, t] > 0.5
    amt_v = amt_t[:, t]; amt_v[~vld_t] = -np.inf
    pcts = np.percentile(amt_v[vld_t], np.linspace(10, 100, 10))
    dec = np.searchsorted(pcts, amt_v)
    sc = np.zeros(n_s)
    for d in range(10):
        m = (dec == d) & vld_t
        if m.sum() < 3: continue
        r = raw[m]; rk = np.argsort(np.argsort(r)).astype(float)
        sc[m] = (rk - rk.mean()) / (rk.std() + 1e-10)
    h[:, t] = sc
# 全矩阵 decay + zscore
h_s = decay_linear_batch(h, DECAY)
a_ret = zscore_rank_matrix(h_s, close > 0.5)
for t in range(1, n_d):
    if not f[t]: a_ret[:, t] = a_ret[:, t-1]
```

### 模式6：布尔信号转连续因子
```python
amt_t = close * volume if volume is not None else np.ones((n_s, n_d))
price_z = zscore_rank_matrix(-close, close > 0.5)  # 低价=高分
amount_z = zscore_rank_matrix(-amt_t, close > 0.5)   # 低成交额=高分
h = amount_z + price_z  # 等权复合（已归一化）
```

## ⚡ 性能要点（全矩阵批处理 + 矩阵预计算原则）

**使用 `*_batch` 函数替代 `for t in range` 循环，将回测从 15~30 秒降到 <2 秒。** 旧模式每天调用 `vol_n`/`amihud_illiq` 等滚动窗口函数，每次 O(window) 重复 2426 次 ≈ O(N_days×window)。批处理版本用 `sliding_window_view` 一次性算完，O(N_days)。

### 铁律：所有 alpha 策略禁止出现 `for t in range`

用户明确要求：**任何 `generate_alpha()` 函数中不得有 Python `for` 循环**。所有滚动窗口、z-score、decay 平滑、forward-fill 都必须用 `*_batch` 函数实现。

不可 batch 的操作（如分位分组、high-low 价差、嵌套循环、per-day 函数、基本面因子）也不写 for 循环——交给 `generate_signal` 模式的 s* 策略（只维护，不新增）和 per-day 保留的特殊 alpha 策略。

### 手动转换方法（禁止使用自动转换器）

将旧循环策略转为批处理时，**逐个文件检查，手动重写 `generate_alpha()` 函数**，不要写脚本批量转换。原因是每个策略的循环体内中间变量和组合逻辑各不相同，自动转换器会丢失中间变量定义。

转换步骤：
1. 确认策略只用到了可 batch 的函数（`vol_n`/`amihud_illiq`/`ret_n`/`amount_ratio`/`price_position` + `zscore_rank` + `decay_linear`）
2. 不可 batch 的情况（需保留 for 循环）：
   - 使用了 `delta`/`correlation`/`skewness`/`kurtosis` 等 per-day 函数
   - 使用了 `high-low` 价差的自定义滚动窗口
   - 分位分组（分10组组内zscore）
   - 嵌套循环（双重 for）
   - 基本面因子（`load_fundamentals`）
3. 转换模板：
   ```python
   # 旧：for t in range: h[:,t]=vol_n(close,t,60); decay_linear; zscore_rank
   # 新：
   h = vol_n_batch(close, 60)           # 一次性算出全矩阵
   a = zscore_rank_matrix(decay_linear_batch(h, DECAY), vld)  # 向量化平滑+zscore
   a = np.where(f, a, -np.inf)          # 非调仓日置零
   a = forward_fill_alpha(a, f)         # 向量化 forward-fill
   ```
4. 更新 import：去掉 `zscore_rank, decay_linear`，加上 `vol_n_batch, decay_linear_batch, zscore_rank_matrix, forward_fill_alpha`
5. 删除 `n_stocks,n_days=...; a=np.zeros(...); h=np.zeros(...)` 等不再需要的变量
6. 运行 `python strategies/aXXX.py` 验证结果是否与旧版一致

### 矩阵预计算原则

**`sliding_window_view` padding 陷阱（踩过坑）**：`sliding_window_view(x, window_shape=n)` 前必须 pad **n-1** 列（不是 n 列）。输出维度 = (pad + n_d) - n + 1 = n_d。pad n 列会多 1 列，导致 `ValueError: operands could not be broadcast together`。**正确代码**：`np.column_stack([np.zeros((n_s, n - 1)), x])`（而不是 `np.zeros((n_s, n))`）。

**`ret_n_batch` 无需 padding**：纯矩阵除法 `close[:, n:] / close[:, :-n] - 1`，前 n 天为 0。

### 紧凑风格模板（推荐，与旧策略风格一致）

```python
LABEL="A??? 策略名周频"; FOLDER="A???-策略名周频"; FREQ="weekly"; TAGS=["alpha","类别"]; POOL="csi1000"
import sys,os; sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
import numpy as np
from core.backtest_utils import *
from core.alpha_utils import vol_n_batch, decay_linear_batch, zscore_rank_matrix, forward_fill_alpha
DECAY=20; STOCK_POOL="csi1000"
def generate_alpha(close,dates=None,volume=None,**kw):
    n_s,n_d=close.shape; f=weekly_filter(dates); vld=close>0.5
    h=vol_n_batch(close,60)
    a=zscore_rank_matrix(decay_linear_batch(h,DECAY),vld)
    a=np.where(f,a,-np.inf); a=forward_fill_alpha(a,f)
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

## 研发流程（只写代码，回测由系统执行）

```
Step 1: 选 1~2 个字段 → 确定运算组合（1分钟）
Step 2: 套模板写代码，保存到 strategies/（2分钟）
Step 3: 输出创建的文件名
-------- 全程不超 8 分钟 --------
```

**不需要手动运行回测。** 写完策略文件保存即完成。APP 的自动研发按钮会检测新文件并自动执行回测。如果你发现自己在运行 `python strategies/aXXX.py`，停——那是系统该做的事。

## 命名规范

- 文件名: `aXXX_因子名_频率.py`（如 `a312_stable_illiq_weekly.py`）
- LABEL: `A312 因子说明频率`
- FOLDER: `A312-因子说明频率`
- TAGS: `["alpha", "类别", "频率"]`
- FREQ: `"weekly"` 或 `"monthly"`
- POOL: `"csi1000"`

## ⚡ 全矩阵向量化铁律（必须遵守）

### 1. 零 Python for 循环
所有 `generate_alpha()` 函数必须使用 `*_batch` 函数，禁止 `for t in range`。
详见 `references/vectorization-patterns.md`。

### 2. sliding_window_view padding = n-1
pad `n` 列 → 输出多一维 → broadcast 报错。始终 pad `n-1`。

### 3. forward-fill 用 forward_fill_alpha
不要手写 `for t in range(1,n_d): if not f[t]: a[:,t]=a[:,t-1]`。

### 4. zscore_rank 用 zscore_rank_matrix
不要手写 `for t in range(n_d): a[:,t]=zscore_rank(x[:,t],v)`。

## 已知无效因子方向（避免重复造轮子）

以下方向在 CSI1000 周频 10 年数据上已验证无效（年化≤1% 或绝对负收益），**不是不能尝试，但若时间有限请优先探索其他方向**：

- K线形态（实体强度、影线不对称、价格范围趋势）
- 彩票效应（MAX 因子及其变种）
- 动量加速度、动量纯度
- 趋势弯曲度、日内收盘偏移
- 残差动量、成交额加速度
- 量价确认突破
- 开收强度、放量动量
- 趋势效率、多周期效率
- 量价趋势一致（已验证多次无效）

## 有效因子参考（已跑出正收益，供组合参考）

| 因子方向 | 代表策略 | 典型逻辑 |
|---------|:--------:|---------|
| 非流动性溢价 🏆🏆🏆 | A212/A219/A215 | `rank(Amihud_Nd)` 买入难交易的股票 |
| 非流动性+低波 🏆 | A213 | `amihud / vol_60d` |
| 低波 🏆 | A202 | `-vol_60d` |
| VWAP 背离 🏆 | A208 | `Δvwap × -Δclose` |
| 低价+非流动性 | A280 | `zscore(-close)+zscore(Amihud)` |
| 杠铃低波 | A301 | `amount_z² × (-vol)` |
| 基本面复合 | A320 | `zscore(ROE+B/P+质量)` |
| 52 周高位 | A256 | `close / max(252d)` |

**注意**：这些只是参考，不是"只能做这些"。鼓励尝试全新方向——资金流、行业轮动、跨品种、事件驱动。

## 运行命令

```bash
# 跑单个策略
cd ~/Desktop/a_stock_trade && USERPROFILE="C:\\Users\\Mayn" PYTHONIOENCODING=utf-8 python strategies/aXXX.py

# 批量跑所有
cd ~/Desktop/a_stock_trade && USERPROFILE="C:\\Users\\Mayn" python batch_run.py
```

## ⚡ 已知陷阱与常见错误（必读）

### 陷阱1：forward_fill_alpha 的收敛问题

**错误用法（曾导致所有策略表现趋同）**：
```python
def forward_fill_alpha(a, f):
    a_safe = np.where(np.isfinite(a), a, -1e10)
    a_ff = np.maximum.accumulate(a_safe, axis=1)  # ← 对 α 值取累计最大值！
    return a_ff
```

**为什么致命**：z-score 是跨截面正态分布（约一半正、一半负），范围通常 -3~+3。`np.maximum.accumulate` 取的是**累计最大值**——一旦某股在某周获得 +3.5 的高 z-score，即使下周跌到 -2.5，因为 3.5 > -2.5，z-score 被卡在 +3.5 永不下降。几周后几乎所有股票都累积了历史最高 z-score → 全部大于 0 → 全被选中 → 所有策略选股和表现完全趋同。

**正确实现**：对**调仓日索引**做 forward-fill，不是对 α 值本身做 accumulate：
```python
def forward_fill_alpha(a, f):
    n_s, n_d = a.shape
    idx = np.where(f, np.arange(n_d), -1)     # 调仓日标记索引
    ff_idx = np.maximum.accumulate(idx)         # 向前传播最后一个调仓日索引
    return a[:, ff_idx]                          # 用索引取 α，非调仓日沿用最近调仓日
```

**验证方法**：跑两个逻辑差异大的策略（如 A212 非流动性 vs A202 低波），正常的策略间超额收益应相差 50%+ 而非挤在 1% 以内。

### 陷阱2：52周最高价的错误写法

**错误写法（1D广播错误）**：
```python
gl = close / np.maximum(close[:, -251], 0.5) - 1
# ValueError: operands could not be broadcast together (5203,2426) (5203,)
```
`close[:, -251]` 取的是第 -251 列（返回 1D），不能与 `close` 的 2D 矩阵广播。

**正确写法**：用 `sliding_window_view` 做滚动 251 天窗口取 nanmax：
```python
from numpy.lib.stride_tricks import sliding_window_view
pc = np.column_stack([np.full((n_s, 250), np.nan), close])
sw = sliding_window_view(pc, window_shape=251, axis=1)
max52 = np.nanmax(sw, axis=2)
gl = close / np.maximum(max52, 0.5) - 1
```
前 250 天的 52 周高位初始为 nan（自动忽略），第 251 天起有完整窗口。

### 陷阱3：close[:,-251] + 等价错误模式

任何 `close[:, -n]` 作为分母与 `close` 全矩阵运算都会触发 1D 广播错误。正确处理滚动窗口统计量的模式：
- 滚动均值 → `sliding_window_view` + `nanmean`
- 滚动最大值 → `sliding_window_view` + `nanmax`
- 滚动波动率 → `vol_n_batch`（已封装好）

### 陷阱4：回测结果首月异常高收益（128%+）→ 引擎 PV 跟踪错误

**现象**：某策略首月 10 个交易日回报 128%，每日 5%~16%，但持仓股票的实际加权收益仅 ±2% 或 0%。首月后收益曲线急剧变平。

**根因**：两个叠加 bug：
1. **alpha_mode 非调仓日每日再平衡**：引擎每天按 `alloc_base * w / close[t]` 重建仓位
2. **`max_position_pct` 双重计费**：`has_cash += excess_val` 与 `has_cash += net_pnl` 重复计算限仓释放现金

**诊断方法**：
1. 对比 CSV daily_return 与持仓加权实际收益
2. 检查位置矩阵 days 2~10 是否完全相同（`pos[:, t].sum()`）
3. 检查 `shares[t] == shares[t-1]` — 如果不等说明每日再平衡未被跳过
4. 详见 `references/backtest-pv-anomalies.md`

**预防**：当回测结果的**首月收益远超合理水平**（如 A 股单日 >10%、首月 >30%），优先怀疑引擎 PV 跟踪问题，而非判定策略有效。

**完整修复记录**（3 个 commit, 2026-05-18）:

| # | 问题 | 效果 |
|---|------|------|
| 1 | 比较 raw signal 替代选股集 | 非调仓日正确跳过再平衡 |
| 2 | 移除 `excess_val` 双重计费 | 消除限仓带来的虚假 P&L |
| 3 | 涨跌停买卖不对称修正 | 涨停可卖、跌停可买 |

## References

- `references/vectorized-batch-api.md` — 全矩阵批处理函数完整 API 文档
- `references/signal-to-alpha-migration.md` — s* 信号策略转 alpha 模式迁移指南
- `references/backtest-engine-modifications.md` — 引擎修改记录（印花税、基准修复等）
- `references/backtest-pv-anomalies.md` — 回测 PV 异常诊断指南（alpha_mode 首月幻觉修复）
- `references/benchmark-survivorship-bias.md` — 中证1000基准幸存者偏差修复
- `references/auto-dev-two-phase.md` — 自动研发按钮两阶段架构
- `references/retail-behavior-alpha.md` — 散户行为逆向量价因子（追涨/恐慌反向）
- `references/longhu-data-structure.md` — 龙虎榜数据结构和akshare接口（用于构建资金流/机构vs散户因子）
