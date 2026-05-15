---
name: a-share-strategy-development
description: "A股量化策略全流程开发：回测框架、信号设计、参数调优、Bug排查。基于backtest_utils共享模块，每个策略只需编写generate_signal()函数返回bool信号矩阵。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [a-share, backtest, strategy, quant, python]
    related_skills: [test-driven-development, systematic-debugging]
---

# A股量化策略开发

## 框架结构

```
a_stock_trade/
├── app.py                  ← Windows桌面版（入口，在根目录）
├── run_all.py              ← 一键全量回测+对比（入口，在根目录）
├── core/                   
│   ├── __init__.py
│   ├── backtest_utils.py   ← 共享回测模块（数据加载、回测引擎、绘图）
│   └── download_data.py    ← 数据下载器
├── strategies/             ← 每个策略独立的 .py 文件
│   ├── __init__.py
│   ├── s01_equal_weight_daily.py  →  generate_signal(close, dates, **kw)
│   ├── s02_equal_weight_weekly.py
│   └── ... s36_*.py
├── data/                   ← K线数据 CSV + NPZ 缓存
└── results/                ← 自动保存的回测结果（每个策略一个子目录）
```

### core/backtest_utils.py 提供：

| 类/函数 | 功能 |
|---------|------|
| `DataLoader` | 加载 CSV → `.npz` 缓存（首次 30s，之后 0.5s） |
| `TradingRules` | 涨跌停（主板10%/创业板20%/科创20%/ST5%）、停牌（volume=0）、新股（首月禁交易） |
| `BacktestEngine` | 信号驱动回测、等权再平衡、个股仓位≤10%、固定基准收益 |
| `IndexLoader` | 下载中证1000指数做基准对比 |
| `Visualizer` | 净值图+基准叠图+超额收益曲线+多策略对比图 |
| `weekly_filter` | 周频过滤工具 |
| `print_stats` | 统计结果打印 |

## 策略开发模板

每个策略是一个独立 `.py` 文件放在 `strategies/` 目录下，只需实现 `generate_signal(close, dates, **kwargs)`：

```python
#!/usr/bin/env python
"""
SXX 策略名称
策略简要描述
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from core.backtest_utils import (
    DataLoader, BacktestEngine, Visualizer,
    IndexLoader, TradingRules, RESULTS_BASE,
    print_stats, COMMISSION, SLIPPAGE,
)


def generate_signal(close, dates=None, **kw):
    \"\"\"返回 bool 矩阵 (N_stocks, N_days)，True=该股票当天应被持有\"\"\"
    signal = np.zeros(close.shape, dtype=bool)
    # ... 你的信号逻辑 ...
    return signal


def main():
    label = "SXX 策略名称"
    folder = "SXX-策略名称"
    print("=" * 60)
    print(f"  {label}")
    print("=" * 60)

    loader = DataLoader().load()
    close = loader.close
    dates = loader.dates

    print(f"[生成信号] {label}...")
    signal = generate_signal(close, loader.dates)
    # ...

    idx_nav, idx_dates = IndexLoader.load(trade_dates=dates)
    rules = TradingRules(close, loader.open_price, loader.volume,
                         loader.codes, loader.names_arr,
                         loader.is_st, loader.exchange)
    engine = BacktestEngine(commission=COMMISSION, slippage=SLIPPAGE)
    engine.run(close, signal, dates, trading_rules=rules)
    engine.set_benchmark(idx_nav, idx_dates)

    print_stats(engine.stats)
    Visualizer.plot_and_save(engine, os.path.join(RESULTS_BASE, folder), label)
    print("=" * 60)


if __name__ == "__main__":
    main()
```

**要点：**
- `sys.path.insert(0, ...)` 确保 `strategies/sXX.py` 可以 standalone 运行（`python strategies/sXX.py`）
- 当被 `run_all.py` 动态导入时，`sys.path` 由 run_all 管理，策略文件的 `sys.path.insert` 不会造成副作用
- 周频策略额外 import `weekly_filter`：`from core.backtest_utils import ..., weekly_filter`
- 文件命名必须 `sNN_描述性名称.py`，不能是 Python 标准库名（如 platform.py）

### generate_signal 可获取的数据

| 数据 | 来源 | 说明 |
|------|------|------|
| `close` | 参数传入 | 收盘价矩阵 (N_stocks, N_days) |
| `dates` | 参数传入 | 日期数组 |
| `loader.open_price` | main()中通过 loader 访问 | 开盘价 |
| `loader.volume` | main()中通过 loader 访问 | 成交量 |
| `loader.codes` | main()中通过 loader 访问 | 股票代码 |
| `loader.is_st` | main()中通过 loader 访问 | 是否ST |
| `loader.exchange` | main()中通过 loader 访问 | 板块（main/chinet/star） |

### 常见信号类型

| 类型 | 示例 | 实现要点 |
|------|------|---------|
| 价格动量 | 前日涨幅TOP20% | `ret = close[:, t] / close[:, t-1] - 1` |
| 均值回归 | 前日下跌 | `signal[:, 1:] = ret[:, :-1] < 0` |
| 移动均线 | MA5>MA20 | 逐个时间窗口 `np.nanmean` |
| 波动率 | 低波/高波选股 | `np.nanstd` over rolling window |
| RSI | 超卖/超买 | 14日RSI公式，注意RSI=0边缘情况 |
| 布林带 | 突破上下轨 | MA±k×std |
| 创新高/低 | 突破/超卖 | 滚动 `np.nanmax`/`np.nanmin` |
| 成交量 | 放量/缩量 | 需要从 loader.volume 获取（signal函数需额外传参）|

## 频次选择

| 频次 | 信号生成 | 持有方式 |
|------|---------|---------|
| 日频 | 每天独立产生信号 | signal 每天可变化，引擎自动买卖 |
| 周频 | 仅周一产生信号 | 用 `weekly_filter(dates)` + forward-fill：`for t: if not first[t]: signal[:,t] = signal[:,t-1]` |

信号量太少（日均<50）容易触发资金集中放大效应。

## 调试与Bug排查

### 常见问题

| 现象 | 根因 | 修复 |
|------|------|------|
| **总收益 -100%** | 信号太少+仓位上限+MIN_EFFECTIVE挡不住 | 加最低持仓数保护 |
| **总收益异常高（如10000%+）** | 信号太少→仓位上限→现金累积→再投→放大（S09案例） | 加信号最小数量限制，详见下方"集中度放大" |
| **NAV全为NaN** | `0 * NaN = NaN` | 数据层 `fillna(0.0)` |
| **净值全为0（total=0）** | 清仓后 `capital_deployed` 未重置，下次信号日跳过部署导致 `total=has_cash` 未被计入 | 清仓/无信号日重置 `capital_deployed=False` |
| **老股被当新股** | `np.argmax(close>0)` 在首日返回0 | 加判断 `if first==0: continue` |
| **成本重复计算** | 仓位超限转现金同时计了两次成本 | 统一由 `traded_sum` 覆盖 |
| **pv[t]不更新** | 仓位超限转现金后 `pv[t]` 没加现金 | `pv[t]=has_cash+sum(positions)` |
| **`platform` 模块冲突** | 在策略目录下创建 `platform.py` 会覆盖 Python 标准库 | 文件名避开标准库名（如 `gen_platform.py`） |
| **超额收益为 -100%** | 固定基准法下相对基准的对齐索引漂移 | 确保 `set_benchmark()` 以 `_first_nav_idx` 对齐 |

**Python 标准库文件名黑名单（创建 .py 文件时避开）：**
`os`, `sys`, `time`, `math`, `json`, `csv`, `re`, `pathlib`, `io`, `base64`, `subprocess`, `datetime`, `random`, `itertools`, `collections`, `typing`, `platform`, `string`, `numbers`, `decimal`, `fractions`, `statistics`, `hashlib`, `hmac`, `secrets`, `uuid`, `bisect`, `heapq`, `array`, `weakref`, `types`, `copy`, `pprint`, `reprlib`, `enum`, `ast`, `inspect`, `textwrap`, `codecs`, `struct`, `pickle`, `shelve`, `marshal`, `dbm`, `sqlite3`, `configparser`, `netrc`, `logging`, `getpass`, `curses`, `socket`, `ssl`, `email`, `json`, `mailcap`, `mimetypes`, `base64`, `binascii`, `quopri`, `uu`, `tabnanny`, `pyclbr`, `py_compile`, `compileall`, `dis`, `pickletools`, `doctest`, `unittest`, `pdb`, `profile`, `trace`, `webbrowser`, `tkinter`, `turtle`, `wave`, `colorsys`, `imghdr`, `sndhdr`, `fileinput`, `filecmp`, `tempfile`, `shutil`, `glob`, `fnmatch`, `linecache`, `macpath`, `posixpath`, `dircache`。

最佳实践：策略脚本统一用 `sNN_描述性名称.py`，工具脚本用 `gen_xxx.py` 或 `xxx_tool.py`。

### 警惕：sed/awk 修改 Python 文件会破坏 docstring

使用 `sed` 或 `awk` 批量修改 Python 文件时，多行 docstring 的结构极易被破坏：
- `sed` 只对单行模式匹配，无法感知 `"""` 块的开始和结束
- `awk` 的 `/^"""/` 模式会漏掉非行首的 `"""`，混入 docstring 后会把 `import` 行吞进 docstring 里
- **正确做法**：对 Python 文件的批量修改务必使用 Python 脚本（`glob.glob` + `re.sub`），以 AST-aware 方式处理

如果已经破坏了，修复方法是：
1. 找到 `def generate_signal` 作为分界线
2. 从此到文件尾是整个策略的逻辑 body（通常完整无损）
3. 重建文件头（shebang + docstring + sys.path + import），拼接 body

### 集中度放大效应（S09 案例）

**现象：** RSI超卖策略（日均信号仅 5-50 只），总收益 > 20000%，超额夏普极低。

**根本原因：**
```
深跌反弹 +20% → 超限10%卖出套现 → 现金增加
→ 下次再平衡现金+盈利同时再投 → 放大
→ 10年×2426天累积出天文数字
```

**修复方法：**

1. **加信号最小数量保护**（已内置在BacktestEngine）：
```python
MIN_EFFECTIVE = max(20, int(n_sig_t * 0.1))
if n_effective < MIN_EFFECTIVE:
    achievable = shares[:, t-1].copy()  # 不交易，保持当前持仓
```

2. **策略层加总信号量过滤**（在 generate_signal 中）：
```python
mask = (rsi[:, t] < 25) & (rsi[:, t] > 0) & (close[:, t] > 0.5)
if mask.sum() >= 80:          # 至少80只股票触发才建仓
    signal[:, t] = mask
```

**判断信号是否过少：**
```python
per_day = signal.sum(axis=0)
print(f"avg={per_day.mean():.0f} median={np.median(per_day):.0f} "
      f"<20 days={(per_day<20).sum()}")
```
- 日均 < 50 → 高风险
- 有超 10% 的交易日信号 < 20 → 极高风险

### 参数调优模式

当策略趋势正确但参数未优化时：

1. 在 `generate_signal()` 中添加命名参数：
```python
def generate_signal(close, dates=None, lookback=10, hold_days=5, **kw):
```

2. 编写调优脚本进行网格搜索：
```python
for lb in [5, 10, 15, 20]:
    for hd in [3, 5, 8, 10]:
        signal = generate_signal(close, dates, lookback=lb, hold_days=hd)
        engine = BacktestEngine(...)
        engine.run(close, signal, dates, trading_rules=rules)
        engine.set_benchmark(idx_nav, idx_dates)
        sharpe = float(engine.stats["夏普比率"])
        # 以超额夏普为优化目标
```

3. 可视化调优结果，选择超额夏普 + 回撤 综合最优

### A股市场特性（经验结论）

- **动量效应 >> 反转效应**：追涨（涨幅TOP10%、20日新高）夏普高，抄底（跌幅TOP10%、布林带下轨）亏钱
- **低价股效应显著**：低价股（小市值）夏普远高于高价股
- **等权是稳赢基本盘**：不用任何择时，+134%/10年
- **日频动量 + 10%仓位上限**：在30+策略中独占鳌头
- **短期回看窗口优于长期**：S35调优显示 lookback=5（5日低点）超额夏普 0.71，远优于 lookback=30 的 0.00
- **较紧止损更平滑**：回撤 5% 止损的夏普高于 10% 止损

### 状态机类策略开发（S31 案例）

信号依赖于持仓状态（如在持仓/不在持仓）时，需要对每只股票逐日遍历：

```python
def generate_signal(close, dates=None, **kw):
    n_stocks, n_days = close.shape
    signal = np.zeros(close.shape, dtype=bool)
    for s in range(n_stocks):
        in_pos = False
        peak = 0.0
        for t in range(n_days):
            if not in_pos:
                if 创新高条件:
                    signal[s, t] = True; in_pos = True; peak = price
            else:
                signal[s, t] = True  # 持续持有
                if 回撤止损条件:
                    signal[s, t] = False; in_pos = False
    return signal
```

这种模式适用于：追高止损、移动止盈、择时进出等策略。
注意：3000只×2500天 ≈ 7.5M 次循环，耗时约 1-2 秒。

### 辅助函数在文件重构时易丢失

当用 `def generate_signal` 作为切分点重建策略文件时，**所有在 `generate_signal` 之前定义的辅助函数（`_vol`, `_rsi`, `_ma`, `_bollinger`）都会丢失**。

**检查方法：** 扫描每个策略文件，看 `generate_signal` 体内调用了哪些以 `_` 开头的函数名但文件中没有定义：

```python
import re
def check_missing_helpers(content):
    m = re.search(r'def generate_signal.*?:(.*?)(?=\ndef |\Z)', content, re.DOTALL)
    if not m: return []
    body = m.group(1)
    defined = set(re.findall(r'def (\w+)', content))
    calls = set(re.findall(r'(_[a-zA-Z]\w*)\s*\(', body))
    return calls - defined
```

**缺失函数的补回模板：**

```python
def _ma(close, w):
    """简单移动平均线"""
    ma = np.zeros_like(close)
    for t in range(w, close.shape[1]):
        ma[:, t] = np.nanmean(close[:, t-w+1:t+1], axis=1)
    return ma

def _vol(close, w=20):
    """滚动波动率（标准差）"""
    ret = np.zeros_like(close)
    mask = close[:, :-1] != 0
    with np.errstate(divide="ignore", invalid="ignore"):
        ret[:, 1:] = np.where(mask, close[:, 1:] / close[:, :-1] - 1.0, 0.0)
    vol = np.zeros_like(close)
    for t in range(w, close.shape[1]):
        vol[:, t] = np.nanstd(ret[:, t-w+1:t+1], axis=1)
    return vol

def _rsi(close, w=14):
    """RSI 计算"""
    rsi = np.zeros_like(close)
    ret = np.zeros_like(close)
    mask = close[:, :-1] != 0
    with np.errstate(divide="ignore", invalid="ignore"):
        ret[:, 1:] = np.where(mask, close[:, 1:] / close[:, :-1] - 1.0, 0.0)
    for t in range(w, close.shape[1]):
        c = ret[:, t-w+1:t+1]
        g = np.where(c > 0, c, 0); l = np.where(c < 0, -c, 0)
        avg_g = np.nanmean(g, axis=1); avg_l = np.nanmean(l, axis=1)
        rs = np.where(avg_l != 0, avg_g / avg_l, 0)
        rsi[:, t] = 100 - 100 / (1 + rs)
    return rsi

def _bollinger(close, w=20, n_std=2):
    """布林带: 返回 (middle, upper, lower)"""
    middle = _ma(close, w)
    std = np.zeros_like(close)
    for t in range(w, close.shape[1]):
        std[:, t] = np.nanstd(close[:, t-w+1:t+1], axis=1)
    upper = middle + n_std * std; lower = middle - n_std * std
    return middle, upper, lower
```

**⚠️ `_bollinger()` 返回三元组**，调用时必须解包：
```python
# 正确
_, _, lower = _bollinger(close, 20, 2.0)   # S15 布林带下轨
_, upper, _ = _bollinger(close, 20, 2.0)   # S16 布林带上轨

# 错误 — lower/upper 会是 (3, N_days) 而非 (N_stocks, N_days)
lower = _bollinger(close, 20, 2.0)
```

单变量接收三元组会导致信号矩阵形状从 `(2930, 2426)` 变成 `(3, 2426)`，引擎跑出 `broadcast error`。

### `run_all.py` 必须同时保存单个策略结果

`run_all.py` 默认只做策略对比（`Visualizer.plot_comparison`），**不会保存每个策略的个股结果文件夹**。如果不加保存，`results/` 下只有 `30策略对比/`，没有 `S01-等权日频/` 等独立文件夹，`app.py` 也读不到数据。

**必须在每个策略跑完后加** `Visualizer.plot_and_save()`：

```python
for name, modname in STRATEGIES:
    ...
    engine.run(close, signal, dates, trading_rules=rules)
    engine.set_benchmark(idx_nav, idx_dates)
    ...

    # ★ 保存单个策略结果
    folder_name = name.replace(" ", "-")
    Visualizer.plot_and_save(engine,
                             os.path.join(RESULTS_BASE, folder_name),
                             name)
```

这样每个策略的结果才会出现在 `results/S01-等权日频/equity_curve.png` 等路径。

### 标准开发流程

1. **创建文件**：在 `strategies/` 目录下复制现有 `s*.py` 模板，修改 `generate_signal()`。模板包含 `main()` 和 `if __name__ == "__main__":` 入口。记得使用 `from core.backtest_utils import ...` 而非直接 `from backtest_utils import ...`。
2. **运行测试**：`python strategies/sXX_xxx.py` 看总收益、超额夏普、回撤
3. **检查异常**：
   - 总收益 > 500% → 检查信号量是否太少（日均<50）
   - 回撤 < -80% → 检查信号量或加最小持仓保护
   - 超额夏普 > 0.5 → 优秀，考虑参数调优
4. **参数调优**：修改 `generate_signal(*, lookback, hold_days, ...)` 支持 kwargs，网格搜索
5. **加入 run_all**：在 `run_all.py` 的 `STRATEGIES` 列表中添加：
   ```python
   ("S37 新策略名称", "s37_new_strategy"),
   ```
   注意：`run_all.py` 使用 `__import__()` 动态导入策略模块，它已将 `strategies/` 加入 sys.path，所以只写模块名（不含 `.py`）。

   `run_all.py` 的标准 sys.path 设置：
   ```python
   PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
   sys.path.insert(0, PROJECT_ROOT)
   sys.path.insert(0, os.path.join(PROJECT_ROOT, "strategies"))
   from core.backtest_utils import (
       DataLoader, BacktestEngine, Visualizer, ...
   )
   ```
6. **结果自动出现在app**：重跑 `python app.py` 即可在桌面应用中看到新策略。
7. **推送GitHub**：`git add -A && git commit && git push`

## 夏普比率定义

超额夏普 = 年化超额收益 / 年化跟踪误差（信息比率），在 `set_benchmark()` 中计算并覆盖原夏普。不是传统总收益夏普，因为固定基准法下总收益夏普会严重失真。

## 固定基准 vs 复利

| 模式 | 收益计算 | 年化公式 | 适用场景 |
|------|---------|---------|---------|
| **固定基准（默认）** | P&L / base | total_ret / years（单利） | 防止复利放大效应，收益真实反映策略能力 |
| 复利 | NAV / NAV_{t-1} - 1 | (1+total_ret)^(1/years)-1 | 传统基金净值跟踪 |

固定基准模式下：日收益 = 今日P&L / INIT_CAP，10% 仓位涨 10% → 利润 = 10%×10%×base = 1% base。

## 结果查看方式

| 方式 | 命令 | 说明 |
|------|------|------|
| **Windows桌面App** | `python app.py` | tkinter界面，左侧策略列表 + 右侧图表+指标 + 显示源码 |
| 终端 | `python strategies/sXX_xxx.py` | 运行单个策略，文本结果（不弹图） |
| 全量对比 | `python run_all.py` | 跑所有策略，生成对比图+CSV |

### Windows桌面App（app.py）

使用 tkinter + Pillow 构建，无外部依赖。架构：

```
app.py
├── scan_strategies()      ← 扫描 results/ 目录，读取 stats.csv
├── App(Tk)
│   ├── 左侧: Treeview     ← 策略列表（名称、总收益、超额夏普、回撤）
│   ├── 右侧: Canvas       ← 显示 equity_curve.png 缩放版
│   ├── 底部: Text         ← 关键指标文字
│   ├── [📂 打开原图]      ← 系统图片查看器看全尺寸
│   └── [📄 显示代码]      ← 弹出新窗口显示策略 .py 源码
└── show_code()            ← 从文件夹名映射到源码文件
```

**文件夹名→源码文件映射：**
结果目录 `S01-等权日频` → 提取前缀 `s01` → 在 `strategies/` 下匹配 `s01_*.py`。确保策略文件名以 `sNN_` 开头并放在 `strategies/` 中。

**添加新策略到app：** 只需在 results/ 下有对应结果目录，app 自动加载，无需修改 app.py。完整 app 源码见 `templates/app.py`。

> **注意：** app.py 的 `_load_code()` 方法（内置版）或 `show_code()`（模板版）会在 `strategies/` 子目录中搜索源码文件，而不是在项目根目录。如果重构后源码搜索失败，先确认 app.py 的 glob 路径指向了 `strategies/`。

**无终端启动 & Treeview 排序实现** 见 `references/app-deck.md`。

### 用户偏好：回测不弹图

策略运行时 `Visualizer.show_chart()` 已被移除，结果仅保存到磁盘，不弹窗。如需查看图表，通过 app.py 或手动打开 `results/<策略名>/equity_curve.png`。

## 已知缺陷

- `generate_signal()` 只接收 close 和 dates，如需 volume/open 需改接口
- 单日10%仓位上限是总市值的10%，非固定的10%
- 没有做空/杠杆支持
- Python 循环生成信号（5000×2500 量级）耗时较长
- 文件名不能叫 `platform.py`（与 Python 标准库冲突）
