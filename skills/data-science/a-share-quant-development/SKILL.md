---
name: a-share-quant-development
category: data-science
description: A股量化APP平台开发——项目架构、桌面平台、批量运行、结果管理。
trigger: User asks to modify app.pyw, change UI, fix platform bugs, or says 'app研发'/'进入量化app研发'/'桌面平台'.
---

# A股量化APP平台开发工作流

> ⚠️ **Alpha 策略研发请使用 `alpha-rapid-combinatorics` skill。** 本 skill 仅覆盖 APP 平台、项目架构、批量运行等工程方面的内容。

## 项目结构

```
a_stock_trade/
├── core/
│   ├── backtest_utils.py    # 引擎（DataLoader, BacktestEngine, Visualizer）
│   ├── alpha_utils.py       # 因子函数库
│   └── platform.py          # 轻量平台（自动发现+汇总CSV，零依赖）
├── strategies/              # 每个策略一个 a*.py 文件
├── batch_run.py             # 单进程批量运行器
├── live/                    # 实盘数据
│   ├── strategies.json      # 实盘策略配置
│   └── positions.json       # 持仓明细（已废弃）
├── app.pyw                  # tkinter 桌面平台（主入口）
├── data/                    # K线数据（NPZ缓存）
└── results/                 # 回测结果
    ├── _summary.csv
    └── _summary_batch.csv
```

## 批量运行与排名

### 方案A（推荐）：单进程批量运行器 batch_run.py

```bash
cd ~/Desktop/a_stock_trade
PYTHONIOENCODING=utf-8 USERPROFILE="C:\\Users\\Mayn" python batch_run.py
PYTHONIOENCODING=utf-8 python batch_run.py --tags alpha          # 按标签过滤
PYTHONIOENCODING=utf-8 python batch_run.py --names a212 a219     # 按名字过滤
```

**优势**：数据加载1次，内存常驻，顺序调每个策略的 `generate_alpha()`，跳过各自 `main()` 里的重复加载。

### 方案B（调试）：子进程模式 core.platform run

```bash
python -m core.platform run                     # 全量
python -m core.platform run --tags momentum     # 按标签
python -m core.platform run --names s76         # 按名字
python -m core.platform rank                    # 查排名（从CSV，秒出）
python -m core.platform compare s76 s67         # 对比

# 单个策略（兼容）
python strategies/aXXX.py
```

方案B每个策略独立子进程，各自加载NPZ缓存（~1.5s/次）。适合 `--names` 小批量调试。

## 核心引擎配置（core/backtest_utils.py）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MIN_COVERAGE` | `0.0` | 最低数据覆盖率。修改后必须删 NPZ 缓存重生成 |
| `BACKTEST_START` | `"2016-05-17"` | 回测起始日期 |
| `INIT_CAP` | `100_000_000` | 每日固定交易金额 1亿 |
| `COMMISSION` | `0.0003` | 万三佣金 |
| `SLIPPAGE` | `0.001` | 0.1% 滑点 |
| `STAMP_DUTY` | `0.0005` | 印花税 0.05%（仅卖出时收取，2026-05-18 新增） |

**成本计算**：买入成本 = 成交额 × (佣金+滑点)；卖出成本 = 成交额 × (佣金+滑点+印花税)。`BacktestEngine` 再平衡时自动拆分买卖计算。

## app.pyw 桌面平台

### 布局层级
```
Tk (self)
├── Row 0: title_lbl
├── Row 1: main_notebook (ttk.Notebook)
│   ├── Tab "📊 策略回测"
│   │   ├── Column 0: left_frame — 策略列表
│   │   │   ├── header_frame: 标题 + 刷新 + 余额
│   │   │   ├── run_bar: ▶全量回测 | ▶运行选中 | 🤖自动研发 | ⏹停止
│   │   │   └── tree (ttk.Treeview)
│   │   └── Column 1: right_frame — 详情面板
│   │       ├── Row 0: dev_frame (研发日志，初始隐藏)
│   │       ├── Row 1: data_status (数据状态栏 — NPZ元数据：最新日期/股票数/交易日/更新时间)
│   │       ├── Row 2: detail_title
│   │       ├── Row 3: detail_notebook (📈净值曲线 / 📄策略代码)
│   │       └── Row 4: btm (stats + 打开原图)
│   └── Tab "🔴 实盘策略"
│       └── pw = PanedWindow
│           ├── Pane 1: strat_tree（实盘策略列表）
│           ├── Pane 2: pos_tree（组合持仓 + 合计条）
│           └── Pane 3: sp_tree（策略持仓 + 合计条）
```

### 固定基准回测引擎常见陷阱

**问题1: has_cash 变负** → 分配基准用 `min(fixed_base, available_total)`

**问题2: 再平衡成本未扣除** → 加 `has_cash -= cost`

**问题3: 成本回收效应** → `has_cash = available - mv - cost`, `pv = has_cash + mv`

**问题4: 超额用固定基准NAV比** → 统一用百分比收益 `pct_ret[t] = pv[t]/pv[t-1]-1`

**问题5: alpha_mode 非调仓日每日再平衡** → 月频/周频策略用 `forward_fill_alpha` 把 alpha 信号保持到非调仓日。但引擎 `alpha_mode` 每天按 `alloc_base * w / close[t]` 重建仓位，导致 PV 中 `net_pnl + index_returns` 交互产生虚假收益（首月 128% 暴涨）。

**修复**：在"正常再平衡"段开头比较两日**原始 alpha 得分向量**——`np.array_equal(signal[:, t-1], signal[:, t])`。forward-filled 的数据完全相同则直接延续仓位（`shares[:,t]=shares[:,t-1]`），跳过每日 rebalance。

**坑1**：不要用选股集对比（`np.array_equal(prev_held, curr_sig_bool)`）。因为 valid mask 过滤（S股/退市/涨跌停）会使 `_alpha_to_weights` 输出的选股集逐日变化，即使 alpha 信号完全一致。必须比较 raw signal。

**坑2**：`forward_fill_alpha(a, f)` 用 `ff_idx = np.maximum.accumulate(idx)` 实现 forward-fill。`a[:, ff_idx]` 返回的矩阵中，非调仓日的列与最近调仓日完全相同（同一列内存引用）。所以 `np.array_equal(signal[:, t-1], signal[:, t])` 对 forward-filled 的列恒为 True。

**问题6: 涨跌停买卖逻辑不对称** → A股实盘规则：涨停可卖不可买、跌停可买不可卖。原代码 `can_buy = ~limit_up & ~limit_down` 和 `can_sell = ~limit_up & ~limit_down` 涨跌停时买卖都禁止，导致涨停无法止盈、跌停无法抄底。  
**修复**：`can_buy = ~limit_up`（跌停可买）, `can_sell = ~limit_down`（涨停可卖）。

**问题7: max_position_pct 限仓双重计费** → 在再平衡段中，个股仓位上限（`max_position_pct`）的 `excess_val`（`has_cash += excess_val`, line 815）与后续的 `net_pnl`（`has_cash += net_pnl`, line 823）**重复计算**了限仓释放的现金。因为 `net_pnl = sum(cur_pos) - sum(new_pos_after_cap)` 中的 `sum(new_pos)` 已经是限仓后的值（小于 alloc_base），差额已包含在 net_pnl 中。再加一次 `excess_val` 导致 P&L 虚高。

**示例**：alloc_base=100M，3只股票限仓释放 30M → sum(new_pos)=70M，net_pnl=cur_pos-70M。net_pnl 已包含 30M 的释放金额，再加 30M 就多了一倍。

**修复**：直接删除 `has_cash += excess_val` 行。net_pnl 自动完整处理。

**验证**：回测首月日收益 > 10% 通常是这个 bug 导致（不限于首月，每次限仓量大的调仓日都会虚增）。

### 颜色方案

见 `core/color_code.txt` 或 references/app-color-scheme。

### 自动研发按钮的架构（两阶段）

```
Phase 1: Hermes 写代码
  ├─ 拍快照: time.time() + set(glob(strategies/*.py))
  ├─ hermes -z (只写代码不跑回测) → PIPE 捕获标准输出
  ├─ 前 5 行实时显示到 dev_text
  ├─ 完成后: 计算 💭 思考用时 → self.refresh() 刷新策略列表
  └─ diff before_files vs after_files → 找出新策略文件

Phase 2: 自动回测
  ├─ dev_text 显示 📦 发现 N 个新策略
  ├─ 逐个 subprocess.Popen([sys.executable, file], PIPE) → communicate(timeout=600)
  ├─ 显示最后 20 行输出到 dev_text
  ├─ 完成后: 计算 ⏱ 回测用时 → self.refresh() 刷新结果
  └─ 状态栏: "✅ 全部完成（💭 XXs + ⏱ XXs）"
```

**计时流**: `_t0` 在方法开头记录 → `_think_sec[0]` 在 done 事件中设置 → 通过 `bt_done` 消息携带 `bt_sec` → `poll_bt` 读取两者显示。

**停止按钮**: 同时杀死 `_dev_proc` (Hermes) 和 `_bt_proc` (回测子进程)，设置 `_dev_stopped = True` 让轮询循环退出。

**队列架构**: 使用 `queue.Queue` 在线程间传递消息：
- `("line", text)` → Phase 1 实时行
- `("done", output)` → Phase 1 完成（含完整输出）
- `("error", msg)` → Phase 1 异常
- `("bt_line", text)` → Phase 2 实时行
- `("bt_done", sec_str)` → Phase 2 完成（含回测秒数）

**兜底处理**: poll() 的 else 分支（Hermes 线程结束但队列未收到 done 事件时）会检测新文件并启动 Phase 2。

### 图表布局（Visualizer.plot_and_save）

3子图，暗色主题，14×10英寸：
```
子图1: 策略净值 + 等权基准(虚线) + 等权超额(点线) + 持仓数(右轴柱状)
子图2: 中证1000超额曲线（差值法，含最大回撤标注）
子图3: 等权超额曲线（差值法，含超额回撤标注）
```

### 数据状态栏

`_update_data_status()` 方法从 NPZ 读取元数据显示在回测页面右侧顶部：
```
📅 2026-05-15  |  🏢 5203只  |  📆 2426天  (2016-05-17~2026-05-15)  |  ✅ 最新5203只可交易  |  🕐 05-17 13:39
```
在 `_build_backtest_tab` 中插入 row 1，在 `refresh()` 中也会调用以刷新状态。

### 实盘列表"最后更新"列

读取 `equity_curve.png` 的 mtime（不是文件夹）。

### 实盘策略"最新信号"列

`refresh_live()` 中 `s.get("signal","")` 已被替换为 `get_last_pos_date(folder)`，从 `position_matrix.npz` 读取最后有持仓的交易日（MM-DD 格式）。

### 等比缩放缩仓阈值

`refresh_combined_positions()` 中缩仓算法：从持仓市值最大的股票开始逐个加入，等比缩放后每只实际金额 < 阈值（2万）则停止。阈值定义在 `core/app.pyw` 中 `if actual_amt < 20000`。

## 数据管道（K线 + 基本面）

### A股前缀白名单

所有数据下载和缓存构建代码必须统一使用以下白名单过滤，三处同步修改：

```python
a_prefixes = {"000","001","002","003","300","301","302","303",
              "600","601","603","605","688"}
```

三处：
- `core/update_data.py:get_all_stocks()`
- `core/update_data.py:_build_cache()`
- `core/update_fundamentals.py:get_all_stocks()`

遗漏后果：B股（200xxx/900xxx）、债券（1xx/4xx/5xx/7xx/8xx/9xx 短码）混入 NPZ，导致股票数虚高至 6691（实际 A 股约 5241）。

### NPZ 缓存重建

`update_data.py:main()` 执行完增量下载后调用 `_build_cache()` 而非 `_clean_cache()`。直接在更新脚本中从 CSV 构建 NPZ（~35s for 5241×2427），避免回测时等 30 秒。

```python
# _build_cache() 在 update_data.py 中重建 NPZ
np.savez_compressed(CACHE_NPZ,
    close=close, open=open_, volume=volume,
    high=high, low=low,
    codes=codes, dates=dates,
    names=names_arr, is_st=is_st, exchange=exchange)
```

缓存结构同回测引擎 `DataLoader._load_data()` 的输出。

### batch 文件退出码

`core/update_data.bat` 末尾必须加 `exit /b 0` 兜底。否则 Windows Task Scheduler 的 Last Result 可能为 2（误报失败）。

## 实盘策略并行运行陷阱

`_run_all_live_strategies()` 使用 `ThreadPoolExecutor` 时，`importlib.util.spec_from_file_location` + `exec_module` **不是线程安全的**。多个策略同时 import 时，重名模块（numpy/matplotlib/core.backtest_utils）产生竞争条件 → 死锁或段错误。

**修复**：`max_workers = 1`，策略逐个串行执行。

## 基本面数据下载注意事项

### API 选择：用 `stock_financial_abstract` 而非 `stock_financial_abstract_ths`

`ak.stock_financial_abstract_ths`（同花顺版）只覆盖约 50% A 股（~2550/5241），其余返回 `'NoneType' object has no attribute 'string'` 错误。改用 **`ak.stock_financial_abstract`**（通用版）覆盖全部 A 股。

**格式差异**：THS 版以日期为行、指标为列；通用版以指标名为行、日期为列，需要转置：

```python
# 通用版：rows=80指标名，cols=日期列（如20260331,20251231...）
df = ak.stock_financial_abstract(symbol=code)
# 转置逻辑：
# 1. 选指标行 → 2. 按日期列展开 → 3. 按报告期聚合
records_df = pd.DataFrame(records)
pivoted = records_df.groupby("报告期", as_index=False).first()
pivoted = pivoted.ffill().fillna(0.0)
```

**字段映射**：通用版的指标名与 THS 版不同：

| THS 原名 | 通用版对应名 |
|----------|-------------|
| `营业总收入同比增长率` | `营业总收入增长率` |
| `净利润同比增长率` | `归属母公司净利润增长率` |
| `销售毛利率` | `毛利率` |
| `净资产收益率` | `净资产收益率(ROE)` |

见 `references/fundamental-data-system.md`。

## 引擎回测关键点

- Windows 路径避开尖括号/冒号/双引号等
- User profile: `USERPROFILE="C:\\Users\\Mayn"` 前缀运行
- NPZ 缓存删除后自动 fallback 到 CSV 重新加载
- 策略文件一律以 `a` 前缀命名
- `decay_linear` 替代已废弃的 `alpha_smooth`
- 基本面数据系统见 `references/fundamental-data-system.md`
