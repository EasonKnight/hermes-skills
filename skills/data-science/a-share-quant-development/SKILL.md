---
name: a-share-quant-development
category: data-science
description: A股量化策略全流程开发——架构搭建、策略编写、批量回测、结果管理、桌面平台。
trigger: User asks to write, test, modify backtest strategies, mentions 'a_stock_trade', '量化', '回测', 'app.pyw', '实盘', '桌面平台', or says '进入量化app研发'/'app研发' (app development mode).
---

# A股量化策略开发工作流

## 项目结构

```
a_stock_trade/
├── core/
│   ├── backtest_utils.py    # 引擎（DataLoader, BacktestEngine, Visualizer）
│   ├── alpha_utils.py       # 因子函数库
│   └── platform.py          # 轻量平台（自动发现+汇总CSV，零依赖）
├── strategies/              # 每个策略一个 s*.py / a*.py 文件
│   └── ...
├── batch_run.py             # 单进程批量运行器（加载数据一次，顺序跑所有策略）
├── live/                    # 实盘数据
│   ├── strategies.json      # 实盘策略配置
│   └── positions.json       # 持仓明细
├── app.pyw                  # tkinter 桌面平台（主入口）
├── run_all.py               # 旧版批量运行器
├── scripts/                 # 辅助脚本
├── data/                    # K线数据
└── results/                 # 回测结果
    ├── _summary.csv         # 汇总CSV（用于快速排名查询）
    └── _summary_batch.csv   # batch_run.py 生成的汇总
```

## 策略文件规范

每个策略文件必须包含以下**模块级元数据**（放在 import 之前）：

```python
LABEL = "S76 低波动动量周频"    # 显示名
FOLDER = "S76-低波动动量周频"   # 结果目录名
FREQ = "weekly"                 # daily 或 weekly
TAGS = ["momentum", "lowvol"]   # 标签
POOL = "csi1000"                # 股票池
```

核心函数只需要 `generate_signal(close, dates, volume)`，返回 bool 矩阵 (N_stocks, N_days)；或 `generate_alpha(close, dates, volume)` 返回 float 得分矩阵。

## 核心发现（已验证）

### 频率选择
- **周频 > 日频 > 月频**。日频换手50-87%，交易成本吃掉alpha。周频是最优平衡点。
- 例：S67低价周频(+21.98%, 换手3.61%) vs S25低价日频(换手极高, 成本吞噬收益)

### 反向策略
- 表现差的信号策略，反转后往往有效——排除原策略选中的股票，买入剩余。
- "宽基增强型"：剔除极端特征股（过热/过冷），吃市场平均向上收益。
- 验证：S22超涨→S57超涨反向(IR 1.49)

### 有效策略类型
- **低价策略**（近5年表现最好）：S67周频+21.98%, S78月频+20.78%
- **低价+排除极端涨跌**：S66年化21.52%, 夏普1.00
- **低波动动量**：S76近20日涨幅前30%中选波动率最低50%
- **反向宽基**：S57超涨反向、S58布林上轨反向

### 无效/负收益策略模式
- 过滤条件太多导致日均持股 < 20只 → 波动大、成本高
- 日频+多条件叠加 → 换手>50%, 成本吃掉所有alpha
- 趋势跟踪类（VCP、均线发散度、VWAP）在A股表现差
- 在CSI1000池内按成交额分10组做均衡动量/低波——各组分头选股，均衡大小盘效果有限

### 成交额(amount)作为大小盘区分指标
见 `references/data-coverage-filtering.md`。amount=close×volume 可作为截面大小盘区分指标。

#### 大小盘均衡策略模式
在 CSI1000 内部用 amount 分档实现大小盘平衡：

1. **分档法**：按 amount 分10组，每组内 z-score 目标因子（动量/低波），各组等权复合。每组分到的权重相等，避免全部压在小盘。
2. **杠铃法**：factor = amount_zscore² × target_factor。偏好成交额极端（大盘+小盘）的股票，避开中盘。
3. **量比确认**：factor = (amount/20d_avg_amount) × target_factor。不分大小盘，只看成交额是否放大确认信号。

杠铃法（A301 大小盘杠铃低波，DECAY=20，中证IR 0.73/换手 5.98%）效果最好。

## 批量运行与排名

### 方案A（推荐）：单进程批量运行器 batch_run.py

```bash
cd ~/Desktop/a_stock_trade
PYTHONIOENCODING=utf-8 USERPROFILE="C:\Users\Mayn" python batch_run.py
PYTHONIOENCODING=utf-8 python batch_run.py --tags alpha          # 按标签过滤
PYTHONIOENCODING=utf-8 python batch_run.py --names a212 a219     # 按名字过滤
```

**核心优势**：数据加载1次（~1.5s 读 NPZ 缓存），内存常驻，顺序调每个策略的 `generate_alpha()`，跳过各自 `main()` 里的重复加载。100个策略约3-5分钟。

**工作原理**：
```
batch_run.py 流程:
1. load_data()  # 一次
2. for 每个策略文件:
   a. 动态 import 模块
   b. 调用 generate_alpha(close, dates, volume)
   c. BacktestEngine.run(...)  # 直接跑，不重新加载数据
   d. Visualizer.plot_and_save(...)
   e. 读取 stats.csv 汇总
3. 保存 _summary_batch.csv + 打印排名
```

记得设 `USERPROFILE`，否则 `os.path.expanduser("~")` 被污染。

### 方案B（旧）：子进程模式 core.platform run

```bash
python -m core.platform run                     # 全量
python -m core.platform run --tags momentum     # 按标签
python -m core.platform run --names s76         # 按名字
python -m core.platform rank                    # 查排名（从CSV，秒出）
python -m core.platform compare s76 s67         # 对比

# 单个策略（兼容）
python strategies/s76_lowvol_momentum_weekly.py
```

方案B每个策略独立子进程，各自加载NPZ缓存（~1.5s/次）。100个策略 → 150s纯加载开销。适合 `--names` 小批量调试。

### 桌面平台
双击 app.pyw（建议用 pythonw.exe 快捷方式避免终端窗口）。

### 全量回测 — 后台进程模式

```bash
cd ~/Desktop/a_stock_trade && USERPROFILE="C:\Users\Mayn" python -m core.platform run
```

注意：`USERPROFILE` 必须显式设置，否则 `os.path.expanduser("~")` 会因环境变量污染报错。

### 批量清理策略文件

当需要在多个策略文件中统一修改（如移除旧导入/调用），用 `execute_code` 配合 `re.sub` 批量处理：

```python
import os, glob, re
for fp in glob.glob("strategies/s[0-9]*.py"):
    with open(fp) as f: content = f.read()
    content = re.sub(r'旧模式', '', content)
    with open(fp, 'w') as f: f.write(content)
```

## 核心工具函数优化陷阱

### amihud_illiq — 不能在循环内重复计算 close×volume

**问题**：`amihud_illiq(close, volume, t, n)` 每次调用内部都计算 `amt = np.maximum(close * volume, 1)` → 5203×2426 的全矩阵乘法。若在 `for t in range(2426): h[:,t]=amihud_illiq(...)` 中调用，就是 2426 次冗余的全矩阵计算，耗时暴增。

**修复**：使用 `amihud_illiq_fast(amt, close, t, n)`，循环外先算 `amt` 一次：

```python
# 错误（极慢 — 每次循环都要算 close*volume 全矩阵）
for t in range(20, n_d):
    h[:,t] = amihud_illiq(close, volume, t, 20)

# 正确（预计算 amt，循环内仅切片）
amt = np.maximum(close * volume, 1)
for t in range(20, n_d):
    h[:,t] = amihud_illiq_fast(amt, close, t, 20)
```

**`amihud_illiq_fast(amt, close, t, n=20)`** 在 `core/alpha_utils.py` 中定义，紧接原函数之后。签名：`amt : ndarray (N_stocks, N_days) 预计算的成交额矩阵`。

**已修复的策略**（8个）：a212, a213, a215, a219, a264, a268, a269, a280。模式一致：改 import + 加 amt 预计算 + 替换函数名 + 调整 loop range。

**检查要点**：任何时候在 alpha 策略循环中调用了全矩阵操作（`close * volume`、`np.nanmean(close, axis=1)` 等涉及全维度的操作），都要提到循环外预计算。

## app.pyw 桌面平台

### 整体布局层级
```
Tk (self)
├── Row 0: title_lbl ("📊 A股策略平台") — sticky="ew"
├── Row 1: main_notebook (ttk.Notebook, style="Main.TNotebook") — sticky="nsew"
│   ├── Tab "📊 策略回测"
│   │   └── backtest_tab (Frame)
│   │       ├── Column 0 (weight=0): left_frame — 策略列表
│   │       │   ├── header_frame: "策略列表" + ↻刷新 + 💰余额
│   │       │   ├── run_bar: ▶全量回测 | ▶运行选中 | 🤖自动研发 | ⏹停止
│   │       │   └── tree (ttk.Treeview + VScrollbar)
│   │       └── Column 1 (weight=1): right_frame — 详情面板
│   │           ├── Row 0: dev_frame (研发日志, 默认hidden via grid_remove)
│   │           ├── Row 1: detail_title + sep
│   │           ├── Row 2: detail_notebook (ttk.Notebook)
│   │           │   ├── Tab "📈 净值曲线" (Canvas + 自适应缩放)
│   │           │   └── Tab "📄 策略代码" (Text + 语法高亮 + 保存/撤销)
│   │           └── Row 3: btn_frame (stats_text + 📂打开原图按钮)
│   └── Tab "🔴 实盘策略"
│       └── pw = ttk.PanedWindow(live_tab, orient=VERTICAL)
│           ├── Pane 1 (weight=2): strat_sec, header has: 刷新按钮 + 运行全部实盘按钮│           │   ├── strat_tree: 6列 (名称|状态|分配金额|最新信号|累计收益|最后更新)
│           │   ├── Row 0: strat_header "📋 实盘策略" + ↻刷新 + ▶运行全部实盘
│           │   ├── Row 1: strat_tree (Treeview + VScrollbar)
│           │   └── Row 2: live_update_label
│           ├── Pane 2 (weight=1): pos_sec — 组合持仓
│           │   ├── Row 0: pos_header "📊 组合持仓（全策略叠加）"
│           │   ├── Row 1: pos_tree (6列 Treeview + VScrollbar)
│           │   └── Row 2: pos_bar (列对齐合计条, self.pos_bar_lbls[])
│           └── Pane 3 (weight=1): sp_sec — 策略持仓
│               ├── Row 0: sp_header — "🎯 策略名" (self.sp_title_lbl)
│               ├── Row 1: sp_tree (7列 Treeview + VScrollbar)
│               └── Row 2: sp_bar (列对齐合计条, self.sp_bar_lbls[])
```

- `main_style = ttk.Style()` 使用独立 `"Main.TNotebook"` 样式名，与详情面板内部 `style2`/`"TNotebook"` 互不冲突
- `self.main_notebook`、`self.live_tab` 挂为实例属性供后续编程访问
- 实盘表格挂在实例上：`self.strat_tree`、`self.pos_tree`、`self.sp_tree`、`self.sp_title_lbl`

# ── 配色方案（Python IDLE Classic · 亮色主题，最终确定）

**⚠️ 用户配色偏好（核心教训）**：此部分经多轮反复才最终确定。用户对颜色极其敏感，任何自选/混合颜色方案都被拒绝。**只使用已知权威来源的完整色板，不要自己调色。**

最终确定方案：**Python IDLE Classic 亮色主题**（白底黑字），所有颜色值精确取自 `cpython/Lib/idlelib/config-highlight.def`：

```python
# 来源：https://github.com/python/cpython/blob/main/Lib/idlelib/config-highlight.def
BG_PRIMARY = "#ffffff"        # normal-background
BG_SECONDARY = "#f0f0f0"     # 浅灰面板
BG_TERTIARY = "#e0e0e0"      # 输入框
FG_PRIMARY = "#000000"        # normal-foreground（纯黑）
FG_SECONDARY = "#666666"      # 深灰辅文
FG_GREEN = "#00aa00"          # string-foreground（Python字符串绿）
FG_RED = "#dd0000"           # comment-foreground（Python注释红）
ACCENT_BLUE = "#0000ff"       # definition-foreground（Python函数蓝）
ACCENT_CYAN = "#0000ff"       # 同上
ACCENT_PURPLE = "#900090"     # builtin-foreground（Python内置紫）
ACCENT_BTN_PURPLE = "#900090"
ACCENT_GREEN = "#00aa00"      # 字符串绿
ACCENT_RED_BG = "#dd0000"     # 注释红
ACCENT_GOLD = "#ff7700"       # keyword-foreground（Python关键字橙）
BORDER = "#cccccc"
TABLE_STRIPE = "#f0f0f0"
HOVER = "#e0e0e0"
```

**Python IDLE 语义映射**：
```
关键字橙 #ff7700 → 金色强调
函数蓝  #0000ff → 按钮/选中行/蓝色强调
内置紫  #900090 → 紫色/AI
字符串绿 #00aa00 → 正收益数值
注释红  #dd0000 → 负收益数值/红按钮
```

**修改配色的正确方式**：找到一个完整的、已发布的色板配色方案（如 Python IDLE、Tailwind CSS 官方色板），列出所有颜色常量一次替换完成。**不要增量修改**，不要自己混合颜色，不要在回复中讨论颜色选择——直接给出完整方案。

**被拒绝的方案（历史记录，不要再次尝试）**：
- Dracula 紫黑主题
- TradingView 暗色
- Tokyo Night 暗蓝
- GitHub Dark
- Catppuccin Mocha 粉彩
- 任何自定义混合配色
- 纯灰度/黑白
- Tailwind neutral 灰阶

### 布局规范
- 左面板：策略列表（标题+刷新按钮 → 运行按钮栏 → 策略Treeview）
  - 运行按钮栏：全量回测(`#2ea043` 绿 + hover `#238636`) | 运行选中(`#58a6ff` 蓝 + hover `#3b82e0`) | 自动研发(`#6f42c1` 紫 + hover `#5835a0`) | 停止(`#da3633` 红 + hover `#b62324`)
- 右面板：详情标题 → Notebook标签页（📈净值曲线 / 📄策略代码）
  - 代码标签页含工具栏：保存(绿) | 撤销修改(灰) + 语法高亮(Consolas 10pt)
- 底部：指标文本区域 + 打开原图按钮
- 默认全屏启动：`self.state("zoomed")`
- 策略元组签名：`(label, stats_dict, equity_png_path, src_path, created_time_str)` — 5元素，用索引访问(s[0]..s[4])而非解包

### 图表子图布局（Visualizer.plot_and_save）

目前3子图布局（dark slate theme, 14x10 inch）：

| 子图 | 内容 | 配色 |
|:---:|:-----|:----:|
| 1 | **净值曲线**：策略(蓝 `#3b82f6` 实线) + 等权基准(黄 `#f59e0b` 虚线) + **等权超额**(绿 `#22c55e` 点线) + 持仓数(紫 `#a78bfa` 柱,右轴) | 含最大回撤标注(红箭头) |
| 2 | **中证1000超额曲线**(橙 `#f97316` 实线) — 替代原回撤折线图 | `engine.csi1000_excess_nav`，不含等权基准回撤线 |
| 3 | **等权超额曲线**(绿 `#22c55e` 实线) — 与等权周频基准的超额对比 | 含超额回撤标注(红箭头)，`engine.excess_nav` |

> **重要**：不再绘制回撤折线图（子图2原为策略回撤+基准回撤）。中证1000超额 = `1 + nav - csi1000_nav`（差值法），通过 akshare 下载 `sh000852`（中证1000指数）。下载失败时子图2显示"数据不可用"。

### 图表自适应缩放
```python
self._raw_pil_img = Image.open(equity)
self._render_chart()
self.img_canvas.bind("<Configure>", self._on_canvas_resize, add="+")

def _render_chart(self):
    ratio = min(cw / img.width, ch / img.height)
    img_small = img.resize((new_w, new_h), Image.LANCZOS)
    self._tk_img = ImageTk.PhotoImage(img_small)  # 必须保存为实例属性防GC
    self.img_canvas.create_image(x, y, anchor="nw", image=self._tk_img)
```

### 运行按钮使用 Windows cmd 终端
```python
# run_all → start cmd.exe /c → 完成后自动关闭
subprocess.Popen(f'start "全量回测" cmd.exe /c "cd /d {d} && python -m core.platform run"', shell=True)

# run_selected → CREATE_NEW_CONSOLE（无pause，跑完自动关）
proc = subprocess.Popen(f'cd /d "{d}" && python "{src}"',
    creationflags=subprocess.CREATE_NEW_CONSOLE, shell=True)
threading.Thread(target=lambda: (proc.wait(), self.after(500, self.refresh)), daemon=True).start()
```

### 自动研发按钮（后台Hermes线程）
深紫色 `#4c1d95`（hover `#3b1470`），点击启动后台线程运行 `hermes -z [prompt]`：
```python
env = os.environ.copy()
env["USERPROFILE"] = "C:\\Users\\Mayn"
proc = subprocess.Popen(["hermes", "-z", prompt], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, env=env, encoding="utf-8")
```
- 后台进程输出 → queue → poll()循环刷新UI
- 支持停止按钮（proc.kill() + _dev_stopped标志）
- 研发完成自动 refresh()
- 非阻塞，不冻结GUI

### 余额窗口（💰按钮 → BalanceWindow）
标题栏新增 `💰` 按钮（金色 `ACCENT_GOLD`），弹出模态 Toplevel 查询 DeepSeek 账户余额。
消费估算函数：`estimate_deepseek_consumption()` 在 `app.pyw` 末尾定义。
详见 `references/deepseek-api-balance.md`。

### 比较基准：中证1000等权周频组合（引擎自动计算）

**`BacktestEngine.run()` 末尾自动调用 `_compute_benchmark(close, dates)`**，不再需要手动调用 `IndexLoader` 或 `set_benchmark()`。

```python
# 核心架构（core/backtest_utils.py）
class BacktestEngine:
    def __init__(self, ..., index_returns=None):  # index_returns: 可选，指数日收益率
        ...

    def run(self, close, signal, dates, ...):
        # ... 回测逻辑 ...
        # 中证1000指数收益用于现金部分
        if self.index_returns is None:
            # 从 akshare 下载 sh000852，计算日收益率
            self.index_returns = csi_ret
            self._csi1000_idx_close = idx_close  # 供 _compute_benchmark 复用
        # 每日现金部分(1亿-股票市值)按中证1000收益率计入pv
        for t in range(1, n_days):
            prev_stock_mv = sum(shares[:, t-1] * close[:, t-1])
            cash_part = max(0, fixed_base - prev_stock_mv)
            pv[t] += cash_part * index_returns[t]
        # 然后按调整后pv计算daily_ret/nav
        self._compute_benchmark(close, dates)  # 复用 _csi1000_idx_close 避免二次下载

    def _compute_benchmark(self, close, dates):
        # 检查 self._csi1000_idx_close 是否可用，有则跳过 akshare 下载
        # 从close矩阵计算等权周频组合净值（中证1000股票池）
        # 超额净值 = 1 + nav - bm_nav（差值法，非比值法）
        # 还下载中证1000指数(sh000852)计算csi1000_excess_nav用于图表
```

**设计要点**：
- `index_returns` 参数可选，不传则自动从 akshare 加载（无网络时静默跳过）
- 现金部分 = `max(0, fixed_base - 上一日股票市值)`，按中证1000日收益率增值
- 防止策略通过低仓位"躲大跌"——大跌日即使空仓也吃指数跌幅
- akshare 下载的指数数据存到 `self._csi1000_idx_close`，`_compute_benchmark` 复用避免二次下载

### 实盘列表"最后更新"列读取 equity_curve.png 而非文件夹

文件夹的 mtime 在 Windows 上不一定随内部文件变更而更新。正确做法：

```python
folder = s.get("folder", "")
update_time = ""
if folder:
    fdir = os.path.join(RESULTS, folder)
    fpath = os.path.join(fdir, "equity_curve.png")   # 最可靠：回测必定生成
    if not os.path.exists(fpath):
        fpath = os.path.join(fdir, "stats.csv")        # 备选
    if not os.path.exists(fpath):
        fpath = fdir                                    # 回退到文件夹
    if os.path.exists(fpath):
        mtime = os.path.getmtime(fpath)
        update_time = datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
```

- 每周（`weekly_filter`）选取中证1000成分股中 `close>0.5` 的股票等权持有
- 通过 `load_csi1000_codes()` + `self.engine_codes` 过滤到284只成分股
- 超额净值 = `1 + nav - benchmark_nav`（差值法：策略累积收益 - 基准累积收益）
- 年化超额 = `excess_ret / years`（简单年化，不复利）
- `csi1000_excess_nav` = `1 + nav - csi1000_nav`（中证1000指数超额，用于图表子图2）
- `set_benchmark()` 保留用于手动覆盖，但一般不需要

### 固定基准回测引擎的常见陷阱

**问题1: has_cash 变负**
当持仓股票下跌后重新再平衡，原有逻辑按满额 `fixed_base` (1亿) 分配目标仓位。股票跌了还需要维持满额意味着要额外"补钱"，导致 `has_cash` 变负。清仓时产生负净值，回撤超过100%。

**修复**：在 rebalance、初始建仓、重新部署三处均使用 `min(fixed_base, available_total)` 作为分配基数，确保不会超出现有资金。

```python
# 再平衡分支
available_total = max(has_cash + cur_mv, 0)
alloc_base = min(self.fixed_base, available_total)
target_amt = alloc_base / n_effective
```

**问题2: 再平衡成本未扣除**
rebalance 分支计算了 `cost = traded_sum * cost_rate` 但只记录到 `tc[t]`，未从 `has_cash` 中扣除，导致 pv 虚高。

**修复**：增加 `has_cash -= cost`。

## 实盘策略标签页（2026-05-17 重构 — ttk.PanedWindow + 列对齐合计条）

**不再依赖** `live/positions.json`（已废弃）。组合持仓从所有策略的 `positions` 字段聚合。

```python
# 数据源
live/strategies.json              → load_live_strategies()  → strat_tree (Pane 1)
策略 positions 字段聚合叠加        → refresh_combined_positions() → pos_tree (Pane 2)
live/strategies.json .positions   → refresh_live_strat_detail()  → sp_tree (Pane 3)
```

### 布局结构（ttk.PanedWindow — 垂直可拖拽分隔条）

```python
pw = ttk.PanedWindow(live_tab, orient=VERTICAL)
pw.grid(row=0, column=0, sticky="nsew", padx=8)

# 每个 section = make_section(pw), 内部 grid:
#   Row 0: header (columnspan=2)
#   Row 1 (weight=1): Treeview (col=0) + Scrollbar (col=1)
#   Row 2 (weight=0): 列对齐合计条 (columnspan=2) — 仅 pos/sp 有

pw.add(strat_sec, weight=2)  # 实盘策略列表（自身无合计条）
pw.add(pos_sec,   weight=1)  # 组合持仓 + pos_bar (self.pos_bar_lbls[6])
pw.add(sp_sec,    weight=1)  # 策略持仓 + sp_bar (self.sp_bar_lbls[7])
```

用户拖拽 sash 自由调整三区域高度。选中行高亮 `#3b4261` 柔和蓝灰。

### 列对齐合计条（make_aligned_bar 工厂函数）

```python
def make_aligned_bar(parent, col_cfgs):
    """返回 (bar_frame, [label, ...]) — Label 网格对齐 Treeview 列宽"""
    bar = Frame(parent, bg=BG_TERTIARY, height=26)
    labels = []
    for i, (cid, ctext, cw) in enumerate(col_cfgs):
        anchor = "w" if i == 0 else "e"
        lbl = Label(bar, text="", font=("Microsoft YaHei", 9, "bold"),
                    fg=ACCENT_CYAN, bg=BG_TERTIARY, anchor=anchor)
        lbl.grid(row=0, column=i, sticky="ew", padx=6)
        bar.columnconfigure(i, weight=0, minsize=cw)
        labels.append(lbl)
    return bar, labels

self.pos_bar, self.pos_bar_lbls = make_aligned_bar(pos_sec, POS_COLS)
self.sp_bar,  self.sp_bar_lbls  = make_aligned_bar(sp_sec,  SP_COLS)
```

更新合计值（示例）：
```python
self.pos_bar_lbls[0].config(text=f"合计 {len(codes)}只")
self.pos_bar_lbls[2].config(text=str(total_lots))
self.pos_bar_lbls[4].config(text=f"{total_amount:,.0f}")
```

> 注意 `n_strats==1` 时用 `next(iter(d["strategies"]))` 取策略名，**不可用** `d["name"]`（那是股票名）。

### 组合持仓（全策略叠加）

`refresh_combined_positions()` 遍历所有策略的 `.positions` 字段：

```
按股票代码聚合: code → {name, lots, amount, strategies: set()}
按总市值降序排列
涉及策略列: 多策略→"N个策略", 单策略→策略名
合计条: self.pos_bar_lbls[0..5]
空数据: self.pos_bar_lbls[0].text="无持仓数据", 其余清空
```

在添加策略（后台完成）、删除策略、`refresh_live()` 时自动调用。

### 添加到实盘（两步走，不卡UI）

**第一步 — 立即保存**（`positions: None`）→ 刷新列表，用户立刻看到：

```python
new_strat = {
    "name": name, "status": "运行中", "capital_pct": "100000",
    "signal": "—", "cum_return": cum_ret, "created": created,
    "folder": folder,    # 从策略文件正则解析 FOLDER=
    "positions": None,   # 后台填充
}
```

> `capital_pct` 字段实际存储**分配金额（元）**，新建策略默认 100,000。用户可通过右键菜单或双击编辑。

**第二步 — 后台线程计算**（`threading.Thread` + `after()` polling）：

```python
def worker():
    result["positions"] = calc_strat_positions(folder)

def poll():
    if not result: self.after(200, poll); return
    live = load_live_strategies()
    for s in live:
        if s["name"] == name: s["positions"] = pos; break
    save_live_strategies(live)
    self.refresh_combined_positions()
    if 当前选中该策略: self.refresh_live_strat_detail(name)

threading.Thread(target=worker, daemon=True).start()
self.after(200, poll)
```

去重保护：同名策略不重复添加。

### 编辑分配金额（右键/双击）

实盘策略列表的`capital_pct`列（表头"分配金额"）支持编辑：

- **右键菜单** → `✏️ 设置分配金额`，弹出输入框
- **双击**分配金额列单元格 → 弹出输入框
- 输入框预填当前值，留空或取消保持原值
- 自动校验正数，整数自动去`.0`
- 保存后即时刷新列表

```python
def edit_allocation_amount(self):
    sel = self.strat_tree.selection()
    cur = vals[2] if len(vals) > 2 else "100000"
    new_val = simpledialog.askstring("分配金额", ..., initialvalue=cur)
    # 校验 → 更新 strategies.json → refresh_live()
```

双绑定方式：
```python
self.strat_tree.bind("<Double-1>", self.on_live_strat_double)
self.live_strat_menu.add_command(label="✏️ 设置分配金额", command=self.edit_allocation_amount)
```

双击只响应**分配金额列**（col index=2），点击其他列不触发编辑。

### 从实盘移除（右键菜单）

```python
# self.live_strat_menu = Menu(...) + add_command("❌ 从实盘移除")
# self.strat_tree.bind("<Button-3>", self.show_live_strat_menu)

def remove_from_live(self):
    strategies = [s for s in load_live_strategies() if s.get("name") != name]
    save_live_strategies(strategies)
    self.refresh_live()         # 刷新列表 + 组合持仓
    self.refresh_live_strat_detail(None)  # 清空下方详情
```

#### 策略持仓表（sp_tree）— 从 position_matrix.csv 预计算

**数据流**：持仓矩阵在「添加到实盘」时由后台线程 `calc_strat_positions(folder)` 算好，存到 JSON 的 `positions` 字段。点击策略时直接从内存读取，零 I/O。

**calc_strat_positions(folder) — 模块级函数**：
```python
def calc_strat_positions(folder):
    """读取 results/{folder}/position_matrix.csv 最后一行 → 计算手数
       返回 [(code, name, lots, price, amount), ...] 或 None"""
    csv_path = os.path.join(RESULTS, folder, "position_matrix.csv")
    import csv
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if row: last_row = row
    stock_map = load_stock_name_map()
    for i in range(1, min(len(header), len(last_row))):
        if val_str == "0": continue
        amount = float(val_str)
        stock_idx = int(header[i])
        name, price = stock_map.get(stock_idx, (str(stock_idx), 0))
        if price > 0:
            shares = int(amount / price / 100) * 100     # 向下取整到100股
            lots = shares // 100
            positions.append((str(stock_idx), name, lots, round(price,2), round(shares*price,0)))
    return positions
```

**position_matrix.csv 格式**：行=交易日（第一行是列头：股票内部索引），列=股票，单元格=持仓金额（元）。取最后一行（最新交易日）作为当前持仓。内部索引与 NPZ 的 `codes` 数组一致。

**refresh_live_strat_detail(strat_name) 渲染逻辑**：
- `positions=None` → 表格显示"⏳ 持仓计算中..."，所有 `self.sp_bar_lbls` 清空
- `positions=[]` → 表格显示"无持仓"
- `positions=[(code, name, lots, price, amount), ...]` → 逐行填充 sp_tree + 列对齐合计条（`self.sp_bar_lbls[0]="合计 N只", [3]=total_lots, [4]=avg_price, [5]=total_amount`）
- 合计条（`self.sp_bar` + `self.sp_bar_lbls[]`）：底栏深色 Frame，Label 按列对齐显示合计值，固定不随滚动

#### 股票名称/价格映射 — 预计算 JSON（86KB，2ms 加载，自动刷新）

**核心优化**：从 97MB NPZ（close matrix: 2930×2426）一次性提取最新收盘价到 86KB JSON，加载 2ms。不再读 985MB CSV。

```python
_STOCK_MAP_CACHE = None

def load_stock_name_map(force_reload=False):
    global _STOCK_MAP_CACHE
    if _STOCK_MAP_CACHE is not None and not force_reload:
        return _STOCK_MAP_CACHE

    npz_path = os.path.join(base, "data", "a_stock_kline_3y.npz")
    json_path = os.path.join(base, "data", "stock_map.json")

    # NPZ 比 JSON 新 → 自动重生成（0.25s）→ 写回 JSON
    if os.path.exists(npz_path) and (
        not os.path.exists(json_path)
        or os.path.getmtime(npz_path) > os.path.getmtime(json_path)
    ):
        m = _build_stock_map_from_npz(npz_path)
        _STOCK_MAP_CACHE = m
        json.dump({str(k): v for k, v in m.items()}, open(json_path, "w"),
                  ensure_ascii=False, indent=None, separators=(",", ":"))
        return m

    # JSON 存在 → 2ms 瞬读
    if os.path.exists(json_path):
        _STOCK_MAP_CACHE = {int(k): v for k, v in json.load(open(json_path)).items()}
        return _STOCK_MAP_CACHE

    # 最后回退：NPZ 直接加载
    _STOCK_MAP_CACHE = _build_stock_map_from_npz(npz_path)
    return _STOCK_MAP_CACHE

def _build_stock_map_from_npz(npz_path):
    """遍历 2930 只股票，取最后一个非 NaN close → {idx: [name, price]}"""
    d = np.load(npz_path, allow_pickle=True)
    result = {}
    for i in range(len(d["codes"])):
        idx = int(d["codes"][i])
        name = str(d["names"][i])
        cl = d["close"][i]
        mask = ~np.isnan(cl)
        if mask.any():
            result[idx] = [name, round(float(cl[np.where(mask)[0][-1]]), 2)]
        else:
            result[idx] = [name, 0.0]   # 停牌 → price=0 → calc 跳过
    return result
```

**边界处理**（实测 2930 只全部有效）：
| 场景 | 处理 |
|------|------|
| 停牌股票（close 全 NaN） | price=0.0 → `calc_strat_positions` 跳过 |
| 部分 NaN 的股票 | 取最后一个非 NaN close |
| NPZ 更新 | `mtime(npz) > mtime(json)` 自动重生成 |
| JSON 损坏 | try/except → fallback 到 NPZ 直接加载 |

### 代码编辑器语法高亮

### 详情面板统计值（show_detail）

指标名用 `FG_SECONDARY`（`#6b7394` 中灰），数值按正负着色：

```python
self.stats_text.tag_configure("stat_key", foreground=FG_SECONDARY)
self.stats_text.tag_configure("stat_val_pos", foreground=FG_GREEN)
self.stats_text.tag_configure("stat_val_neg", foreground=FG_RED)
self.stats_text.tag_configure("stat_val", foreground=ACCENT_CYAN)

for k in self.STAT_KEYS:
    if k in stats:
        v = stats[k]
        self.stats_text.insert(END, f"  {k}:  ", "stat_key")
        if "%" in v or any(c in v for c in ("+","-")):
            try:
                nv = float(v.replace("%","").replace("+","").replace(",",""))
                tag = "stat_val_pos" if nv >= 0 else "stat_val_neg"
            except: tag = "stat_val"
        else:
            tag = "stat_val"
        self.stats_text.insert(END, v + "\n", tag)
```

### 按钮配色规范
```python
▶ 全量回测: bg=ACCENT_GREEN="#22c55e"  active="#16a34a"
▶ 运行选中: bg=ACCENT_BLUE="#60a5fa"   active="#2563eb"
🤖 自动研发: bg=ACCENT_BTN_PURPLE="#7c3aed"  active="#6d28d9"
⏹ 停止:     bg=ACCENT_RED_BG="#ef4444" active="#dc2626"
↻ 刷新:      bg=BG_TERTIARY
💰 余额:     bg=BG_TERTIARY + text=ACCENT_GOLD
▶ 运行全部实盘: bg=BTN_TEAL (深绿)
```
- 选中行高亮：背景 `#404040`，文字 `#ffffff`
- Treeview 表头：`borderwidth=0, relief="flat"` 去掉 3D 凸起
- Treeview 整体：`style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])` 去掉多余边框

## 常见陷阱

### USERPROFILE 环境变量
Windows的 `os.path.expanduser("~")` 依赖 `USERPROFILE` 环境变量。如果被污染（如终端输出串入），需要在命令前加：
```
USERPROFILE="C:\Users\Mayn" python script.py
```

### 关键配置参数（core/backtest_utils.py）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MIN_COVERAGE` | `0.0` | 股票最低数据覆盖率。CSV原始~5203只。`0.9`→2930只, `0.5`→4112只, `0.0`→全量5203只。**修改后必须删除 `data/a_stock_kline_3y.npz` 缓存重新生成。** |
| `BACKTEST_START` | `"2016-05-17"` | 回测起始日期（10年，2426个交易日） |
| `INIT_CAP` | `100_000_000` | 每日固定交易金额 1亿 |
| `COMMISSION` | `0.0003` | 万三佣金 |
| `SLIPPAGE` | `0.001` | 0.1% 滑点 |

**数据过滤陷阱**：`MIN_COVERAGE` 用 `close_df.dropna(thresh=min_days)` 过滤，新股（数据不足N天）会被剔除。设为 `0.0` 即纳入全部股票，引擎自动处理上市前的 NaN。

### amihud_illiq 循环性能陷阱
见上方"核心工具函数优化陷阱"节。复习要点：
- `amihud_illiq` 每次调用计算 `close*volume` 全矩阵
- 必须用 `amihud_illiq_fast(amt, close, t, n)` + 预计算 `amt`
- 检查所有调用了 `amihud_illiq` 的策略，确认已用 fast 版

### 实盘列表最后更新时间
见上方"实盘列表'最后更新'列"节。读取 `equity_curve.png` 或 `stats.csv` 的 mtime，不要读文件夹 mtime。

## 回测日期裁剪
通过 `core/backtest_utils.py` 中的 `BACKTEST_START` 全局变量控制，或通过 `DataLoader._crop_dates()` 自动裁切。

### 策略文件清理
定期删除无对应results目录的策略文件（使用 `core/platform.py` 的自动检测机制）。
