---
name: a-share-strategy-development
description: "A股量化策略全流程开发。基于backtest_utils共享模块，每个策略只需编写generate_signal()函数返回bool信号矩阵。"
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [a-share, backtest, strategy, quant, python]
    related_skills: [test-driven-development, systematic-debugging]
---

# A股量化策略开发（Alpha模式）

## 研发铁律

### 统一使用 Alpha 模式
所有新策略研发**必须**使用 alpha 模式（float 得分矩阵），不得再使用旧的 bool 信号模式。
不再编写 `generate_signal()` 函数，统一用 `generate_alpha()` 返回 z-score 归一化的得分矩阵。

### ⚡ 研发速度铁律
只要有了因子思路，直接写代码、直接跑回测，**不要**先写计划再问再执行。流程：
1. 想出一个 Alpha101 风格公式（一行数学表达式）
2. 用 `alpha_utils` 原语写成代码（不超过 5 行逻辑）
3. 直接跑 `python strategies/aXXX.py`
4. 看年化/回撤/换手三项指标裁决
5. 下一个

每批 3-5 个策略一起写，一起跑，不一个个来。中间不询问、不汇报、不写文档。
失败的策略直接删文件+结果目录，只汇报最终存活列表。

### 避旧创新
每次研发新策略前，必须先回顾已有策略列表，确保新思路**不重复、不相似、低相关**。优先探索完全不同的因子：资金流、基本面、宏观、事件驱动、行业轮动、跨品种。

**已有策略库速查（Alpha模式 A200+ / 信号模式 S*）**：
| 类别 | 策略 | 核心逻辑 |
|------|------|----------|
| **Alpha - 低波** 🏆 | **A202** | **-rank(std_60d) 年化12.31%** |
| Alpha - 动量 | A200 | rank(ret_20d) 年化7.31% |
| Alpha - 反转 | A201 | -rank(ret_5d) 年化7.49% |
| Alpha - 量价动量 | A203 | rank(ret×amt_ratio) 年化7.75% |
| 基线 | S01/S02 | 等权 |
| 低价 | S66/S67/S78/S92 | 价格分位+排除极端/周频/月频 |
| 动量+低波 | S76/S81/S82/S91 | 双频段/分层/低波动过滤 |
| 等权增强 | S93/S121/S122/S124 | 双剔除/低动量剔除/流动性中段 |

### 自主迭代
全自动化、自主决策，不询问。流程：写一批(3-5个)→**逐个跑**（`python strategies/aXXX.py`，不动 `_summary.csv`）→自主裁决(年化>15%且夏普>0.4保留，负收益/选股<10只删)→汇报成果。

**重要**：所有新策略使用 alpha 模式写作。策略文件命名统一 `aXXX_因子名_freq.py`（如 `a204_lowvol_momentum_weekly.py`），`generate_alpha()` 返回 float 得分矩阵，引擎调用 `BacktestEngine(alpha_mode=True)`。

### 灵感来源
1. 券商金工研报(github.com/hugo2046/QuantsPlaybook)
2. 学术论文(SSRN/arXiv/IEEE)
3. 量化社区(聚宽/米筐/BigQuant)
4. 海外论坛(QuantConnect/Reddit r/algotrading)
5. 经典技术指标改造(A股验证，多数失效)

## 核心经验

### 频率选择（最关键发现）
| 频率 | 特点 | 推荐场景 |
|------|------|----------|
| **周频** 🏆 | 换手3-20%，成本可控 | 绝大多数策略 |
| **月频** | 换手2-3%，收益略低 | 低成本稳健型 |
| **日频** ❌ | 换手50-87%，成本吃掉alpha | 仅限极少数宽基策略 |

### 10年回测排名 (2016-05~2026-05, 复利年化, 中证1000等权周频基准)
**注意**：年化收益率统一用复利法 `(1+total_ret)^(1/years)-1` 计算，不与固定基准法的单利年化混用。超额IR统一使用 `策略年化 - 基准年化`（年化相减）。

| 排名 | 策略 | 年化 | 等权IR | 中证IR | 回撤 | 换手 |
|:----:|------|:---:|:-----:|:-----:|:----:|:---:|
| 1 | S110 低价均线支撑周频 | 12.56% | 0.08 | 0.78 | -31.79% | 13.53% |
| 2 | S125 小盘均线支撑周频 | 12.27% | 0.05 | 0.68 | -30.62% | 4.99% |
| 3 | S127 小盘低价周频 | 12.15% | 0.05 | 0.74 | -30.13% | 2.27% |
| 4 | S112 温和动量安全性月频 | 12.01% | 0.03 | 0.72 | -38.28% | 1.31% |
| 5 | S67 低价股周频 | 11.95% | 0.03 | 0.76 | -30.35% | 3.60% |
| 6 | S78 低价股月频 | 11.63% | 0.01 | 0.75 | -31.41% | 2.45% |
| 7 | S66 低价排除极端涨跌 | 11.08% | -0.04 | 0.74 | -34.07% | 9.25% |
| 8 | S124 流动性适中选股周频 | 10.89% | -0.06 | 0.74 | -39.88% | 5.11% |
| 9 | S109 低价流动性中段周频 | 10.83% | -0.06 | 0.74 | -36.62% | 5.55% |
| 10 | S100 低价排除放量周频 | 10.79% | -0.07 | 0.77 | -37.51% | 7.35% |
| 11 | S118 低价深度反转周频 | 10.71% | -0.07 | 0.67 | -36.27% | 4.82% |
| 12 | S105 低价正向动量月频 | 10.56% | -0.09 | 0.70 | -44.22% | 5.09% |
| — | (等权周频基准) | ~11.55% | — | — | — | — |

### ⚠️ app.pyw 常见陷阱（汇总）
### ⚠️ 策略扫描坑（2026-05-16修复）
`app.pyw` 的 `scan_strategies()` 和 `core/platform.py` 的 `discover()` 都必须直接扫 `strategies/*.py`，**禁止按文件名前缀过滤**（如 `s[0-9]*` 或 `a[0-9]*`）。否则新前缀命名的策略会被忽略。

正确写法：
```python
strategy_files = sorted(glob.glob(os.path.join(STRATEGIES_DIR, "*.py")))
strategy_files = [f for f in strategy_files if os.path.basename(f) != "__init__.py"]
```

### ⚠️ platform.py 架构（2026-05-16重写）
`run_one()` 使用 `subprocess.run([sys.executable, filepath])` 以子进程方式运行每个策略，不再用 `importlib` 动态导入。原因：
- 避免 `core/platform.py` 与 Python 内置 `platform` 模块的命名冲突
- 支持信号模式和 alpha 模式混合（子进程各自处理自己的 import）
- 隔离不同策略间的 import 污染

`run()` 使用 `ThreadPoolExecutor(max_workers=4)` 并行执行。汇总 CSV 使用 `concat` + `drop_duplicates` 追加去重，不再覆盖写入。

### `_read_meta` 紧凑格式兼容
`platform.py` 的 `_read_meta()` 用 `re.split(r'[;\n]', content)` 拆分行内分号分隔的多条赋值，以支持紧凑格式：
```python
LABEL="A204 因子名"; FOLDER="A204-因子名"; FREQ="weekly"; TAGS=["alpha"]; POOL="csi1000"
```
`_parse_label` 在 `app.pyw` 和旧的 `run_all.py` 中也必须同样处理。

### ⚠️ app.pyw `_parse_label` 大小写坑
策略文件的元数据变量名不统一：旧策略用 `label=`/`folder=`（小写，模块级），新策略用 `LABEL=`/`FOLDER=`（大写）。`_parse_label` 若只匹配大写，新旧策略读到文件名回退；若只匹配小写，新策略读不到。必须分两步：
1. 先匹配大写 LABEL/FOLDER
2. 无大写时回退到文件名（与 platform.py 的 `_read_meta` 一致——它只读大写，setdefault fallback 到文件名）
**不要**读小写 `label`/`folder` 作为 folder 值，因为 platform.py 的 `_read_meta` 不读小写，旧策略的结果目录名是文件名（如 `s01_equal_weight_daily`），不是小写 folder 的值。读小写会导致目录名不匹配，app显示为空。

```python
# ✅ 正确：只读大写，无大写回退文件名
m = re.search(r'LABEL\s*=\s*["\'](.+?)["\']', content)
m2 = re.search(r'FOLDER\s*=\s*["\'](.+?)["\']', content)
folder = m2.group(1) if m2 else os.path.splitext(os.path.basename(src_path))[0]
```

### 双超额夏普（2026-05-16新增）
每个策略同时输出两套超额指标，在app.pyw列表和CSV中都有：

| 列名 | 含义 | stats key | 比较对象 |
|:----|:----|:---------|:--------|
| **等权夏普** | 策略 vs 等权周频组合的信息比 | `信息比率` | CSI1000等权周频组合(+195%总收益) |
| **中证夏普** | 策略 vs 中证1000指数的信息比 | `中证信息比` | 中证1000指数(+30~50%总收益) |

中证IR远高于等权IR，因为等权组合大幅跑赢了指数。中证指数数据通过akshare下载。年化超额用`策略年化-基准年化`计算（复利年化相减，不是总点数差/年数）。

### 小盘因子研究（2026-05-16）
**代理变量**：因无市值数据，用成交额(close×volume)的后30%分位作为小盘股代理（在CSI1000内选成交额最低的股票）。

**发现**：在CSI1000（中盘股为主）内，加成交额筛选的效果有限。S125(小盘均线支撑)与S110(原版)收益几乎持平(21.67% vs 22.50%)。S127(小盘低价)比S67(原版低价)微幅增强(21.34% vs 20.77%)。**结论：CSI1000本身已经是中盘，内部的"小盘"分化不够大，成交额代理效果弱。真正的α需要全市场小盘股。**

**保留策略**：
| 策略 | 年化 | 回撤 | 说明 |
|:----|:---:|:----:|:----:|
| **S125 小盘均线支撑周频** | 21.67% | -30.62% | 成交额30%+低价后50%+站上MA20 |
| **S127 小盘低价周频** | 21.34% | -30.13% | 成交额30%+价格后30%分位 |

**成交额计算**：`amt = close * volume`（volume来自`loader.volume`，在`generate_signal(close, dates, volume=loader.volume)`中传入）。注意volume是float64，成交额量级约10^7~10^9。在计算分位数时建议用`np.nanpercentile`，空安全。`generate_signal`签名应加`volume=None, **kw`参数以避免调用出错。

### ⚠️ 回测引擎陷阱 list
- **has_cash 变负** → 导致回撤超100%。修复：分配基准按实际可用资金。
- **has_cash=0.0 + max_position_pct** → 现金消失导致断崖下跌。修复：保留剩余现金，pv含现金。
- **再平衡成本未扣除** → 收益虚高。修复：加 `has_cash -= cost`。
- **t=0 缩进错误** → shares/mv/cost在 `if n_buy>0:` 外执行。修复：整个部署块缩进到if内。
- **成本回收效应** → 成本在买入日从pv扣除，但次日pv按全市场价重算，成本"回来"了。修复：`has_cash = available - mv - cost`（成本嵌入has_cash），`pv[t] = has_cash + mv`。
- **超额用固定基准NAV比百分比基准** → pv>1亿时放大超额。修复：超额统一用百分比收益 `pct_ret[t] = pv[t]/pv[t-1]-1` 计算 `excess_nav = 1 + strat_pct_nav - bm_nav`。
- 详见 `references/negative-cash-fix-2026-05.md`。

### 研发检查清单
- [ ] 使用 alpha 模式（`generate_alpha()` + `BacktestEngine(alpha_mode=True)`）
- [ ] 使用 `DECAY` 平滑（正整数窗口天数，默认 5）
- [ ] 日均选股 ≥ 30只（否则不稳定）
- [ ] 年化 > 5%（否则无效）
- [ ] 回撤 > -50%（否则风险过高）
- [ ] 换手 < 15%（decay 控制），检验：`日均换手 < 15%`
- [ ] 与已有策略逻辑不重复
- [ ] 超额为正（跑赢等权周频基准）才有保留价值

### 工具命令
```bash
# ✅ 研发新策略：直接跑单个文件（不碰 _summary.csv）
USERPROFILE="C:\Users\Mayn" python strategies/aXXX.py

# ✅ 全量汇总（包括 s* 旧信号 + a* alpha 策略，4线程并行，子进程隔离）
USERPROFILE="C:\Users\Mayn" python -m core.platform run

# ✅ 查排名（只读，不跑策略），会自动跳过失败的策略
python -m core.platform rank

# ⚠️ 策略文件命名规则：aXXX_因子名_freq.py（alpha模式）
#   sXXX_因子名_freq.py（旧信号模式，只维护不新增）

### Alpha 模式研发（2026-05-16新增）

引擎新增 `alpha_mode=True` 支持 float 得分矩阵替代 bool 信号。与原有信号模式的区别：

| 维度 | 信号模式（默认） | Alpha 模式 |
|:----|:--------------|:--------:|
| 输入 | bool 矩阵 (选/不选) | float 矩阵（得分，>0选中） |
| 选股 | `signal > 0.5` | `score > 0`（z-score均值0以上） |
| 权重 | 等权分配 | 按得分比例分配（得分越高权重越大） |
| 策略函数 | `generate_signal()` | `generate_alpha()` |

**通用工具模块** `core/alpha_utils.py` — 所有 alpha 策略优先调用，不再重复造轮子：

```python
from core.alpha_utils import (
    zscore_rank,        # 截面 rank → z-score 归一化  ★ 最终输出格式
    decay_linear,       # 线性加权移动平均（平滑因子值，整数窗口天数）★ 标准平滑方式
    ret_n,              # N日收益率
    vol_n,              # N日波动率
    amount_ratio,       # 成交额比例
    price_position,     # 价格在区间中的分位
    rolling_max_dd,     # 滚动最大回撤
    ts_rank, ts_sum, ts_max, ts_min,  # 时间序列算子
    delta, delay,                          # 差分/延迟
    correlation, covariance,               # 滚动相关系数
    signedpower, scale, rank_pct,          # 截面/数学运算
    alpha101_001, alpha101_003, alpha101_012,  # Alpha101 示例因子
)
# 注意：alpha_smooth 已废弃，统一使用 decay_linear
```

**策略文件模板（紧凑风格 — 优先使用）**：
```python
LABEL="A209 因子说明频率"; FOLDER="A209-因子说明频率"; FREQ="weekly"; TAGS=["alpha","类别"]; POOL="csi1000"
import sys,os; sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
import numpy as np
from core.backtest_utils import *
from core.alpha_utils import zscore_rank, decay_linear, ts_rank, delta

DECAY=5; STOCK_POOL="csi1000"  # DECAY=整数窗口天数！

def generate_alpha(close,dates=None,volume=None,**kw):
    n_stocks,n_days=close.shape; alpha=np.zeros((n_stocks,n_days)); first=weekly_filter(dates)
    hist=np.zeros((n_stocks,n_days))  # 存原始因子值
    for t in range(n_days):
        # ★ 每天算原始因子值
        hist[:,t] = ts_rank(close,t,10) * delta(close,t,3)
        if not first[t]:
            if t>0: alpha[:,t]=alpha[:,t-1]
            continue
        # ★ decay_linear 平滑后排名
        raw=decay_linear(hist,t,DECAY)
        valid=close[:,t]>0.5; alpha[:,t]=zscore_rank(raw,valid)
    return alpha

def main():
    ...  # 标准 main()
if __name__=="__main__": main()
```

**引擎调用**：
```python
engine = BacktestEngine(commission=COMMISSION, slippage=SLIPPAGE,
                        alpha_mode=True)
engine.run(close, alpha_scores, dates, trading_rules=rules, valid=valid)
```

**引擎内部逻辑**（`core/backtest_utils.py`）：
- `_alpha_to_weights(scores, valid_mask, top_pct=1.0)` — 将得分转为选股 + 权重
- `score > 0` → 选中
- 权重 = 正分归一化（分数越高权重越大）
- `alpha_top_pct` 参数可限制仅取前N%

**已有Alpha策略（CSI1000周频，decay_linear=5）**：
| 策略 | 因子 | 年化 | 回撤 | 换手 |
|:----|:----|:---:|:---:|:---:|
| A208 VWAP背离Alpha 🏆 |  Δvwap×-Δclose | 14.50% | -23.20% | 19.36% |
| A202 低波Alpha 🏆 | -vol_60d | 12.71% | -18.05% | 4.04% |
| A201 反转Alpha | -ret_5d | — | — | — |
| A203 成交额动量 | ret×amt_ratio | — | — | — |
| A200 动量Alpha | ret_20d | — | — | — |

**`decay_linear` 用法**：`decay_linear(hist, t, window)` 对 `hist` 第 t 天往前 `window` 天的数据做线性加权平均，权重 `1,2,...,window`（今天权重最高）。用在 `generate_alpha` 中平滑原始因子值后再 `zscore_rank`，降低噪声减少换手。
- `DECAY=5`：5天窗口（默认）
- 窗口太小(<3)则平滑不足；太大(>20)则信号滞后
- 不需要再维护 `alpha_smooth`，已被 `decay_linear` 替代

### app.pyw `_parse_label` 大小写坑\n见 `references/app-parse-label-regex-2026-05.md`。新旧策略文件的元数据变量名不同（旧用 `label=`/`folder=` 小写，新用 `LABEL=`/`FOLDER=` 大写），`_parse_label` 的正则必须同时匹配两者，否则app扫不到结果。

### 图表布局（Visualizer.plot_and_save）
3个子图，暗色主题，尺寸 14×10：

| 子图 | 高度比 | 内容 | 颜色 |
|:---:|:------:|------|:----:|
| 1 | 3 | 策略净值 + 等权周频基准(虚线) + 等权超额(点线) + 持仓数(右Y轴柱状) | 蓝/黄/绿/紫 |
| 2 | 1 | **中证1000超额**曲线（差值法，含最大回撤标注） | 橙(#f97316) |
| 3 | 1 | **等权超额**曲线（差值法，含超额回撤标注） | 绿 |

- 子图2替代了原来的回撤折线图（已移除）
- 所有超额均使用差值法 `1 + nav - benchmark`，而非比值法
- 中证1000指数数据通过akshare下载，失败时显示"数据不可用"

### 比较基准（引擎自动计算）
**`BacktestEngine.run()` 末尾自动调用 `_compute_benchmark(close, dates)`**，不再需要手动调用 `IndexLoader.load()` + `set_benchmark()`。

- 基准：**等权周频组合（中证1000股票池）**（CSI1000成分股 + close>0.5，每周等权再平衡）
- 超额计算：**差值法** `excess_nav = 1 + nav - bm_nav`（不再是比值法 `nav / aligned`）\n- 年化超额：`strategy_ann - benchmark_ann`（两端都用复利年化，不是总点数差/年数）
- 等权基准2016-05~2026-05总收益约+195.18%（CSI1000池，年化11.55%），详情见 `references/equal-weight-benchmark-2026-05.md`\n- 同时自动计算**中证1000指数超额**：`self.csi1000_excess_nav = 1 + nav - csi1000_index`（用于图表子图2，通过akshare下载指数数据）
- 不再单独依赖 `IndexLoader` 类，所有53个策略文件已清除 `IndexLoader` 导入和 `set_benchmark()` 调用
- `set_benchmark()` 保留用于手动覆盖，但一般不需要
- 细节见 `references/equal-weight-benchmark-2026-05.md`

```python
# ❌ 旧模式（已废弃）
idx_nav, idx_dates = IndexLoader.load(trade_dates=dates)
engine = BacktestEngine(...)
engine.run(...)
engine.set_benchmark(idx_nav, idx_dates)

# ✅ 新模式（引擎自动完成）
engine = BacktestEngine(...)
engine.run(close, signal, dates, trading_rules=rules, valid=valid)
# benchmark统计、超额曲线自动生成
```

### 技术细节
- `BACKTEST_START = "2016-05-17"`（10年），修改在 `core/backtest_utils.py` 全局配置
- 数据范围 2016-05-17 ~ 2026-05-15，2426个交易日，2930只股票（经清洗）
- CSI1000成分股覆盖：2016年399只 → 2026年775只
- 核心引擎在 `core/backtest_utils.py`：`BacktestEngine.run()` 自动调用 `_compute_benchmark()` 计算等权周频基准+超额
- 超额净值 = 差值法：`1 + strat_pct_nav - benchmark_nav`（百分比收益，非固定基准，防止pv>1亿时放大）
- 策略不再需要导入 `IndexLoader` 或调用 `set_benchmark()` — 引擎自动处理
- `set_benchmark()` 保留用于手动覆盖基准场景
- `BACKTEST_START` 全局变量控制回测起始日期
- 策略文件一律以 `a` 前缀命名：`a204_my_factor_weekly.py`
- 策略文件加 `LABEL/FOLDER/FREQ/TAGS/POOL` 元数据
  - LABEL = "A204 因子描述频率"  (A开头标识alpha模式)
  - FOLDER = "A204-因子描述频率"  (目录名与LABEL对应)
  - FREQ = "weekly" 或 "monthly"
  - TAGS = ["alpha", "因子类别", "频率"]
  - POOL = "csi1000"
- `core/platform.py` 已清理 `IndexLoader` 导入，支持标签筛选
- `weekly_filter` / `monthly_filter` 在 core/backtest_utils.py
- Windows路径避开 `<>:"/\|?*` 字符
- 用户名 `Mayn`，`USERPROFILE` 环境变量经常被污染
- Windows 平台要点见 `references/windows-pitfalls-2026-05.md`
- 涨跌停用0.5%容差(float32精度问题)\n- 固定基准(1亿) + 复利年化计算 `(1+total_ret)^(1/years)-1`\n- 用户是Windows中文用户，USERPROFILE环境变量被污染，需 `USERPROFILE="C:\\Users\\Mayn"` 前缀运行

### ⚠️ 回测引擎陷阱：has_cash 管理（共7个bug已修复）

**触发条件**：固定基准法（fixed_base=1亿）下，持仓股票持续下跌时再平衡，引擎仍按满额1亿重新分配，`net_pnl = cur_pos - new_pos` 为负 → `has_cash` 变负 → 清仓后 NAV < 0 → 回撤 >100%。

**全部修复**（2026-05-16，详见 `references/negative-cash-fix-2026-05.md`）：

| # | Bug | 修复 |
|:--|:----|:----|
| 1 | 再平衡按满额分配，无视实际亏损 | `alloc_base = min(fixed_base, available_total)` |
| 2 | 重新建仓按满额分配 | `alloc_base = min(fixed_base, available)` |
| 3 | 再平衡成本未从现金扣除 | `has_cash -= cost` |
| 4 | `has_cash=0.0` + max_position_pct → 现金消失，pv漏算现金；成本回收效应(次日pv重算) | `has_cash = available - mv - cost`, `pv = has_cash + mv` |
| 5 | 超额用固定基准NAV比百分比基准 → pv>1亿时放大超额 | 超额统一用百分比收益 `pct_ret[t] = pv[t]/pv[t-1]-1` 计算 |
| 6 | 新股上市日(close[t-1]=0)导致基准计算inf | `rets = np.where(np.isfinite(rets), rets, 0.0)` 在 _compute_benchmark 中 |
| 7 | **年化超额用总点数差÷年数(简单平均)** → 等权IR为负但中证IR虚高至1.25 | 改为 `ann_excess = strat_ann - bm_ann`（复利年化相减） |
| 8 | **年化收益率(固定基准法用单利)与IR(百分比复利)不一致** → IR偏低 | `_compute_stats` 统一用 `(1+total_ret)^(1/years)-1` 复利法 |

```python
# ❌ 错误：无视亏损仍按满额分配
target_amt = self.fixed_base / n_effective

# ✅ 正确：按实际可用资金分配
available_total = max(has_cash + cur_mv, 0)
alloc_base = min(self.fixed_base, available_total)
target_amt = alloc_base / n_effective

# ❌ 错误：pv不含剩余现金
has_cash = 0.0
pv[t] = mv - cost

# ✅ 正确：保留现金，成本嵌入has_cash，pv含全部价值
has_cash = available - mv - cost  # 成本永久扣除
pv[t] = has_cash + mv  # = available - cost
```

**修复效果**：原先 s18 回撤 -104.98% → -95.45%，S118 单日-84.70%断崖消失 → 最大-6.27%。等权策略超额不再有spurious正超额。完整修复日志见 `references/bug-log-2026-05-16.md`。  
