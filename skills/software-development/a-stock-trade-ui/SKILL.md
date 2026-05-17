---
name: a-stock-trade-ui
description: GUI 修改规范与常用模式 — tkinter Treeview/Text/Notebook 在 a_stock_trade 项目中的修改套路
trigger: 用户要求修改 app.pyw 界面（列名、可编辑单元格、合计行、配色、字体等）
---

# A股量化桌面平台 — GUI 修改指南

## 配色约定 — 现代舒适深色主题（Modern Comfort Dark）
配色定义在项目根目录 `color_code.txt`，所有 UI 修改必须使用这些常量，禁止硬编码颜色值。

### 背景层级（中深灰，护眼舒适）
| 变量 | 色值 | 用途 |
|------|------|------|
| `BG_DEEP` | `#0d1117` | 最深背景（窗口底层） |
| `BG_PRIMARY` | `#161b22` | 主背景（主要工作区） |
| `BG_SECONDARY` | `#21262d` | 次级背景（卡片/侧边栏） |
| `BG_TERTIARY` | `#30363d` | 三级背景（输入框/表头/按钮） |
| `BG_ELEVATED` | `#3c444d` | 悬停/激活 |
| `BG_CARD` | `#1c2128` | 卡片专用 |

### 文字（柔和白色，高可读性）
| 变量 | 色值 | 用途 |
|------|------|------|
| `FG_PRIMARY` | `#f0f6fc` | 主文字（柔和白色） |
| `FG_SECONDARY` | `#8b949e` | 标签/正文 |
| `FG_MUTED` | `#6e7681` | 注释/占位符 |
| `FG_GHOST` | `#484f58` | 禁用状态 |

### 强调色（低饱和度，温和不刺眼）
| 系列 | 主色 | 暗调(悬停) | 按钮深色(常态) | 其他 | 用途 |
|------|------|-----------|--------------|------|------|
| 蓝色 | `ACCENT_BLUE = "#58a6ff"` | `ACCENT_BLUE_DIM = "#163d8a"` | `BTN_BLUE = "#0f2d6e"` | `ACCENT_BLUE_SOFT = "#1f6feb"` | 链接/主要按钮/表头 |
| 青绿 | `ACCENT_TEAL = "#56d364"` | `ACCENT_TEAL_DIM = "#1a5c24"` | `BTN_TEAL = "#0f3a12"` | `ACCENT_TEAL_BG = "#132238"` | 成功/正收益/全量回测 |
| 琥珀 | `ACCENT_AMBER = "#f0883e"` | `ACCENT_AMBER_DIM = "#8a4518"` | — | — | 警告/注意 |
| 金色 | `ACCENT_GOLD = "#e3b341"` | — | — | — | 金额/高亮数据 |
| 红色 | `ACCENT_RED = "#f85149"` | `ACCENT_RED_DIM = "#6e1414"` | `BTN_RED = "#5a0a0a"` | `ACCENT_RED_BG = "#2d0c0f"` | 错误/负收益/停止 |
| 紫色 | `ACCENT_PURPLE = "#bc8cff"` | `ACCENT_PURPLE_DIM = "#451a75"` | `BTN_PURPLE = "#2e0f5c"` | — | AI/研发/自动研发 |

按钮设计: `bg=BTN_*`(深色常态)，`activebackground=*_DIM`(悬停提亮)。避免用主色直接做按钮 bg，文字看不清。

### 实盘策略标记（两棵树联动）
左侧回测结果树(`self.tree`)和右侧实盘策略树(`self.strat_tree`)都需要标记"已在实盘"的策略。

**逻辑**: 读取 `live/strategies.json` 中的策略名集合，遍历插入行时比对。

**左侧回测树(`self.tree`)** — 在 `populate_tree()` 中:
```python
live_names = {s["name"] for s in load_live_strategies()}
for i, entry in enumerate(self.strategies):
    name = entry[0]
    tag = "odd" if i % 2 else "even"
    if name in live_names:
        tag = "live"
    self.tree.insert("", END, values=(...), tags=(tag,))
```

**右侧实盘树(`self.strat_tree`)** — 在 `refresh_live()` 中:
```python
cap = float((s.get("capital_pct") or "").strip().replace(",", ""))
# except → cap = 0
tags = ("live",) if cap > 0 else ()
self.strat_tree.insert("", END, values=vals, tags=tags)
```

**tag 配置**: `self.tree.tag_configure("live", background="#1a3a1a", foreground="#ffffff")` — 深绿色背景 + 白色文字（暗色主题下保证可读性）。
注意两棵树是独立的 tree 对象，需要各自 tag_configure。

### 边框 & 表格
- `BORDER = "#30363d"`, `BORDER_LIGHT = "#3c444d"`, `BORDER_GLOW = "#58a6ff"`
| `TABLE_STRIPE = "#151b24"`, `TABLE_HOVER = "#252b33"`, `TABLE_SELECT = "#7c3aed"`
- 正收益行底色: `ACCENT_TEAL_BG = "#132238"`，负收益行底色: `ACCENT_RED_BG = "#2d0c0f"`

## 项目文件结构（2026-05-17 函数式重构 — 方案B）

用户拒绝模块拆分（方案A），采用**函数式重构（方案B）**：全部代码仍在 `app.pyw` 中，将 `__init__` 拆成多个 `_build_*` 子方法：

```
app.pyw  (1828行)
├── 顶层常量 (~360行)         # 配色、COLUMNS、load_live/stock 工具函数
├── class App(Tk)
│   ├── __init__()              # ~23行骨架：窗口属性 + _build_styles + _build_ui + 数据初始化
│   ├── _build_styles()         # ttk 样式配置（通用化 Notebook 样式循环）
│   ├── _build_ui()             # 标题 + Notebook 容器，调用子构建器
│   ├── _build_backtest_tab()   # 回测标签页（左侧列表+右侧详情面板，~160行）
│   ├── _build_live_tab()       # 实盘标签页（3个 PanedWindow Pane，~120行）
│   ├── _sort_strategies()      # 排序工具方法（消除3处重复排序代码）
│   ├── refresh() / refresh_live() / refresh_combined_positions() / refresh_live_strat_detail()
│   ├── 交互方法 (~20个)        # on_select / add_to_live / edit_amount / auto_develop 等
│   ├── 详情面板方法            # show_detail / _render_chart / _load_code / _highlight_code / save/revert
│   └── 排序方法                # sort_by / populate_tree / _get_sort_key
├── class BalanceWindow         # DeepSeek 余额查询对话框
└── hermes_streamer.py          # 自动研发实时输出转发器（独立脚本）
```

### 改什么取决于修改目标（2026-05 重构后）

| 要改什么 | 位置 |
|----------|------|
| 颜色值 | `app.pyw` 顶部第 29-73 行配色常量块 |
| 按钮行为/排列 | `_build_backtest_tab()` 中的按钮循环（btns 列表） |
| 回测策略列表 | `_build_backtest_tab()` Treeview + `populate_tree()` 渲染方法 |
| 实盘标签页 | `_build_live_tab()` 中的 3 个 Pane 构建 + `refresh_live*()` 数据方法 |
| 研发面板 | `_build_backtest_tab()` 中的 dev_frame 构建 + `auto_develop()` 方法 |
| 新增排序/过滤 | `_sort_strategies()` 工具 + `populate_tree()` + `sort_by()` |
| 按钮颜色 | 修改 `BTN_TEAL/BLUE/PURPLE/RED` 常量 + 对应 `ACCENT_*_DIM` 悬停色 |

⚠️ **`COLUMNS` 列定义**在顶层（~363行），同时被 `sort_by()` 和 `populate_tree()` 依赖。改列名/列宽/新增列需要在 `COLUMNS` 和 `_build_backtest_tab()` 的 Treeview columns 中同步修改。

## 研发日志面板（dev_frame）模式

### 创建位置
dev_frame 创建在 **回测标签页右侧详情面板的最顶部**（row 0，在 detail_title 之上），展开时标题和 Notebook 自动下移。按钮在回测标签页左侧，点击后框体在右侧详情面板展开。

```python
# _build_backtest_tab() 中 (right_frame 布局):
right_frame.rowconfigure(2, weight=1)  # row 2 = Notebook 撑满
# row 0 = dev_frame（默认隐藏）, row 1 = detail_title + separator, row 2 = Notebook

self.dev_frame = Frame(right_frame, bg=BG_PRIMARY, bd=1, relief="flat",
                       highlightbackground=ACCENT_GOLD, highlightthickness=1)
self.dev_label = Label(self.dev_frame, text="⏳ 等待研发...",
                       font=("Microsoft YaHei", 14, "bold"), ...)
self.dev_label.pack(fill=X, padx=6)
self.dev_text = Text(self.dev_frame, height=7, font=("Consolas", 13), ...)
self.dev_text.pack(fill=BOTH, expand=True, padx=4, pady=(0, 4))
self.dev_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))
self.dev_frame.grid_remove()     # 初始隐藏

self.detail_title.grid(row=1, column=0, sticky="ew")
separator.grid(row=1, column=0, sticky="ew")
self.notebook.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
```

**注意**：不要改变 row 顺序（dev_frame row 0 → detail_title row 1 → notebook row 2），这是原版备份中的布局。auto_develop 中 `dev_frame.grid(row=0, ...)` 展开时必须与之匹配。

**`tab.rowconfigure` vs `self.rowconfigure` 陷阱**：在 `_build_live_tab()` / `_build_backtest_tab()` 等子方法中配置标签页内的行权重，必须用 `tab.rowconfigure()`（参数是标签页 Frame），**不是** `self.rowconfigure()`（那是主窗口的行）。误用 `self.rowconfigure(1, weight=1)` 会在主窗口而非标签页上设置权重，导致布局完全错乱。

### 显示/隐藏
dev_frame 全程用 `grid()` 管理，**不要**混用 `place()`。

```python
# 显示:
self.dev_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))

# 隐藏:
self.dev_frame.grid_remove()
```

### 常见错误
- **place + grid 混用**：创建时 `place()`，显示时 `grid()` → tkinter 冲突，按钮点不动。必须全程只用一种几何管理器。
- **放错标签页**：按钮在回测tab，dev_frame 却在实盘tab？这其实是正确的——按钮点击后跳到实盘tab看进度。原始设计如此。
- **dev_frame 与 PanedWindow 抢 row**：dev_frame 在 row 0，PanedWindow 在 row 1。row 0 weight=0（固定高度），row 1 weight=1（填充剩余空间）。
- **`self.rowconfigure` vs `tab.rowconfigure`**：在 `_build_live_tab()` 里必须用 `tab.rowconfigure()` 配置标签页的行，**不是** `self.rowconfigure()`（那是主窗口的行）。

### 自动研发（auto_develop）模式 — 隐藏终端 + PIPE 读取

**稳定方案：后台运行（`CREATE_NO_WINDOW`），PIPE 读取输出，在 dev_text 中显示。**

```python
def auto_develop(self):
    import subprocess, threading, queue, os
    prompt = (
        "调用 a-stock-backtesting 和 alpha-rapid-combinatorics skill。"
        "项目路径 C:\\Users\\Mayn\\Desktop\\a_stock_trade，"
        "data/下有 a_stock_kline_3y.npz（5203股×2426日K线）和 a_stock_fundamentals.npz（43季基本面日频展开）。"
        "策略放 strategies/，结果放 results/<folder>/。"
        "POOL=CSI1000，LABEL/FOLDER/FREQ/TAGS 元数据，紧凑风格（;分号多赋值），主函数 main()→BacktestEngine。"
        "换手率<10%，每批1~3个策略，8分钟超时即交。"
        "新编写1~3个量化策略，优先用 alpha_utils.py 里的预制因子做排列组合。"
    )
    ...
    env = os.environ.copy()
    env["USERPROFILE"] = "C:\\\\Users\\\\Mayn"
    proc = subprocess.Popen(
        ["hermes", "-z", prompt],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
        env=env, encoding="utf-8", errors="replace"
    )
    self._dev_proc = proc
    for line in proc.stdout:
        out_lines.append(line)
        if len(out_lines) <= 5:
            q.put(("line", line.rstrip()))
    proc.wait()
    q.put(("done", "".join(out_lines)))
```

**Prompt 设计原则**：把所有上下文一次性塞进 prompt，让 Hermes 0 轮探索直接开工。包含了：
- 要加载的 skill 名
- 项目路径
- 数据文件名 + 规格
- 目录结构约定
- 元数据/风格/命名规范
- 硬约束（换手率、批量大小、超时）
- 方法论提示（预制因子排列组合）

**Windows `.pyw` + 子进程终端可见性的坑**：
- `.pyw` (pythonw.exe) 本身无控制台，子进程默认继承—也无控制台
- `CREATE_NEW_CONSOLE` 给子进程新终端，但若同时 PIPE 其 stdout，输出被截走→终端空白
- `ShowWindow(GetConsoleWindow(), 0)` / `FreeConsole()` 在 `.pyw` 进程不可靠
- 尝试过文件轮询 + tee 转发器方案，但 Windows 控制台 + PIPE 交互不稳定，最终回退到隐藏终端
- **结论**：`CREATE_NO_WINDOW + PIPE` 最稳定可靠

#### `stop_dev` 终止逻辑

```python
def stop_dev(self):
    if hasattr(self, "_dev_proc") and self._dev_proc and not self._dev_proc.poll():
        self._dev_proc.kill()  # kill 子进程 → PIPE 断开 → run_hermes 循环结束
    self._dev_stopped = True
    ...
```

#### `env["USERPROFILE"]` 必须设置
修复 Windows 下 hermes 路径污染问题：`env["USERPROFILE"] = "C:\\Users\\Mayn"`

#### 完成后自动刷新
```python
if not getattr(self, "_dev_stopped", False):
    self.after(500, self.refresh)  # 研发完成自动刷新回测列表
```

## 实盘策略置顶（populate_tree 模式）

回测结果列表中的实盘策略需要**固定在最前面，不参与排序**：

```python
def populate_tree(self):
    for row in self.tree.get_children():
        self.tree.delete(row)
    live_names = {s["name"] for s in load_live_strategies()}
    # 实盘策略居前，非实盘在后
    live_entries = [e for e in self.strategies if e[0] in live_names]
    other_entries = [e for e in self.strategies if e[0] not in live_names]
    sorted_entries = live_entries + other_entries
    for i, entry in enumerate(sorted_entries):
        name, stats = entry[0], entry[1]
        ...
        tag = "live" if name in live_names else ("odd" if i % 2 else "even")
        self.tree.insert("", END, values=..., tags=(tag,))
```

要点：
- 使用 `live/strategies.json` 中的名称集合判断哪些是实盘策略
- 非实盘策略保留奇偶斑马纹（用 sorted_entries 的索引 i 决定）
- 实盘策略不带奇偶标记，统一用 `"live"` tag（深绿背景白字）

## 状态栏（底部数据信息）

### 创建

```python
# 在 __init__ 中，notebook grid 之后
self.rowconfigure(3, weight=0)
status_bar = Frame(self, bg=BG_DEEP, height=26)
status_bar.grid(row=3, column=0, sticky="ew")
self.status_labels = []
for i, (txt, w) in enumerate([("策略", 120), ("股票", 120), ("数据", 200), ("", 1)]):
    lbl = Label(status_bar, text="", font=("Microsoft YaHei", 9),
                fg=FG_MUTED, bg=BG_DEEP, anchor="w", padx=10)
    lbl.grid(row=0, column=i, sticky="w")
    status_bar.columnconfigure(i, weight=0, minsize=w)
    self.status_labels.append(lbl)
```

### 延迟更新（不阻塞启动）

```python
def update_status_bar(self):
    self.after(100, self._do_update_status_bar)  # 延迟100ms，不阻塞首屏

def _do_update_status_bar(self):
    try:
        n_strats = len(self.strategies)
    except Exception:
        n_strats = 0
    self.status_labels[0].config(text=f"📊 策略 {n_strats}")

    try:
        stock_map = load_stock_name_map()
        n_stocks = len(stock_map)
    except Exception:
        n_stocks = 0
    self.status_labels[1].config(text=f"📈 股票 {n_stocks}" if n_stocks else "📈 股票 —")

    try:
        latest = get_latest_data_date()
        self.status_labels[2].config(text=f"📅 数据 ~{latest}" if latest else "📅 数据 无")
    except Exception:
        self.status_labels[2].config(text="📅 数据 读取失败")
```

三个字段各自独立 try-except，一个失败不影响其他。`get_latest_data_date()` 在 `core/data_loader.py` 中。

### 快速读取 CSV 末行日期（不扫描全文件）

```python
def get_latest_data_date():
    """从 CSV 末尾读200字节获取最新交易日期，避免扫描1000万行"""
    csv_path = "data/a_stock_kline_3y.csv"
    try:
        with open(csv_path, "rb") as f:
            f.seek(-200, 2)  # 从末尾往回读200字节
            tail = f.read().decode("utf-8-sig", errors="replace")
            last_line = tail.strip().split("\n")[-1]
            parts = last_line.split(",")
            return parts[2] if len(parts) >= 3 else None
    except Exception:
        return None
```

**绝对不要**逐行遍历 CSV — 980万行数据会阻塞 GUI 数秒。`seek` 到末尾读最后 200 字节，毫秒级完成。

## 滚动条自定义样式

默认 ttk 滚动条在深色主题下几乎隐形。使用 clam 主题后，通过 `Vertical.TScrollbar` 和 `Horizontal.TScrollbar` 样式自定义：

```python
style = ttk.Style()
style.theme_use("clam")
style.configure("Vertical.TScrollbar",
    background="#555a66",        # 滑块（中灰，与深色背景对比明显）
    troughcolor="#1a1d24",       # 轨道（深灰）
    bordercolor="#1a1d24",       # 边框
    arrowcolor="#8b949e",        # 箭头（次文字色）
    relief="flat", borderwidth=0)
style.map("Vertical.TScrollbar",
    background=[("active", ACCENT_BLUE), ("pressed", ACCENT_BLUE_DIM)],  # hover→蓝色
    arrowcolor=[("active", FG_PRIMARY), ("pressed", FG_PRIMARY)])        # hover→白色
```

注意：滑块的 `background` 必须与 `troughcolor` 有明显对比度，否则用户看不清。用户偏好：中等灰度（`#555a66`）滑块 + 深灰（`#1a1d24`）轨道 + 蓝色 hover 反馈。

## 按钮深色偏好

用户要求按钮颜色尽可能地暗（比 ACCENT_*_DIM 更暗），要在可见的前提下调到最深：

| 按钮 | 色值 | 用途 |
|------|------|------|
| `BTN_TEAL` | `#0f3a12` | 全量回测、保存 |
| `BTN_BLUE` | `#0f2d6e` | 运行选中、打开原图 |
| `BTN_PURPLE` | `#2e0f5c` | 自动研发 |
| `BTN_RED` | `#5a0a0a` | 停止 |

按钮 hover 时提亮到对应的 `ACCENT_*_DIM`（如 `ACCENT_TEAL_DIM = "#1a5c24"`）。

**"运行选中"按钮启动状态**：用户要求不要初始禁用，移除 `self.run_sel_btn.config(state="disabled")`。按钮始终处于正常可点击状态。

## 底部两张表的合计条字体

`make_aligned_bar()` 创建的合计标签默认字号 9，用户要求改为 12（实盘持仓底部合计行 12 号 bold）。

顶部实盘策略列表的合计行用 tag_configure 独立控制：`font=("Microsoft YaHei", 12, "bold")`，前景色 `ACCENT_TEAL`。

## 通用修改原则
1. **批量一次改完** — 不要只改一处文字/颜色，全量扫描同类元素一次改完
2. **引擎级修改** — 在核心代码改，不做表面补丁
3. **优先使用已有变量** — `FG_PRIMARY`, `BG_SECONDARY` 等已定义，不要硬编码颜色值
4. **`make_label()` 返回已 `pack()` 的 Label**，不能对其调用 `.grid()` — 如需 grid 布局，直接用 `Label(...).grid(...)`
5. **`make_label()` 的 `bg` 默认是 `BG_PRIMARY`**，不是父容器的背景色。在 `BG_SECONDARY` 容器中直接 `make_label(...)` 会导致标签背景与容器背景不一致（色差）。
6. **`make_button()` 的 `pack_padx` 默认 `(3, 0)`** — 调用时通过关键字参数覆盖

## Treeview 常用模式

### 1. 添加可编辑列
步骤:
- 导入 `from tkinter import simpledialog, messagebox`
- 右键菜单添加 `add_command(label="✏️ 设置XX", command=self.edit_xxx)`
- 绑定 `<Double-1>` 事件，检测目标列后调用编辑方法
- `edit_xxx` 方法中用 `simpledialog.askstring` 弹出输入框
- 校验输入（数字、非负、非空），保存到 `strategies.json`，调用 `self.refresh_live()` 刷新

### 2. 添加合计行
- 遍历完数据后 `self.tree.insert("", END, values=(...), tags=("total",))`
- `tree.tag_configure("total", font=(..., "bold"), foreground=ACCENT_TEAL)`
- 合计值用千分位格式 `f"{total:,.0f}"`，合计行前景色用 `ACCENT_TEAL`

### 股票代码显示：必须补0
NPZ 缓存的股票代码去掉了前导0（`"19"` 实为 `000019`）。**所有股票代码显示路径必须用 `code.zfill(6)` 恢复**，包括 `calc_strat_positions()`、`refresh_combined_positions()`、`refresh_live_strat_detail()` 三处。

## Canvas 事件绑定 — 避免重复积累

`<Configure>` 等事件在 `show_detail` 中被多次调用时（用户快速点击不同策略），`add="+"` 会积累回调：

```python
# ❌ 错误：每次 show_detail 加一次绑定 → N 次 resize 触发 N 次 _render_chart
self.img_canvas.bind("<Configure>", self._on_canvas_resize, add="+")

# ✓ 正确：先解绑再绑，确保只有一个回调
self.img_canvas.unbind("<Configure>")
self.img_canvas.bind("<Configure>", self._on_canvas_resize)
```

**规律**：任何在 `show_detail` / `refresh` 等**可能被多次调用**的方法中绑定的事件，都必须先 `unbind` 再 `bind`，不能用 `add="+"`。

## 策略源码加载崩溃防护（_load_code）

`_load_code` 被 `show_detail` 调用，有两个致命风险：

**风险1：glob 空列表 → IndexError**

```python
candidates = glob.glob(...)
src_path = candidates[0]  # ❌ candidates 可能为空
# ✓ 正确：
src_path = candidates[0] if candidates else None
```

**风险2：文件读取无 try-except → 崩溃抛到 tkinter 事件循环**

```python
# ✓ 正确：读取文件必须包 try-except
if src_path and os.path.exists(src_path):
    try:
        with open(src_path, encoding="utf-8") as f:
            content = f.read()
        self.code_text.insert("1.0", content)
        self.current_src_path = src_path
    except Exception:
        self.code_status.config(text="⚠ 读取失败", fg=ACCENT_RED)
else:
    self.code_status.config(text="⚠ 未找到源码", fg=ACCENT_AMBER)
```

## Regex 批量修改 Python 代码 — 危险警示

**永远不要用 `re.sub` 批量删除 Python 代码行。** 删除一行后，周围行的缩进会残留，导致 `IndentationError`：

```
# re.sub 删除后：
                    self._dev_running = False   # ← 缩进从24空格变成40空格！
```

**推荐做法**：
1. 简单替换（单变量名/颜色值）→ `patch`（唯一匹配优先）
2. 删除带缩进的代码行 → `terminal` 里 `python -c` 逐行读取→判断→跳过→写入
3. 跨多行修改 → 用 `patch` 包足够上下文（至少前后各2行）确保唯一匹配

### 研发日志面板显示发送的提示词

点击"🤖 自动研发"后，dev_text 先显示 prompt 内容，再显示 Hermes 输出：

```python
# 显示研发面板时
self.dev_text.delete("1.0", END)
self.dev_text.insert("1.0", f"📝 发送的提示词:\n{prompt}\n{'─'*50}\n\n")
```

这让用户能看到 Hermes 收到了什么上下文，方便调试 prompt。

### calc_strat_positions — 跨文件委托陷阱（CSV→NPZ 迁移遗漏）

`app.pyw` 和 `core/data_loader.py` 各有一个同名的 `calc_strat_positions()` 函数，返回格式相同但读取格式不同。NPZ 迁移时只改了 `data_loader.py` 的版本，`app.pyw` 的版本被遗漏 → 实盘策略添加后永远"⏳ 持仓计算中..."。

**规则**：`app.pyw` 中的 `calc_strat_positions` 必须委托给 `core.data_loader.calc_strat_positions`，不得保留独立的 CSV 或 NPZ 实现：

```python
def calc_strat_positions(folder):
    from core.data_loader import calc_strat_positions as _npz_loader
    return _npz_loader(folder)
```

`data_loader.py` 自包含（有自己的 `RESULTS`、`load_stock_name_map`、`_build_stock_map_from_npz`），不会产生循环导入。

**预防**：修改 `data_loader.py` 中 `calc_strat_positions` 时，同步检查 `app.pyw` 中是否有重复函数需要更新或委托。

**JSON 陈旧数据恢复**：如果策略是在数据格式迁移前添加到实盘的，`live/strategies.json` 中存有 `positions: null`（永远不更新）。修复步骤：
1. 确保策略已重新运行过（NPZ 文件存在）
2. 手动更新 JSON：`calc_strat_positions(folder)` → 写入 `s["positions"] = pos`
3. 在实盘标签页点"🔄 刷新"即可显示
注意：仅修复 NPZ 文件不够，JSON 不会自动重试失败的持仓计算。这是由 `add_selected_to_live` 的流程决定的——计算一次不成功就永远不重试。`_on_close` 清理

`add_selected_to_live()` 中的 `poll()` 函数用一个 `result = {}` dict 在 worker 线程和 UI 轮询间通信。原始代码中 `"error" in result` 分支只 `return` 不显示任何错误 → 策略的 `positions` 永远为 `None` → 用户永远看到"⏳ 持仓计算中..."。

```python
# ❌ 错误：静默吞掉
if "error" in result:
    return

# ✓ 正确：显示错误到界面
if "error" in result:
    self.sp_title_lbl.config(text=f"⚠ {name}: {result['error']}", fg=ACCENT_GOLD)
    self.sp_tree.delete(*self.sp_tree.get_children())
    self.sp_tree.insert("", END, values=("", f"⚠ {result['error']}", "", "", "", "", ""))
    return
```

同样，`calc_strat_positions` 返回 `None`（文件不存在/数据为空）也必须视为错误，而不是静默写回 `None`：

```python
def worker():
    try:
        pos = calc_strat_positions(folder)
        if pos is None:
            result["error"] = f"未找到持仓数据（position_matrix.npz 不存在），请重新运行该策略的回测"
        else:
            result["positions"] = pos
    except Exception as e:
        result["error"] = str(e)
```

**原则**：所有后台线程的错误必须在 UI 上显示，不能静默 return。常见无声失败点：`calc_strat_positions` None 返回、NPZ 文件缺失、JSON 解析异常。

### low_ir 策略源码归档（右键菜单）

`scan_strategies()` 默认只扫 `strategies/*.py`（顶层），子目录自动排除。策略移到 `strategies/low_ir/` 后不再显示。

**右键菜单 "⬇ 移入 low_ir"**：将选中策略的 `.py` 源码从 `strategies/` 移到 `strategies/low_ir/`，回测结果 `results/` 不动。

```python
def move_selected_to_low_ir(self):
    sel = self.tree.selection()
    if not sel: return
    item = self.tree.item(sel[0])
    name = item["values"][0]
    src_path = next((e[3] for e in self.strategies if e[0] == name), None)
    if not src_path or not os.path.exists(src_path): return
    import shutil
    dst_dir = os.path.join(STRATEGIES_DIR, "low_ir")
    os.makedirs(dst_dir, exist_ok=True)
    shutil.move(src_path, os.path.join(dst_dir, os.path.basename(src_path)))
    self.refresh()
```

**注意**：只移源码文件，不移 results 结果文件夹。`scan_strategies()` 用 `glob(STRATEGIES_DIR, "*.py")` 只扫顶层，移入 `low_ir/` 后自动排除。不需要在 `scan_strategies` 中加排除逻辑。

### 研发日志面板开发字体
研发区域(`dev_text`)使用等宽字体，字号应偏大以便阅读日志输出：
```python
self.dev_text = Text(..., font=("Consolas", 13), ...)
```
之前用 `Consolas 9` 太小，改到 `13` 后阅读性显著提升。

### 列定义模式
```python
STRAT_COLS = [
    ("key", "中文列名", width),
    ...
]
self.tree = ttk.Treeview(..., columns=("key", ...), show="headings")
for cid, ctext, cwidth in STRAT_COLS:
    self.tree.heading(cid, text=ctext)
    self.tree.column(cid, width=cwidth, minwidth=cwidth, anchor="center")
```

### 双击事件崩溃防护（重要）
Treeview 绑定 `<Double-1>` 时必须加多层守卫，否则双击空白/合计行/行间缝隙会导致程序闪退。
三大守卫: `identify_row` 先行定位 → 跳过合计/空行 → try/except 兜底

### 运行选中策略的终端自动关闭 — 不要用 shell=True

`run_selected()` 使用 `subprocess.Popen` 在新终端中运行策略：

```python
def run_selected(self):
    proc = subprocess.Popen(
        [sys.executable, src],
        cwd=d,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    # 跟踪进程供 _on_close 清理
    if not hasattr(self, "_sel_procs"):
        self._sel_procs = []
    self._sel_procs.append(proc)
    def wait_and_refresh():
        proc.wait()
        # 从跟踪列表中移除已结束的进程
        try: self._sel_procs.remove(proc)
        except ValueError: pass
        self.after(500, self.refresh)
    threading.Thread(target=wait_and_refresh, daemon=True).start()
```

**底线**：`shell=True` + `CREATE_NEW_CONSOLE` 产生孤儿 cmd.exe 进程。必须改用 `Popen([sys.executable, src], cwd=d, creationflags=CREATE_NEW_CONSOLE)` 直接启动 python.exe。新办法：`cwd=d` 替代 `cd /d`，命令列表替代 shell 字符串，零 cmd.exe 中介。

**进程跟踪**：`run_selected` 的 proc 对象必须入 `self._sel_procs` 列表供 `_on_close` 清理。proc 结束后必须从列表中移除（`remove(proc)`）防止列表无限增长。初始化：`self._sel_procs = []` 放在 `__init__` 中。

### _on_close — 多类型进程清理

```python
def _on_close(self):
    import subprocess
    # 清理实盘运行进程
    if hasattr(self, "_live_procs"):
        for p in self._live_procs:
            if p.poll() is None:
                try: p.kill()
                except: pass
    # 清理 run_selected 子进程
    if hasattr(self, "_sel_procs"):
        for p in self._sel_procs:
            if p.poll() is None:
                try: p.kill()
                except: pass
    # 清理 Hermes 研发子进程
    if hasattr(self, "_dev_proc") and self._dev_proc:
        if self._dev_proc.poll() is None:
            try: self._dev_proc.kill()
            except: pass
    self.destroy()
```

关闭窗口时必须清理所有子进程类别：`_live_procs`（实盘）、`_sel_procs`（运行选中）、`_dev_proc`（研发）。漏掉任何一类都会导致关闭后遗留孤儿进程。

**新增子进程类型的检查清单**：每在 app.pyw 中新增一个 `subprocess.Popen` 调用，必须同步做三件事：
1. **创建跟踪列表** — `__init__` 中初始化列表（如 `self._xxx_procs = []`）
2. **入队+出队** — Popen 后 `append(proc)`，proc 结束后 `.remove(proc)`
3. **关闭清理** — `_on_close()` 中遍历该列表杀进程
缺少任意一步 → 长期运行后列表无限增长，或关闭后遗留孤儿进程。

### matplotlib figure 泄漏防护（in-process 运行）

`ThreadPoolExecutor` + `importlib` 模式下多条策略在同进程运行，matplotlib figure 必须彻底关闭：

**策略级别**：`_run_one()` 的 finally 块加 `plt.close('all')`

```python
def _run_one(src_path):
    try:
        ...
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
    except Exception:
        pass
    finally:
        import matplotlib.pyplot as _plt
        _plt.close('all')  # 防止异常退出残留 figure
```

**回测引擎级别**：`plot_and_save()` 用 `plt.close(fig)` 精确关闭 + `plt.close('all')` 兜底：

```python
fig, axes = plt.subplots(3, 1, figsize=(14, 10), ...)
_fig = fig   # 给 finally 块引用
...
plt.close(_fig)
plt.close('all')
```

### 实盘策略表「最后更新」列

用策略结果文件夹的修改时间作为最后更新时间：

```python
# STRAT_COLS 中：("last_update","最后更新",110)
# columns=("name","status","capital_pct","signal","cum_return","last_update")

# refresh_live() 中：
from datetime import datetime
for s in strategies:
    folder = s.get("folder", "")
    update_time = ""
    if folder:
        fpath = os.path.join(RESULTS, folder)
        if os.path.isdir(fpath):
            mtime = os.path.getmtime(fpath)
            update_time = datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
```

注意：`RESULTS` 已在顶层通过 `os.path.expanduser` 展开，不需要再次 `expanduser`。`datetime` 导入放函数顶部避免重复导入。

## ▶ 运行全部实盘 — 线程池模式（2026-05-17 重构）

`_run_all_live_strategies()` 从 `subprocess.Popen` 改为 **`ThreadPoolExecutor` + `importlib`** 在同进程内执行：

```python
def _run_all_live_strategies(self):
    from concurrent.futures import ThreadPoolExecutor
    import importlib.util, io, contextlib

    max_workers = max(1, min(len(src_files), os.cpu_count() // 2 or 4))
    pool = ThreadPoolExecutor(max_workers=max_workers)
    futures = [pool.submit(_run_one, src) for src in src_files]

    def wait_all():
        try:
            for f in futures: f.result()
        finally:
            pool.shutdown(wait=False)
            self._live_running = False
            self.after(0, lambda: self.run_live_btn.config(
                text="▶ 运行全部实盘", state="normal"))
            self.after(500, self.refresh_live)

    threading.Thread(target=wait_all, daemon=True).start()
```

**关键细节**：
- `max_workers = cpu_count // 2` — 留一半给 numpy + IO 带宽
- 按钮状态管理在 `wait_all()` 的 `finally` 块内，不在外层 `run_all_live()` 里 —— 否则按钮会在策略提交完但未跑完时提前恢复
- `pool.shutdown(wait=False)` + `f.result()` 手动管理生命周期，不阻塞UI
- `io.StringIO()` 吞噬 stdout
- 单策略异常不影响其他
- `_run_one` 的 finally 块必须包含 `plt.close('all')` 防止 figure 泄漏

**变化原因**：旧版开多个python子进程分别加载NPZ，重复IO浪费。新方式同进程运行，NPZ缓存OS共享，启动快约5倍。

## ◀ 停止按钮 — 保持自定义颜色

停止按钮（和其他需要保持定制颜色的按钮）**永远不要设 `state="disabled"`**：

```python
# ❌ 错误：disabled 后 tkinter 覆盖 bg 为灰色
self.stop_btn.config(state="disabled")

# ✓ 正确：永远保持红色，回调内部判断是否可执行
# 按钮创建时不设 state
# stop_dev() 中不做 state 切换
# auto_develop() 中不做 state 切换
```

Tkinter Button 在 `state="disabled"` 后自动覆盖 `bg` 为系统灰色（`disabledforeground` 可设但 `disabledbackground` 不存在）。用户对深色主题要求严格（暗红 `#5a0a0a` → 禁用后变灰非常难看）。

**替代方案**：按钮始终 `state="normal"`，在回调函数内部守卫：
```python
def stop_dev(self):
    if hasattr(self, "_dev_proc") and self._dev_proc and not self._dev_proc.poll():
        self._dev_proc.kill()  # 有进程才杀
    # 没有进程时点击无副作用
```

这条适用于所有深色主题的自定义颜色按钮。如果仍然需要视觉上"不可点击"的反馈，改为改变按钮的 `bg` 或文字，不要用 `state`。

## 持仓矩阵 NPZ（回测结果）

2026-05-17 起，`position_matrix.csv` 被替换为 `position_matrix.npz`：

| 格式 | 大小（A320 示例） | 写入代码 | 读取代码 |
|------|-------------------|---------|---------|
| CSV (旧) | 7.5MB | `Visualizer.plot_and_save()` → `df.to_csv()` | `calc_strat_positions()` 逐行解析 |
| NPZ (新) | **3.1MB** | `engine.save_position_matrix()` | `calc_strat_positions()` → `np.load()` |

**文件输出**（`backtest_utils.py` ~1420行）：复用已有的 `save_position_matrix()` 方法：

```python
engine.save_position_matrix(output_dir, codes=codes_arr, dates=dates_arr)
```

**文件读取**（`data_loader.py` `calc_strat_positions()`）：改为 `np.load`：

```python
d = np.load("position_matrix.npz", allow_pickle=True)
pos = d["pos_value"]  # (n_stocks, n_days), float32
codes = d["codes"]    # 股票代码数组
last_pos = pos[:, -1]  # 最后一天持仓
```

**清理**：旧 CSV 删除（find -delete 扫描 results/ 下所有 position_matrix.csv）。

## 数据持久化
- 实盘数据存 `live/strategies.json`，函数 `load_live_strategies()` / `save_live_strategies()`
- 修改后立即调 `save_live_strategies()` + `self.refresh_live()`
- 默认分配金额 `"100000"`（10万），在 `add_selected_to_live()` 中设置

## 鲁棒数字解析（从 JSON 字段解析数值）
```python
raw = (s.get("capital_pct") or "").strip().replace(",", "")
try:
    val = float(raw) if raw else 0
except (ValueError, TypeError):
    val = 0
```
兼容: 字段缺失 → `""` → 0 | None → `""` → 0 | "100,000" → "100000" | " 1000 " → "1000" | "abc" → ValueError → 0

## 组合持仓逐步缩仓算法

**背景**: 用户资金量小，纯等比缩放会把所有股票缩到 <1万然后全部过滤掉。

### 算法：逐步缩仓（从大到小逐只加入）

```
1. 按原始市值从大到小排序所有股票
2. k=1 开始：取前k只最大股票
3. 计算 scale = 总分配金额 / 前k只总金额
4. 检查前k只每只取整手数后的实际金额是否 ≥ 1万
   → 全部满足：保存这组结果，k+=1，继续尝试
   → 有低于1万的：停止，用上一组(k-1)的结果
5. 最终选中的股票集等比缩放对齐总分配金额
```

关键：阈值检查用 `actual_amt`（取整后实际金额），不是 `scaled_amt`（理论金额）。`int()` 向下截断后实际金额可能远低于阈值。

## 防止出错
- 操作前先搜索 `capital_pct` / 目标字段在全局的使用位置，确认不影响下单逻辑
- `style.map("Treeview", background=[("selected", TABLE_SELECT)])` — Treeview 选中行背景通过 style.map 控制，不是通过 TABLE_SELECT 变量自动生效的，两个地方都要改
- 修改 Treeview 全局样式会影响所有 treeview（结果表、策略表、持仓表），需要确认是否预期
- `refresh_live()` 会删除所有行重建，合计行也在其中，不需要额外清理
- 重构后按钮跑到 `_build_live_tab` 方法里了，搜索 `self.auto_btn =` 定位实际创建位置
- 如果按钮点了没反应但没有报错：先检查 dev_frame 的几何管理器是否统一（place 不能和 grid 混用）
- **永远不要用 regex 批量修改 Python 代码** — 删除一行代码后，周围行的缩进会残留，导致 `IndentationError`。特别是 `stop_btn.config(state="disabled")` 这种在多个缩进层级出现的行，用 `re.sub` 全量替换会打乱周围行的缩进。改用 `patch`（old_string/new_string 逐段匹配）或 `terminal` 里 `python -c` 逐行处理。
- **批量改 Python 代码的推荐方式**：1) 简单替换用 `patch`（唯一匹配优先） 2) 涉及缩进删除的操作用 `terminal` 中 python 逐行读取→判断→写入 3) 绝对不要用 `re.sub` 跨多行匹配删除带缩进的代码行

## 实盘策略表头部按钮（刷新 + 运行全部实盘）

实盘标签页头部增加两个按钮：🔄 刷新（仅刷新列表）和 ▶ 运行全部实盘（后台执行策略，完成后自动刷新）。

```python
# _build_live_tab() 中 hdr 部分：
hdr = Frame(strat_sec, bg=BG_SECONDARY)
hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
Label(hdr, text="📋 实盘策略", font=("Microsoft YaHei", 12, "bold"),
      fg=FG_PRIMARY, bg=BG_SECONDARY).pack(side=LEFT)
btn_frame = Frame(hdr, bg=BG_SECONDARY)
btn_frame.pack(side=RIGHT)
Button(btn_frame, text="🔄 刷新", font=("Microsoft YaHei", 9),
       bg=BTN_BLUE, fg=FG_PRIMARY, bd=0, padx=8, pady=2,
       cursor="hand2", command=self.refresh_live).pack(side=LEFT, padx=(0,3))
self.run_live_btn = Button(btn_frame, text="▶ 运行全部实盘", font=("Microsoft YaHei", 9),
       bg=BTN_TEAL, fg=FG_PRIMARY, bd=0, padx=8, pady=2,
       cursor="hand2", command=self.run_all_live)
self.run_live_btn.pack(side=LEFT)
```

按钮回调 `run_all_live()` 需管理按钮状态防止重复点击：

```python
def run_all_live(self):
    if getattr(self, "_live_running", False):
        return
    self.run_live_btn.config(text="⏳ 运行中...", state="disabled")
    self.update()
    import threading
    threading.Thread(target=self._run_all_live_strategies, daemon=True).start()
```

注意：按钮状态恢复在 `_run_all_live_strategies` 内部的 `wait_all()` finally 块中处理，不在 `run_all_live` 里。详见「▶ 运行全部实盘 — 线程池模式」章节。

## 实盘策略 — 零自动执行偏好

用户要求 **完全手动控制** 实盘策略执行，禁止任何形式的自动触发：

- ❌ 程序启动时自动运行实盘（已移除 `_start_live_scheduler` 中的 `startup_run` 线程）
- ❌ 每晚22:00定时调度执行（已移除 `_schedule_live_run` 和 `_on_live_scheduled_run` 方法）
- ❌ 任何定时器/调度器相关的自动执行（已移除 `_live_timer` 及其在 `_on_close` 中的清理）
- ✅ 用户通过实盘标签页的按钮手动触发 `_run_all_live_strategies()`

**相关代码完全移除**：`_start_live_scheduler`、`_schedule_live_run`、`_on_live_scheduled_run` 三个方法已彻底删除，`__init__` 中的调用也已移除。如需恢复调度，需重新实现定时逻辑。

## ⚠️ 关键原则：非必要不修改核心功能

本会话中反复出现的教训——**不要随意改动以下关键部分，除非得到用户明确指示**：

1. **布局几何管理器** — `pack()` / `grid()` / `place()` 不能互相替代或混用。重构时保留原始管理器类型，只微调参数。
2. **按钮命令回调** — `command=self.xxx` 的绑定关系、按钮的 `state` 初始状态、按钮集群的排列顺序，都不应在非相关的重构中改变。
3. **事件处理器** — `<<TreeviewSelect>>`、`<Button-3>` 等事件的绑定方法名和签名，即使重构到新方法中也必须保持原有行为。
4. **子进程调用方式** — `subprocess.Popen` 的参数（shell/creationflags/env/args 格式）与特定运行环境强绑定，改变可能导致功能完全失效。
5. **数据读写路径** — `LIVE_DIR`、`RESULTS`、`STRATEGIES_DIR`、`DATA_DIR` 的解析方式（`__file__` 相对路径 vs `expanduser` 绝对路径）不能随意改变。

**黄金法则**：如果重构目标是减少重复代码/拆分模块，只改导入路径和函数签名，不改调用逻辑、布局顺序、事件绑定。