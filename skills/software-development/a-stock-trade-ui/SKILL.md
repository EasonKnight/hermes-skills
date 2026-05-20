---
name: a-stock-trade-ui
description: GUI 修改规范与常用模式 — tkinter Treeview/Text/Notebook 在 a_stock_trade 项目中的修改套路
trigger: 用户要求修改 app.pyw 界面（列名、可编辑单元格、合计行、配色、字体等）
---

# A股量化桌面平台 — GUI 修改指南

## 隐藏控制台窗口（双击 .pyw 仍出终端时的兜底）

某些 Windows 系统上 `.pyw` 文件的关联可能是 `python.exe`（而非 `pythonw.exe`），双击后会同时弹出 cmd 终端窗口。在文件最开头添加：

```python
# 隐藏控制台窗口（双击 .pyw 仍出终端时的兜底）
try:
    import ctypes
    ctypes.windll.user32.ShowWindow(
        ctypes.windll.kernel32.GetConsoleWindow(), 0)
except Exception:
    pass
```

**为什么不用 `FreeConsole()`**：`FreeConsole()` 会分离进程的控制台，导致从 cmd 启动时也看不到输出。`ShowWindow(handle, 0)` 只是隐藏窗口，不改变控制台关联状态。`GetConsoleWindow()` 在 `pythonw.exe` 下返回 0，`ShowWindow(0, 0)` 是空操作。

## 高 DPI 支持（Windows 高清屏幕）

tkinter 默认不感知系统 DPI 缩放，在 >100% 缩放下会位图拉伸导致模糊。

### 第一步：进程级 DPI 感知（文件顶部，tkinter 导入前）

```python
# 必须在 tkinter 导入前设置
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()   # Fallback
    except Exception:
        pass
```

`SetProcessDpiAwareness(2)` = `PROCESS_PER_MONITOR_DPI_AWARE`，每个显示器独立 DPI。Windows 7/8 回退到 `SetProcessDPIAware()`。

### 第二步：tk 缩放因子（App.__init__ 中）

```python
# 获取窗口 DPI，设置 tk 渲染缩放
try:
    import ctypes
    dpi = ctypes.windll.user32.GetDpiForWindow(self.winfo_id())
    scaling = dpi / 96.0 * 1.35  # 1.35 = 额外放大系数
    self.tk.call("tk", "scaling", scaling)
except Exception:
    pass
```

- 96 DPI = 100% 缩放。1.35 倍额外放大使界面更大更舒适
- `GetDpiForWindow` 需要 Windows 10 1607+，否则抛异常被 except 捕获
- `tk scaling` 必须在 Tk 实例创建后调用（`super().__init__()` 之后）

### 字体渲染说明

`Noto Sans SC` 使用 DirectWrite 渲染，比 `GDI` 渲染的 `Microsoft YaHei` 更锐利清晰。配合 DPI 感知 + tk scaling 后，小字号文字不再模糊。

## 字体约定 — Noto Sans SC Medium / Light

```
标题/区头（16/13/12/11） → "Noto Sans SC Medium"（清晰锐利，不加 bold）
正文/按钮/状态栏（10/9） → "Noto Sans SC Light"（纤细清秀）
TreeView/合计行/bar 标签（10/9） → "Noto Sans SC Light"
```

**历史演变**：
- `Microsoft YaHei`（全项目初始）→ Microsoft YaHei UI / UI Light（稍细）→ **Noto Sans SC Medium / Light**（最锐利）

**字号调整对照表**（Noto 字形比 YaHei 视觉上大一号，需下调）：

| 原 YaHei UI 字号 | 替换为 Noto 字号 | 适用场景 |
|------------------|-----------------|---------|
| 18 | 16 | 主标题（顶部） |
| 14 | 13 | 副标题/详情头 |
| 13 | 12 | 研发状态标签 |
| 12 | 11 | 区头标题/底部合计条 |
| 11 | 11（Light） | 余额面板文字 |

**规则**：新增 UI 元素必须用 Noto Sans SC 系列，不要回退到 Microsoft YaHei。标题用 Medium（不加 bold），正文用 Light。

**不在 DPI 感知环境下的表现**：关闭 DPI 感知后，tkinter 由 Windows 位图拉伸，即使是 Noto 也模糊。必须先做高 DPI 感知（文件顶部 + App.__init__），字体清晰度才有意义。

## 代码模块化（core/ 目录拆分）— 最终架构

2026-05-19~20 完成模块化重构，将原先全部集中在 `app.pyw` 的代码拆分为 `core/` 目录下的模块：

| 文件 | 内容 | 依赖 |
|------|------|------|
| `app.pyw` | App 主类（__init__ / 布局 / 事件处理 / 回测面板） | 以下全部 |
| `core/app_config.py` | 颜色常量 / 路径常量 | 无 |
| `core/app_utils.py` | 独立函数（策略扫描/统计读取/DeepSeek/标签解析） | app_config |
| `core/app_live.py` | `AppLiveMixin` — 所有实盘方法（~300行） | app_config, app_utils |
| `core/app_balance.py` | `BalanceWindow` — 余额查询弹窗 | app_config |

### Pitfall: _parse_label — 必须读取完整文件内容

`scan_strategies()` 通过 `_parse_label()` 从策略源码中提取 LABEL 元数据。**必须读取整个文件内容，不能只读第一行**：

```python
# ❌ 错误：只读第一行 — 老策略有 shebang + docstring，LABEL 不在第1行
with open(src_path) as f:
    first_line = f.readline()
match = re.search(r'LABEL\s*=[\"\\'](.*?)[\"\\']', first_line)

# ✓ 正确：读取全文
with open(src_path, encoding=\"utf-8\") as f:
    content = f.read()
match = re.search(r'LABEL\s*=[\"\\'](.*?)[\"\\']', content, re.IGNORECASE)
```

正则表达式必须支持**单引号和双引号**两种写法：`LABEL\s*=[\"\\'](.*?)[\"\\']`

**症状**：`_parse_label` 返回空字符串 → `scan_strategies` 的 `label` 为空 → `populate_tree()` 中 `entry[2]` 为空 → 策略名称列显示为策略文件名而非中文标签。

**迁移时检查清单**（函数从 app.pyw 移到 core/app_utils.py 时）：
1. 数据读取方式（DictReader vs reader）
2. 文件读取范围（全文 vs 首行）
3. 引号类型（单/双引号）
4. 错误处理（return "" vs raise）
5. 编码（utf-8 vs utf-8-sig）

**mixin 模式**：`AppLiveMixin` 是一个独立的类，`app.pyw` 中的 `class App(AppLiveMixin, Tk)` 多继承。mixin 方法通过 `self.*` 引用 App 实例的属性（如 `self.strat_tree`、`self.pos_tree`），这些属性在 App 主类的 `_build_live_tab()` 中创建。

**增量清理原则**：不要一次性删除 `app.pyw` 中的旧函数。先确保 `core/xxx.py` 中的新函数正确，再将旧函数逐段删除并改为 `from core.xxx import ...`。备份在 `bak/app_bak_pre_split.pyw`。

## API （akshare）基础知识

### 实时行情：新浪源（免费、无需注册）

```python
import akshare as ak
df = ak.stock_zh_a_spot()  # 全量~5500只，14字段
# 列: 代码、名称、最新价、涨跌额、涨跌幅、买入、卖出、昨收、今开、最高、最低、成交量、成交额、时间戳
```

该接口内部调用 `http://hq.sinajs.cn/list=...` 分批轮询约 69 次获取全量数据，耗时约 15-20 秒。
如果只需少数股票，可以绕过 akshare 直接调用新浪 API（见 references/realtime-stock-quotes.md）。

### 基本面数据：通用版 vs THS 版

```python
# ❌ THS 版（仅覆盖 ~50% A股，其余返回 None → 'NoneType' has no attribute 'string'）
df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")

# ✓ 通用版（覆盖全部 A 股，但格式不同：行=指标名，列=报告期）
df = ak.stock_financial_abstract(symbol=code)
```

通用版返回格式需转置：指标名在行上，日期在列上。`KEY_FIELDS` 字段名不同（2026-05-19 切换后更新）：

| 旧（THS） | 新（通用版） |
|-----------|-------------|
| `销售毛利率` | `毛利率` |
| `营业总收入同比增长率` | `营业总收入增长率` |
| `净利润同比增长率` | `归属母公司净利润增长率` |
| `净资产收益率` | `净资产收益率(ROE)` |

转置逻辑见 `core/update_fundamentals.py` 中的 `fetch_one()`：

```python
# 1. 去重（同一指标名可能出现在多个类别中，取首次出现）
df = df.drop_duplicates(subset=["指标"], keep="first")

# 2. 选出 KEY_FIELDS 中存在的指标
available = [c for c in KEY_FIELDS if c in df["指标"].values]
df_filt = df[df["指标"].isin(available)]

# 3. 转置：遍历每个指标的每一期，收集 {报告期, 指标名: 值} 记录
date_cols = [c for c in df_filt.columns if c not in ("选项", "指标")]
records = []
for _, row in df_filt.iterrows():
    for col in date_cols:
        try: val = float(row[col])
        except (ValueError, TypeError): val = None
        records.append({"报告期": col, row["指标"]: val})

# 4. 按报告期聚合 → 每期一条记录
records_df = pd.DataFrame(records)
pivoted = records_df.groupby("报告期", as_index=False).first()
pivoted = pivoted.ffill().fillna(0.0)
```

注意：`pandas` 较新版本不支持 `fillna(method='ffill')`，需用 `ffill()` 方法。
- `'销售毛利率'`（THS）→ `'毛利率'`（通用）
- `'营业总收入同比增长率'`（THS）→ `'营业总收入增长率'`（通用）
- `'净利润同比增长率'`（THS）→ `'归属母公司净利润增长率'`（通用）
- `'净资产收益率'`（THS）→ `'净资产收益率(ROE)'`（通用）

转置逻辑见 `core/update_fundamentals.py` 中的 `fetch_one()`。

### A 股有效代码前缀

排除 B 股（200xxx/900xxx）、债券、基金等非 A 股品种：

```python
A_PREFIXES = {"000","001","002","003","300","301","302","303",
              "600","601","603","605","688"}
```

在 `get_all_stocks()` 和 `_build_cache()` 两处都必须过滤。未过滤时 NPZ 含 6691 只（含 1450 非 A），过滤后 5241 只。

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

## 实盘标签页布局 — 左右双栏

`_build_live_tab()` 从 **垂直三段 PanedWindow** 改为 **左右双栏 Frame**：

```
tab.columnconfigure(0, weight=3)  # 左栏 3份
tab.columnconfigure(1, weight=2)  # 右栏 2份
tab.rowconfigure(0, weight=1)

left_col = Frame(tab)   # 左: 实盘策略 + 策略持仓（纵向堆叠）
right_col = Frame(tab)  # 右: 组合持仓（独占）
```

### 左栏
```python
left_col.rowconfigure(0, weight=2)  # 实盘策略占 2份
left_col.rowconfigure(1, weight=1)  # 策略持仓占 1份

strat_sec = make_section(left_col)
strat_sec.grid(row=0, column=0, sticky="nsew")

sp_sec = make_section(left_col)
sp_sec.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
```

### 右栏
```python
pos_sec = make_section(right_col)
pos_sec.grid(row=0, column=0, sticky="nsew")
```

### 变更要点
- 移除 `ttk.PanedWindow`，改用 `Frame` + `grid`
- 左实盘策略列表和下方策略持仓用 `rowconfigure` 分割
- 右组合持仓独占一列，底部合计条位置不变
- 按钮（刷新/运行全部实盘）仍在左栏策略表头部
- 布局数据在 `tab`（标签页 Frame）上配置，不是 `self` 上

### 详情标题栏删除（2026-05-20）

用户认为 `detail_title`（"选择左侧策略查看详情" / "📈 策略名"）占用纵向空间，已将其完全移除。涉及四处修改：

1. **创建代码删除** — `_build_backtest_tab()` 中删除 `self.detail_title` 和分隔 Frame 的创建
2. **grid 行号调整** — notebook 从 row 3 → row 2
3. **clear_detail 中删除** — 删除 `self.detail_title.config(text="选择左侧策略查看详情")`
4. **show_detail 中删除** — 删除 `self.detail_title.config(text=f"📈  {name}")`
5. **rowconfigure 更新** — `right.rowconfigure(2, weight=1)`（释放一行空间给 notebook）

### 底部指标栏 + 打开原图按钮完全移除（2026-05-20）

`btm`（底部指标文本框 + "打开原图"按钮）占用最后一行的纵向空间，2026-05-20 完全移除：

**删除内容**：
- `btm = Frame(right)` + `stats_text`（指标文本）+ `open_btn`（打开原图按钮）的创建代码
- `STAT_KEYS` 遍历渲染指标的 `show_detail` 代码段
- `self.stats_text.delete()` / `self.stats_text.insert()` 调用（clear_detail + show_detail）
- `self.open_btn.config(state=...)` 调用
- `open_chart()` 方法

**效果**：notebook 独占 row 2 到底部全部空间，不再被底部栏压缩。

### 布局重构 — 安全删除 UI 元素清单（2026-05-20 实战教训）

删除一个 UI 元素（Frame/Text/Button）时，**不能只删创建代码**，必须同步删除/重写所有对该元素的引用。半删（保留引用但删 widget）导致 `AttributeError` 或沉默失效。

**删除清单**（每删一个元素逐项检查）：

```
□ 1. 创建代码（如 `btm = Frame(right)` + children + grid/pack）
□ 2. clear_detail 中的清除（`self.xxx.delete()` / `self.xxx.config(...)`）
□ 3. show_detail 中的写入（`self.xxx.insert()` / `self.xxx.config(...)`）
□ 4. 方法本身（如 `open_chart()` — 删按钮后不再被调用）
□ 5. 构造器/__init__ 中的初始化（`self.xxx = ...`）
□ 6. 其他方法中的引用（`self.xxx.config(...)` / `self.xxx.xxx()`）
```

**常见遗漏**：只做第 1 步，忘记 2~6 → 程序不报错（因为方法不被调用）但功能无声损坏。

**row 号连锁调整** — 删除 grid 行后，所有依赖原行号的引用必须同步更新：

```
□ `widget.grid(row=N, ...)` — 下方所有行的 N 减 1
□ `container.rowconfigure(N, weight=W)` — 指向正确的行号
□ 旧行的 weight 必须迁移到新行（否则新行 weight=0 → widget 高度为 0）
```

**排查链**（从功能失效回溯到行号问题）：当删除一个 grid 行后图表（或任意 notebook 内容）不显示时：

1. 确认 notebook.grid(row=N) 的 N 是否正确（删行后 N 应减 1）
2. 确认 `container.rowconfigure(N, weight=W)` 的 N 是否正确
3. 如果 rowconfigure 指向已删除的行，notebook 所在行 weight=0 → 高度=0 → canvas `winfo_height() - 16` 返回负数 → `if ch < 100: return` 提前返回 → 图片不显示
4. 通过 `print(self.img_canvas.winfo_height())` 验证 canvas 高度

**实战案例**（2026-05-20 删除 btm 底部指标栏）：
- ❌ 删了 btm 创建代码（Frame + stats_text + open_btn）→ notebook 从 row 3 上移到 row 2
- ❌ 但 `right.rowconfigure(3, weight=1)` 没改成 `rowconfigure(2, weight=1)`
- ❌ → notebook 所在行 weight=0 → 高度为 0 → 图片画布 `winfo_height() - 16` 返回负数
- ❌ → `_render_chart()` 中 `if ch < 100: return` 提前返回 → 图片不显示
- ❌ 还误删了 `open_btn.config(state=...)` 的引用但没有删 `open_btn` 创建 → crash
- ✅ 修复：改 rowconfigure + 补全删除清单

**黄金法则**：布局重构每删一个 UI 元素，跑一遍 checklist。不信任 grep 结果——grep 只找创建代码，不找引用。

### 净值曲线图拉伸填满画布（2026-05-20）

`_render_chart()` 中从等比例缩放 + 居中改为拉伸填满：

```python
# 之前：保持比例，居中
ratio = min(cw / img.width, ch / img.height)
new_w = max(200, int(img.width * ratio))
new_h = max(150, int(img.height * ratio))
img_small = img.resize((new_w, new_h), Image.LANCZOS)
x = (cw - new_w) // 2 + 8   # 居中偏移
y = (ch - new_h) // 2 + 8

# 之后：拉伸填满，左上对齐
new_w = max(200, cw)
new_h = max(150, ch)
img_small = img.resize((new_w, new_h), Image.LANCZOS)
self.img_canvas.create_image(8, 8, anchor="nw", image=self._tk_img)  # 左上对齐
```

去掉了 `ratio` 计算和居中偏移，直接以画布尺寸 `cw x ch`（减去16px padding）为目标尺寸进行 resize。图片可能变形，但充分利用了所有显示空间。`anchor="nw"` + `(8, 8)` 坐标确保图片紧贴 padding 边缘。

## 项目文件结构（2026-05-20 模块化重构 — core/ 拆分）

2026-05-19~20 完成第二次重构：将 `app.pyw` 中的常量、工具函数、实盘方法拆分到 `core/` 目录下的模块。`app.pyw` 从 ~1828 行缩减到 ~1309 行。

```
a_stock_trade/
├── app.pyw                     # 1309行：App 主类 + 布局 + 回测面板 + 交互方法
├── core/
│   ├── app_config.py           # 颜色常量 / 路径常量（无依赖）
│   ├── app_utils.py            # 独立函数：scan_strategies, read_stats, _parse_label,
│   │                           #   load_stock_name_map, load_live_strategies,
│   │                           #   fetch_deepseek_balance, estimate_deepseek_consumption
│   ├── app_live.py             # AppLiveMixin — 实盘刷新/实时行情/组合持仓/CSV导出
│   ├── app_balance.py          # BalanceWindow — DeepSeek 余额查询弹窗
│   ├── data_loader.py          # NPZ 加载 / 日线 / 基本面 / calc_strat_positions
│   ├── update_data.py          # 数据增量更新 + NPZ 缓存构建
│   ├── update_fundamentals.py  # 基本面数据下载
│   └── update_data.bat         # 计划任务批处理入口
├── strategies/                 # 策略源码
│   └── low_ir/                 # 低夏普移入
├── results/                    # 回测结果（每策略一个子文件夹）
├── live/
│   └── strategies.json         # 实盘策略配置
├── data/                       # NPZ / CSV 数据
└── bak/
    └── app_bak_pre_split.pyw   # 备份（拆分前完整版）
```

## 改什么取决于修改目标（2026-05 模块化重构后）

| 要改什么 | 位置 |
|----------|------|
| 颜色/路径常量 | `core/app_config.py` 顶部 |
| 按钮行为/排列 | `app.pyw` 中 `_build_backtest_tab()` 的按钮循环 |
| 回测策略列表 + 排序 | `app.pyw` 中 `populate_tree()` / `sort_by()` / `_sort_strategies()` |
| 实盘标签页 | `app.pyw` 中 `_build_live_tab()` 布局 + `core/app_live.py` 中数据方法 |
| 实盘持仓/实时行情 | `core/app_live.py` 中的 `AppLiveMixin` 方法 |
| 研发面板 | `app.pyw` 中 `_build_backtest_tab()` dev_frame + `auto_develop()` |
| 策略扫描/统计读取 | `core/app_utils.py` — `scan_strategies()`, `read_stats()`, `_parse_label()` |
| 数据分析/因子计算 | `core/data_loader.py` — `calc_strat_positions()`, 日线/基本面加载 |
| DeepSeek 余额查询 | `core/app_balance.py` — `BalanceWindow` 类 |

⚠️ **`COLUMNS` 列定义**在 `core/app_config.py` 中（若已迁移）或仍位于 `app.pyw` 顶层。同时被排序和 populate_tree 依赖。改列名/列宽/新增列需要同步修改列定义 + Treeview columns + populate_tree insert values。若需实时行情的涨跌幅列（索引5），values 中必须给 `""` 占位。

### 主标签页（Main.TNotebook）样式醒目化

```python
for name in ("Main.TNotebook", "TNotebook"):
    s = ttk.Style()
    s.theme_use("clam")
    s.configure(name, background=BG_PRIMARY, borderwidth=0)
    s.configure(name + ".Tab", background=BG_TERTIARY,
                foreground=FG_SECONDARY if name == "Main.TNotebook" else FG_PRIMARY,
                padding=[20, 6], font=("Noto Sans SC Medium", 12))
    s.map(name + ".Tab", background=[("selected", BG_ELEVATED)],
          foreground=[("selected", FG_PRIMARY)])
```

变化：`padding` 增大、`font` 从 Light 10 改为 Medium 12、选中背景从 `BG_SECONDARY` 改为 `BG_ELEVATED`（更亮）。注意 `Main.TNotebook` 未选中时用 `FG_SECONDARY`（更淡），选中用 `FG_PRIMARY`（明亮）；子 notebook（`TNotebook`）始终用 `FG_PRIMARY`。

### 研发日志面板（dev_frame）模式

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
# 启动时默认可见，显示研发 prompt（2026-05-19 不再 grid_remove）
# 详见「研发日志面板 — 启动时显示默认 prompt」章节

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

- **同 `tab.rowconfigure` vs `self.rowconfigure`**：在 `_build_live_tab()` 里必须用 `tab.rowconfigure()` 配置标签页的行，**不是** `self.rowconfigure()`（那是主窗口的行）。
- **同位置不同容器**：做 grid 布局时注意容器实例，尤其是从 tab 切换到 self。

### 启动时显示默认研发 Prompt（2026-05-19）

2026-05-19 起，dev_frame **不再 `grid_remove()` 隐藏**，而是启动时即展开显示默认 prompt。

### 默认 Prompt 格式（2026-05-20 — 按条分行）

默认 prompt 改为 7 条按行编号，便于用户阅读和修改：

```python
default_prompt = (
    "调用 alpha-rapid-combinatorics skill，按以下要求生成策略：\\n"
    f"1. 项目路径: {_proj}\\n"
    "2. 数据: data/a_stock_kline_3y.npz（5203股×2426日K线）\\n"
    "3. 因子: 用 alpha_utils.py 预制因子做排列组合\\n"
    "4. 输出: 只写2个策略代码到 strategies/ 目录，不要运行回测\\n"
    "5. 股票池: POOL=CSI1000，元数据紧凑风格\\n"
    "6. 约束: 全矩阵向量化（零 for 循环），8分钟超时即交\\n"
    "7. 注意: 只输出创建的文件名，不做任何表现分析"
)
```

项目路径通过 `_proj = PROJECT_ROOT.replace(chr(92), chr(92)*2)` 动态生成，避免硬编码。`\\n` 换行符使文本框多行显示。

### 研发结果标签实时计时（2026-05-20）

`dev_result_label` 在研发过程中显示实时计时，不再使用 `dev_label`（其已固定为 "💡 Prompt"）：

```python
# auto_develop 启动时（设置初始状态）
self.dev_result_label.config(text="⏳ 正在研发中...")

# poll() 中计时器更新（每秒触发）
elapsed[0] += 1
self.dev_result_label.config(text=f"⏳ 正在研发中... 已等待 {elapsed[0]} 秒")

# Phase 1 思考完成
self.dev_result_label.config(text=f"💭 思考完成（{think_sec}s），正在回测...")

# 全部完成
self.dev_result_label.config(text="📋 研发结果  ✅ 完成")

# 研发出错
self.dev_result_label.config(text="❌ 研发出错")

# 无新策略
self.dev_result_label.config(text="📋 研发结果")

# 停止
self.dev_result_label.config(text="⛔ 已停止")
```

所有 `dev_label.config` 调用已被移除。状态显示位置：prompt 框的标签 → dev_result 框的标签。

**Pitfall：计时器每秒更新一次** — `elapsed[0]` 在 `poll()` 闭包中，必须在 `auto_develop` 中被定义为 `elapsed = [0]`（列表容器跨闭包共享），然后 `poll()` 中 `elapsed[0] += 1` 并更新 label。

### 研发日志面板 — dev_label 固定为「Prompt」（2026-05-20）

早期版本中 `self.dev_label` 随研发阶段变化（「⏳ 等待研发...」→「⏳ 正在启动 Hermes...」→「✅ 完成」等）。2026-05-20 起 dev_label **固定显示 `💡 Prompt`**，不再变化：

```python
self.dev_label = Label(self.dev_frame, text="💡 Prompt",
                       font=("Noto Sans SC Medium", 12),
                       fg=ACCENT_GOLD, bg=BG_PRIMARY, pady=3, anchor="w")
```

所有状态信息（「正在启动 Hermes...」「正在回测...」「✅ 全部完成」等）改为写入 `dev_result` 文本框。**删除所有 `self.dev_label.config(text=...)` 调用**：auto_develop、stop_dev、poll、poll_bt 中的 label 状态更新全部移除。状态信息改为 `self.dev_result.insert(END, "📌 状态文本\\n")`。

### 研发日志面板架构（2026-05-20 重构 — 双框分离）

2026-05-20 拆分 prompt 编辑和结果展示为两个独立框：

```
右栏布局 (2026-05-20 最终版):
row 0: dev_frame (prompt编辑框)     — height=4, font=Consolas 11, fill=X (不expand)
row 1: dev_result_frame (结果框)    — height=4, font=Consolas 11, fill=X (不expand)
row 2: notebook                     — 净值曲线 + 策略代码（weight=1独占剩余空间）
```

注意：detail_title（row 2）和 btm（底部指标+按钮，旧 row 3）均已完全移除。notebook 独占全部剩余空间直达面板底部。

**dev_text（prompt 编辑框）**：只负责存储和编辑 prompt。**从不被覆盖**。auto_develop 中读取 prompt 后不再 `delete`/`insert` 到 dev_text。

**dev_result（结果框）**：展示所有 Hermes 输出、回测日志、状态更新。

```python
# dev_text — prompt 专用（创建代码）
self.dev_text = Text(self.dev_frame, height=4, font=("Consolas", 11), ...)  # 2026-05-20: height 7→4, font 13→11
self.dev_text.pack(fill=X, padx=4, pady=(0, 4))  # 不再 expand=True
self.dev_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))
# 填充默认 prompt（chr(92) 避免反斜杠转义陷阱）
_proj = PROJECT_ROOT.replace(chr(92), chr(92) * 2)
default_prompt = (...)
self.dev_text.insert("1.0", f"📝 默认提示词:\\n{default_prompt}\\n{'─'*50}\\n\\n")
self.dev_text.config(state=NORMAL)  # 可编辑

# dev_result — 研发日志专用（创建代码）
self.dev_result_frame = Frame(right, bg=BG_PRIMARY, bd=1, relief="flat",
                               highlightbackground=ACCENT_TEAL, highlightthickness=1)
self.dev_result_label = Label(self.dev_result_frame, text="📋 研发结果",
                               font=("Noto Sans SC Medium", 12),
                               fg=ACCENT_TEAL, bg=BG_PRIMARY, pady=3, anchor="w")
self.dev_result_label.pack(fill=X, padx=6)
self.dev_result = Text(self.dev_result_frame, height=4, font=("Consolas", 11), ...)  # 2026-05-20: height 8→4, font 12→11
self.dev_result.pack(fill=X, padx=4, pady=(0, 4))  # 不再 expand=True
self.dev_result.insert("1.0", "等待启动研发...\\n")
self.dev_result_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(2, 0))
```

auto_develop 中从 dev_text 读 prompt，所有日志写入 dev_result：

```python
prompt = self.dev_text.get("1.0", "end-1c").strip()  # 从文本框读取
if not prompt:
    prompt = "调用 alpha-rapid-combinatorics skill..."

# 后续所有 self.dev_text.insert/see → self.dev_result.insert/see
```

### 数据状态栏移至左栏（2026-05-20）

数据状态栏（`self.data_status`）从右栏 detail 面板顶部移至左栏策略列表下方，pack 在 treeview + vsb 之后：

```python
vsb.pack(side=RIGHT, fill=Y)
# ── 数据状态栏（策略列表下方）──
self.data_status = Label(left, font=("Noto Sans SC Light", 9),
                         fg=ACCENT_BLUE, bg=BG_TERTIARY, pady=3, padx=10, anchor="w")
self.data_status.pack(fill=X, pady=(2, 0))
self.after(50, self._update_data_status)
```

右栏原来的 data_status grid 定义被删除。

### 自动研发（auto_develop）模式 — 隐藏终端 + PIPE 读取

**稳定方案：后台运行（`CREATE_NO_WINDOW`），PIPE 读取输出，在 dev_result 中显示。**

```python
def auto_develop(self):
    import subprocess, threading, queue, os
    # 从文本框读取提示词（用户可手工修改）
    prompt = self.dev_text.get("1.0", "end-1c").strip()
    if not prompt:
        prompt = "调用 alpha-rapid-combinatorics skill。从 data/a_stock_kline_3y.npz 读取数据..."
    ...
    env = os.environ.copy()
    # PYTHONIOENCODING 需保留以处理 GBK 编码；USERPROFILE 继承父进程，无需显式设置
    env["PYTHONIOENCODING"] = "utf-8"
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

#### `env` 继承父进程（不再显式设置 USERPROFILE）
**`env` 继承父进程**：子进程自动继承当前用户的环境变量（USERPROFILE 等），不需要显式设置。移除硬编码用户名后，项目移植到其他电脑也能正常工作。`PYTHONIOENCODING="utf-8"` 仍需保留以处理 GBK 编码问题。

#### 完成后自动刷新
```python
if not getattr(self, "_dev_stopped", False):
    self.after(500, self.refresh)  # 研发完成自动刷新回测列表
```

#### 路径硬编码排查清单

全项目从绝对路径（`os.path.expanduser("~/Desktop/a_stock_trade/...")`）迁移到相对路径后，排查清单：

| 检查项 | 模式 | 示例 |
|--------|------|------|
| `core/app_config.py` | `PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` | 其他模块引用 `from core.app_config import PROJECT_ROOT` |
| `core/` 下独立脚本 | `__file__` 两级上级 | `_SCRIPT_DIR = os.path.dirname(__file__); _PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)` |
| 项目根目录脚本 | `__file__` 一级上级 | `BASE = os.path.dirname(os.path.abspath(__file__))` |
| 子进程 env | 继承父进程（`os.environ.copy()`） | 移除 `env["USERPROFILE"]` |
| Prompt 文本 | 运行时动态生成 | `_proj = PROJECT_ROOT.replace(chr(92), chr(92)*2)` 避免反斜杠转义陷阱 |

**Python 反斜杠转义陷阱** — 在 f-string / patch 工具中处理 `replace(\"\\\\\", \"\\\\\\\\\")` 极易出错（每层解析吃一半反斜杠）。可靠做法：

```python
# ✓ 用 chr(92) 避免源码级转义
_proj = PROJECT_ROOT.replace(chr(92), chr(92) * 2)
# 等价于 .replace(\"\\\\\", \"\\\\\\\\\") 但不会被 patch/f-string 破坏
```

完整讨论见 `references/backslash-escaping-pitfalls.md`（含三层逃逸链拆解和每种场景的可靠写法）。

**回滚恢复方法**：如果 patch/re.sub 把文件改坏了，从 `bak/` 备份恢复后重新应用改动。备份在每次大改前手动 `cp app.pyw bak/`。

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

## 自定义深色滚动条 — DarkScrollbar

标准 tkinter `Scrollbar` 在深色主题下是灰色 Win95 风格，无法通过样式直接美化。实际项目中采用 **Canvas 自绘** 的 `DarkScrollbar` 类替代全部 6 处 Scrollbar。

### 类定义（在 `app.pyw` 中，STAT_KEYS 之后）

```python
class DarkScrollbar(Canvas):
    """自定义深色滚动条，适配暗色主题"""
    BAR = 10  # 滚动条宽/高

    def __init__(self, parent, orient="vertical", command=None, **kw):
        self._orient = orient
        self._cmd = command
        self._first = 0.0
        self._last = 1.0
        self._drag_start = 0
        self._drag_offset = 0.0
        self._hover = False
        self._drag = False
        kw.pop("bd", None); kw.pop("highlightthickness", None)
        kw.pop("relief", None); kw.pop("width", None); kw.pop("height", None)
        Canvas.__init__(self, parent, bd=0, highlightthickness=0,
                        relief="flat", **kw)
        if orient == "vertical":
            self.configure(width=self.BAR, cursor="hand2")
        else:
            self.configure(height=self.BAR, cursor="hand2")
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self):
        self.delete("all")
        w = self.winfo_width(); h = self.winfo_height()
        if w < 2 or h < 2: return
        if self._drag:       clr = ACCENT_BLUE_SOFT
        elif self._hover:    clr = BORDER_LIGHT
        else:                clr = BG_ELEVATED
        pad = 1
        if self._orient == "vertical":
            sh = max(20, h * (self._last - self._first))
            sy = h * self._first
            self.create_rectangle(pad, sy, w - pad, min(sy + sh, h),
                                  fill=clr, outline="", width=0)
        else:
            sw = max(20, w * (self._last - self._first))
            sx = w * self._first
            self.create_rectangle(sx, pad, min(sx + sw, w), h - pad,
                                  fill=clr, outline="", width=0)

    def set(self, first, last):
        self._first = float(first)
        self._last = float(last)
        self._draw()

    def _on_press(self, event):
        self._drag = True
        if self._orient == "vertical":
            h = max(self.winfo_height(), 1)
            self._drag_offset = event.y / h - self._first
        else:
            w = max(self.winfo_width(), 1)
            self._drag_offset = event.x / w - self._first
        self._draw()

    def _on_drag(self, event):
        if not self._cmd: return
        if self._orient == "vertical":
            h = max(self.winfo_height(), 1)
            fraction = event.y / h - self._drag_offset
        else:
            w = max(self.winfo_width(), 1)
            fraction = event.x / w - self._drag_offset
        fraction = max(0.0, min(1.0, fraction))
        self._cmd("moveto", fraction)

    def _on_release(self, event): self._drag = False; self._draw()
    def _on_enter(self, event):  self._hover = True;  self._draw()
    def _on_leave(self, event):  self._hover = False; self._draw()
```

### 替换方式

原代码 `vsb = Scrollbar(left, orient="vertical", command=...)` 改为 `vsb = DarkScrollbar(left, orient="vertical", command=...)`，其余 `configure` / `pack` / `grid` 调用不变。`DarkScrollbar` 也实现了 `set(first, last)` 接口，Treeview/Text 的 `yscrollcommand` 绑定不需要修改。

### 颜色状态

| 状态 | 滑块颜色 | 触发行 |
|------|---------|--------|
| 常态 | `BG_ELEVATED` (#3c444d) | — |
| 悬停 | `BORDER_LIGHT` (#3c444d 微亮) | `<Enter>` |
| 拖拽 | `ACCENT_BLUE_SOFT` (#1f6feb) | `<Button-1>` + `<B1-Motion>` |

轨道（trough）直接是 Canvas 背景色（不额外绘制），通过 Canvas 的 `bg` 参数设置。

### Pitfall: 滑条手感（moveto 模式）

- 拖拽时必须用 `moveto` 模式（跳到精确位置），不能用 `scroll ... units`（按行滚）。`scroll units` 模式下每次鼠标移动只滚几行，拖动量跟滚动量不匹配，感觉像「卡住」。
- 正确实现：`_on_press` 记录 `_drag_offset = 点击比例 - 当前位置比例`，`_on_drag` 计算 `新比例 = 鼠标位置比例 - _drag_offset`，调用 `self._cmd("moveto", 新比例)`。
- `moveto` 参数范围 `[0.0, 1.0]`，需要 `max(0.0, min(1.0, fraction))` 截断防止越界。
- 滑块最小高度 20px，避免 1000+ 行数据时滑块缩成一条线点不到
- `<Configure>` 事件绑定到 `lambda e: self._draw()` 确保窗口缩放时重绘

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

### 3. 添加表头排序（带实时数据保留）

两阶段：① 存储原始数据到 `self._pos_data`；② 排序时重新排 `_pos_data` 并刷新树。

**初始化**（App.__init__ 或类属性）：
```python
self._pos_sort_col = "amount"   # 默认排序列
self._pos_sort_rev = True       # 默认方向（降序）
self._pos_data = []             # 缓存原始数据
```

**数据存储 + 表头箭头重置**（在数据刷新方法末尾保存并重置排序状态）：
```python
adjusted.sort(key=lambda x: x[3], reverse=True)  # 默认按金额降序
self._pos_data = adjusted
self._pos_sort_col = "amount"
self._pos_sort_rev = True
# 重置表头箭头
for cid, ct, cw in POS_COLS:
    arrow = " ▼" if cid == "amount" else ""
    self.pos_tree.heading(cid, text=ct + arrow)
self._populate_pos_tree()
```

**排序 + 渲染方法**（实时数据快照保留）：
```python
def _populate_pos_tree(self):
    # ★ 快照当前实时涨跌幅（排序时不丢失 already-fetched data）
    change_map = {}
    for item in self.pos_tree.get_children():
        vals = self.pos_tree.item(item, "values")
        if len(vals) >= 6 and vals[5]:
            change_map[vals[0].strip().zfill(6)] = vals[5]

    for row in self.pos_tree.get_children():
        self.pos_tree.delete(row)

    # 按当前排序列排序
    col = self._pos_sort_col
    rev = self._pos_sort_rev
    if col == "code":       adjusted_sorted = sorted(self._pos_data, key=lambda x: x[0], reverse=rev)
    elif col == "pname":    adjusted_sorted = sorted(self._pos_data, key=lambda x: x[1], reverse=rev)
    elif col == "lots":     adjusted_sorted = sorted(self._pos_data, key=lambda x: x[2], reverse=rev)
    elif col == "price":    adjusted_sorted = sorted(self._pos_data, key=lambda x: x[5], reverse=rev)
    elif col == "amount":   adjusted_sorted = sorted(self._pos_data, key=lambda x: x[3], reverse=rev)
    elif col == "strategies": adjusted_sorted = sorted(self._pos_data, key=lambda x: len(x[4]), reverse=rev)
    else:                   adjusted_sorted = self._pos_data

    for code, name, lots, amount, strats, pps in adjusted_sorted:
        # ★ 回填快照的涨跌幅
        change_val = change_map.get(code.strip().zfill(6), "")
        self.pos_tree.insert("", "end", values=(code, name, str(lots), ...,
                                                change_val, strats_str))
    # ... 合计条渲染 ...

def sort_positions(self, col_id):
    if col_id == self._pos_sort_col:
        self._pos_sort_rev = not self._pos_sort_rev
    else:
        self._pos_sort_col = col_id
        self._pos_sort_rev = (col_id != "code" and col_id != "pname")
    # 更新表头箭头
    for cid, ct, cw in POS_COLS:
        arrow = ""
        if cid == col_id:
            arrow = " ▲" if not self._pos_sort_rev else " ▼"
        self.pos_tree.heading(cid, text=ct + arrow)
    self._populate_pos_tree()
```

**绑定表头点击**（在 Treeview 创建循环中）：
```python
for cid, ct, cw in POS_COLS:
    self.pos_tree.heading(cid, text=ct, command=lambda c=cid: self.sort_positions(c))
```

**关键设计决策**：
- **不重新聚合计算** — 排序只操作缓存的 `_pos_data`，不重新读取 NPZ 或重新等比缩仓
- **快照保留实时数据** — 排序前扫描现有树项的涨跌幅列，按代码快照，重建后回填
- **涨跌幅颜色重新来过** — 颜色标签（up/down）不需要保留，3 秒后的实时循环会重新设置
- **数据刷新时重置排序** — `refresh_combined_positions()` 每次重算后重置为按金额降序，确保初始状态一致

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

### 研发日志面板 — R&D 日志写入 dev_result (2026-05-20 起)

点击「🤖 自动研发」后，dev_result 显示发送的 prompt 和 Hermes 输出（不再覆盖 dev_text 文本框）：

```python
# dev_result 写入日志（dev_text 只存 prompt，不受影响）
self.dev_result.delete("1.0", END)
self.dev_result.insert("1.0", f"📝 发送的提示词:\n{prompt}\n{'─'*50}\n\n")
```

这让用户能看到 Hermes 收到了什么上下文，同时 prompt 编辑框保持不动。

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
研发区域(`dev_result`)使用等宽字体，字号应偏大以便阅读日志输出：
```python
self.dev_result = Text(..., font=("Consolas", 13), ...)
```
dev_text (prompt编辑框) 同样用 Consolas 13。之前用 `Consolas 9` 太小，改到 `13` 后阅读性显著提升。

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

注意：`RESULTS` 已在 `core/app_config.py` 中定义为 `os.path.join(PROJECT_ROOT, "results")`（基于 `__file__` 自动检测），不依赖 `expanduser`。`datetime` 导入放函数顶部避免重复导入。

## ▶ 运行全部实盘 — 串行模式（importlib 线程不安全）

`_run_all_live_strategies()` 从 `subprocess.Popen` 改为 **`ThreadPoolExecutor` + `importlib`** 在同进程内执行：

```python
def _run_all_live_strategies(self):
    from concurrent.futures import ThreadPoolExecutor
    import importlib.util, io, contextlib

    max_workers = 1  # importlib 非线程安全，必须串行
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
- `max_workers = 1` — **importlib 非线程安全**。`spec_from_file_location()` 和 `exec_module()` 有竞争条件，多策略同时加载同模块（`numpy`/`matplotlib`/`backtest_utils`）会导致死锁或段错误。即使 numpy 可释放 GIL，importlib 本身有内部全局锁冲突。不要设 `cpu_count // 2`。
- 按钮状态管理在 `wait_all()` 的 `finally` 块内，不在外层 `run_all_live()` 里 —— 否则按钮会在策略提交完但未跑完时提前恢复
- `pool.shutdown(wait=False)` + `f.result()` 手动管理生命周期，不阻塞UI
- `io.StringIO()` 吞噬 stdout
- 单策略异常不影响其他
- `_run_one` 的 finally 块必须包含 `plt.close('all')` 防止 figure 泄漏

**变化原因**：旧版开多个python子进程分别加载NPZ，重复IO浪费。新方式同进程运行，NPZ缓存OS共享，启动快约5倍。但 importlib 线程不安全迫使串行。

### Pitfall: ThreadPoolExecutor importlib 崩溃

`importlib.util.spec_from_file_location` 和 `spec.loader.exec_module` 在多线程下不安全。策略代码间共享全局模块（numpy/pandas/matplotlib/backtest_utils），同时 exec_module 会触发多次模块初始化 → 段错误或死锁。

**症状**：点击「运行全部实盘」后程序无响应或闪退，没有异常输出（因为 stdout 被 StringIO 吞噬）。

**修复**：设 `max_workers = 1`。如果未来需要并行，改用 `ProcessPoolExecutor`（每个进程独立 import 环境）而非 ThreadPoolExecutor。

### Pitfall: read_file + write_file 整文件污染

**永远不要**把 `read_file()` 的返回内容直接传给 `write_file()` 写回同一文件。

`read_file()` 逐行输出时包含 `行号|` 前缀（如 `   383|        font=(...)`），直接 `write_file()` 会把这些前缀写入文件 → 每行开头多出 `   383|`，Python 编译报 `IndentationError: unexpected indent` 且 line 1 就有问题。

```python
# ❌ 灾难
content = read_file(path="app.pyw", ...)  # 内容含 "\u2003 383|" 前缀
text = content["content"]
write_file(path="app.pyw", content=text)  # 前缀写入 → 文件损坏

# ✓ 正确
patch(new_string="...", old_string="...", path="app.pyw", replace_all=True)
```

**修复方法**：`git checkout <上一个完好commit的hash> -- app.pyw` 从之前版本恢复。不要直接 `git checkout HEAD --` 因为 HEAD 已被污染。

**在 execute_code 中做这种操作尤其危险** — 没有预览确认就先写入，等发现时文件已被提交。安全做法：用 `terminal` 的 `head -5` 预览确认格式后再操作。

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
### 4. 在组合持仓表新增列（3处同步修改 + 底部合计条）

新增列的完整步骤：

**① POS_COLS 定义（常量块）**
```python
POS_COLS = [("code","股票代码",120), ("pname","股票名称",105),
            ("lots","总手数",75),  ("price","参考价",85),
            ("amount","总市值",100),
            ("change_pct","涨跌幅",85),      # ← 新增列
            ("strategies","涉及策略",100)]
```

**② Treeview columns**
```python
self.pos_tree = ttk.Treeview(pos_sec,
    columns=("code","pname","lots","price","amount",
             "change_pct",                # ← columns 顺序必须一致
             "strategies"),
    show="headings", height=5)
```

**③ insert 时的 values 元组（必须7个值，涨跌幅给空占位）**
```python
self.pos_tree.insert("", END,
    values=(code, name, str(lots), f"{pps:.2f}",
            f"{amount:.0f}", "", strats_str))
```
涨跌幅列初始为空字符串 `""`，后续由后台线程回填实时数据。

**④ 底部合计条索引偏移**
`make_aligned_bar` 会根据 POS_COLS 长度自动创建对应数量的 Label。新增列后索引全部右移：
```python
self.pos_bar_lbls[5].config(text="")              # 原涨跌幅位置（新增）
self.pos_bar_lbls[6].config(text=f"分配 ¥{total_alloc:,.0f}")  # 原索引5→6
```

**常见失误**：漏掉 ①~④ 任何一步。最隐蔽的错误是第③步 — values 个数<columns 数时，最后一个值会填入倒数第二列，导致涉及策略列空白、涨跌幅列占位错误。修复方法：给新列一个空字符串占位 `""`。

### 5. 实时行情后台线程模式（新浪免费接口 + 3秒循环）

获取 A 股实时涨跌幅的稳定模式：常驻后台线程每3秒轮询新浪 API，`self.after(0, _update)` 回到主线程更新 UI。

```python
def refresh_combined_positions(self):
    # ... 渲染基础数据 ...
    # 更新持仓代码列表供后台线程使用
    self._realtime_codes = [code for code, _, _, _, _, _ in adjusted]
    # 首次渲染时启动常驻循环线程（只启动一次）
    if not hasattr(self, "_realtime_thread_started"):
        self._realtime_thread_started = True
        threading.Thread(target=self._realtime_loop, daemon=True).start()

def _realtime_loop(self):
    """后台循环：每3秒拉取一次实时涨跌幅"""
    import time
    while True:
        codes = getattr(self, "_realtime_codes", None)
        if codes:
            self._fetch_realtime_changes(codes)
        time.sleep(3)

def _fetch_realtime_changes(self, codes):
    """后台线程：新浪实时行情 → after(0) 更新 UI"""
    if not codes: return
    try:
        import urllib.request
        prefixes = {"000":"sz","001":"sz","002":"sz","003":"sz",
                    "300":"sz","301":"sz","302":"sz","303":"sz",
                    "600":"sh","601":"sh","603":"sh","605":"sh","688":"sh"}
        sina_codes = ",".join(f"{prefixes.get(c[:3],'sh')}{c}" for c in codes)
        url = f"http://hq.sinajs.cn/list={sina_codes}"
        req = urllib.request.Request(url,
            headers={"Referer": "https://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("gbk")

        change_map = {}
        for line in raw.strip().split("\n"):
            if not line.startswith("var hq_str_"): continue
            code = line.split("=")[0].split("_")[-1]
            fields = line.split("\"")[1].split(",")
            if len(fields) >= 32:
                yclose = float(fields[2]) if fields[2] else 0
                now = float(fields[3]) if fields[3] else 0
                if yclose > 0:
                    pct = (now - yclose) / yclose * 100
                    raw_code = code[2:] if len(code) > 2 else code
                    change_map[raw_code] = f"{pct:+.2f}%"

        def _update():
            for item in self.pos_tree.get_children():
                vals = list(self.pos_tree.item(item, "values"))
                c = vals[0].strip().zfill(6)
                pct_str = change_map.get(c, "")
                vals[5] = pct_str if pct_str else "—"
                tags = ()
                if pct_str:
                    tags = ("up",) if pct_str.startswith("+") else ("down",)
                self.pos_tree.item(item, values=tuple(vals), tags=tags)
            self.pos_tree.tag_configure("up", foreground="#f85149")   # 红涨
            self.pos_tree.tag_configure("down", foreground="#56d364") # 绿跌

        self.after(0, _update)
    except Exception:
        pass  # 网络失败不阻塞
```

**要点**：
- 新浪 API 以 GBK 编码返回，需 `.decode("gbk")`
- 需要 `Referer: https://finance.sina.com.cn` 请求头，否则可能被拦截
- `sz`=深交所，`sh`=上交所
- 涨跌额通过昨收价`fields[2]`和现价`fields[3]`计算
- `_realtime_loop` 只启动一次（`_realtime_thread_started` 标志），每次 render 更新 `_realtime_codes` 即可
- 颜色 tag_configure 红涨(#f85149) / 绿跌(#56d364) — A股习惯改为了红涨绿跌
- 网络异常静默忽略，已有基础数据显示不受影响
- daemon=True 线程随窗口关闭自动结束

### 6. 导出持仓 CSV — 默认文件名加日期

`export_positions_csv()` 使用 `filedialog.asksaveasfilename` 的 `initialfile` 参数：

```python
initialfile=f"组合持仓_{datetime.now():%Y%m%d}.csv"
```

日期格式 `%Y%m%d`（如 `组合持仓_20260518.csv`），避免手动重命名。

### 7. 加权涨跌列（组合持仓最后一列 + 底部合计条）

在组合持仓表最后一列新增「加权涨跌」，每行显示该股对总组合的涨跌贡献（`该股市值/总市值 × 涨跌幅`），底部合计条显示总加权涨跌幅（带「合计」前缀）。该列**不参与排序**。

**新增列完整步骤（6处同步修改）**：

**① app.pyw — POS_COLS + Treeview columns（加权涨跌不绑排序命令）**
```python
POS_COLS = [..., ("strategies","涉及策略",100), ("weighted","加权涨跌",85)]
self.pos_tree = ttk.Treeview(pos_sec,
    columns=(..., "strategies", "weighted"), ...)
for cid, ct, cw in POS_COLS:
    cmd = None if cid == "weighted" else (lambda c=cid: self.sort_positions(c))
    self.pos_tree.heading(cid, text=ct, command=cmd)
    self.pos_tree.column(cid, width=cw, minwidth=cw, ...)
```

**② refresh_combined_positions — heading 循环同步加新列**
```python
for cid, ct, cw in [(...), ("strategies","涉及策略",100), ("weighted","加权涨跌",85)]:
```

**③ sort_positions — 列列表同步加 weighted**
```python
for cid, ct, cw in [(...), ("strategies","涉及策略",100), ("weighted","加权涨跌",85)]:
```

**④ _populate_pos_tree — 先算总市值 → 每行计算加权贡献 → 底部合计条**
```python
# 先算总市值（用于加权涨跌）
total_lots = sum(x[2] for x in adjusted_sorted)
total_amt = sum(x[3] for x in adjusted_sorted)
wret_total = 0.0
rows = []
for code, name, lots, amount, strats, pps in adjusted_sorted:
    change_val = change_map.get(code.strip().zfill(6), "")
    wval_str = ""
    if change_val and change_val != "—":
        try:
            pct = float(change_val.replace("%", "").replace("+", ""))
            w = (amount / total_amt) * pct if total_amt > 0 else 0
            wret_total += w
            sign_w = "+" if w >= 0 else ""
            wval_str = f"{sign_w}{w:.2f}%"
        except ValueError:
            pass
    rows.append((..., change_val, strats_str, wval_str))  # 8值元组
for r in rows:
    self.pos_tree.insert("", "end", values=r)
# 底部合计条索引偏移：涨跌幅[5]空 → 涉及策略[6]分配 → 加权涨跌[7]合计
self.pos_bar_lbls[5].config(text="")
self.pos_bar_lbls[6].config(text=f"分配 ¥{total_alloc:,.0f}")
self.pos_bar_lbls[7].config(text=f"合计 {sign}{wret_total:.2f}%", fg=wcolor)
```

**⑤ _fetch_realtime_changes._update — 两遍扫描计算每行加权贡献**
```python
def _update():
    # 第一遍：收集涨跌幅和总市值
    items_data = []
    total_amt = 0.0
    for item in self.pos_tree.get_children():
        vals = list(self.pos_tree.item(item, "values"))
        # ... 更新 vals[5] = pct_str ...
        amt = float(vals[4].replace(",", ""))  # 反解析千分位
        total_amt += amt
        pct_val = float(pct_str...) if pct_str and pct_str != "—" else 0.0
        items_data.append((item, vals, tags, amt, pct_val))
    # 第二遍：计算每行加权贡献并写入 vals[7]
    wret = 0.0
    for item, vals, tags, amt, pct_val in items_data:
        wval_str = ""
        if pct_val != 0 and total_amt > 0:
            w = (amt / total_amt) * pct_val
            wret += w
            wval_str = f"{'+' if w >= 0 else ''}{w:.2f}%"
        while len(vals) < 8:
            vals.append("")
        vals[7] = wval_str
        self.pos_tree.item(item, values=tuple(vals), tags=tags)
    self.pos_bar_lbls[7].config(text=f"合计 {sign}{wret:.2f}%", fg=wcolor)
```

**⑥ export_positions_csv — header 补全**
```python
w.writerow(["股票代码", "股票名称", "总手数", "参考价", "总市值", "涨跌幅", "涉及策略", "加权涨跌"])
```

**关键设计要点**：
- 加权涨跌列 heading 不绑排序命令（`command=None`），排序时该列被跳过
- `_populate_pos_tree` 中必须先算 `total_amt`，再逐行计算 `(amount / total_amt) * pct`
- 实时更新必须**两遍扫描**：第一遍收集所有行的 `amt` 和 `pct_val` 算出 `total_amt`，第二遍才能正确计算每行权重并写入 `vals[7]`
- `pos_bar_lbls` 索引随 POS_COLS 新增列右移
- 涨红 `#f85149` / 跌绿 `#56d364`

### 5. 实盘策略表「最新信号」列

`STRAT_COLS` 中 `("signal","最新信号",95)` 原本显示 `s.get("signal","")`（来自 JSON 的原始信号）。2026-05-19 改为从 `position_matrix.npz` 读取策略最后有持仓的日期：

```python
from app import get_last_pos_date  # 或内联在文件顶部定义

def get_last_pos_date(folder):
    npz_path = os.path.join(RESULTS, folder, "position_matrix.npz")
    if not os.path.exists(npz_path):
        return ""
    d = np.load(npz_path, allow_pickle=True)
    pos = d.get("pos_value")
    dates = d.get("dates")
    if pos is None or dates is None:
        return ""
    for t in range(pos.shape[1] - 1, -1, -1):
        if (pos[:, t] > 0).any():
            return pd.Timestamp(dates[t]).strftime("%m-%d")
    return ""
```

在 `refresh_live()` 中：
```python
vals = (..., get_last_pos_date(s.get("folder","")), ...)
```

从最后一天往前找第一个有非零持仓的交易日，显示 `MM-DD` 格式。无持仓或 NPZ 不存在时返回空字符串。异常安全（全 try-except 兜底）。

### 6. 导出持仓 CSV — 默认文件名加日期

`export_positions_csv()` 使用 `filedialog.asksaveasfilename` 的 `initialfile` 参数：
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

**背景**: 用户资金量小，纯等比缩放会把所有股票缩到门槛以下然后全部过滤掉。

### 算法：逐步缩仓（从大到小逐只加入）

```
1. 按原始市值从大到小排序所有股票
2. k=1 开始：取前k只最大股票
3. 计算 scale = 总分配金额 / 前k只总金额
4. 检查前k只每只取整手数后的实际金额是否 ≥ 2万（阈值可调）
   → 全部满足：保存这组结果，k+=1，继续尝试
   → 有低于阈值的：停止，用上一组(k-1)的结果
   → 有低于阈值的：停止，用上一组(k-1)的结果
5. 最终选中的股票集等比缩放对齐总分配金额

关键：阈值检查用 `actual_amt`（取整后实际金额），不是 `scaled_amt`（理论金额）。`int()` 向下截断后实际金额可能远低于阈值。

**阈值变量**：`refresh_combined_positions()` 中 `if actual_amt < 20000:` — 该值已从 10000 调至 20000。修改时同步更新函数 docstring 中的注释。

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

## 性能优化模式（Tkinter 桌面应用专有）

### 检测：哪些操作引起 UI 卡顿？

卡顿 = 主线程（tkinter event loop）长时间被占用。常见原因：

| 原因 | 典型耗时 | 检测方法 |
|------|---------|---------|
| 全量 NPZ 加载（~112MB close 矩阵） | 0.5~1.5s | `_update_data_status` 中 `np.load` |
| 语法高亮每击键一次跑 6 个 regex | 10~50ms/次 | `code_text.bind("<KeyRelease>", ...)` |
| 窗口拖动时 LANCZOS 重采样 | 50~200ms/帧 | `img_canvas.bind("<Configure>", ...)` |
| 实时行情 3 秒循环 UI 更新堆积 | 队列累积 | `_realtime_loop` 每 3s 触发 |
| `self.update()` 强制同步 | 100~500ms | `run_all_live` 中的 `self.update()` |

### 模式1：NPZ 轻量读取（mmap_mode='r'）

**问题**：`np.load(npz_path)` 加载完整 ~112MB close 矩阵只为了读 dates/codes 元数据。

**修复**：使用 `mmap_mode='r'` 只读需要的数组，不把整个文件加载到内存：

```python
# ❌ 之前（加载整个 112MB 文件）
d = np.load(npz_path, allow_pickle=True)
dates = d["dates"]  # OK
codes = d["codes"]  # OK
# d["close"] 被惰性加载，但 NpzFile 对象持有文件句柄

# ✓ 之后（mmap 映射，只读需要的键）
d = np.load(npz_path, allow_pickle=True, mmap_mode='r')
dates = d["dates"]
codes = d["codes"]
n_stocks, n_days = len(codes), len(dates)
d.close()  # 显式关闭，释放文件句柄
```

**注意**：
- `mmap_mode='r'` 对已压缩的 NPZ 不生效（回退到正常加载），但代码风格一致无副作用
- 读完后显式 `d.close()` 释放文件锁
- 只访问需要的小数组（dates/codes 几十 KB），不访问 close/volume 大矩阵
- 这个模式也适用基本面 NPZ（只读 codes/dates/fields，不读 data）

**适用场景**：状态栏显示、元数据读取、股票列表获取等只需要文件结构信息的操作。

### 模式2：debounce 防抖（200~300ms 延迟）

**问题**：每个用户动作（按键、窗口拖动）立即触发昂贵的计算操作。

**修复**：用一个 `after_cancel / after` 链实现防抖，只在用户停止操作后才执行：

```python
# 按键防抖（语法高亮）
def _debounce_highlight(self):
    if hasattr(self, '_hl_timer') and self._hl_timer:
        self.after_cancel(self._hl_timer)
    self._hl_timer = self.after(300, self._highlight_code)

# 绑定 KeyRelease
self.code_text.bind("<KeyRelease>", lambda e: self._debounce_highlight())

# canvas resize 防抖（图表缩放）
def _on_canvas_resize(self, event=None):
    if self._raw_pil_img:
        if hasattr(self, '_resize_timer') and self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(150, self._render_chart)
```

**公式**：`cancel + after(200~300ms, func)` — 时间窗口通常 150ms（resize）~300ms（键盘）。

### 模式3：防重复计算（尺寸/状态无变化时跳过）

**问题**：`<Configure>` 事件在拖动窗口时连续触发，每次触发先 delete 再 recreate canvas。

**修复**：缓存上次渲染尺寸，相同尺寸直接返回：

```python
def _render_chart(self):
    cw = self.img_canvas.winfo_width() - 16
    ch = self.img_canvas.winfo_height() - 16
    if cw < 100 or ch < 100:
        return
    # 如果尺寸没变，跳过重绘
    if (hasattr(self, '_last_cw') and hasattr(self, '_last_ch')
            and self._last_cw == cw and self._last_ch == ch):
        return
    self._last_cw, self._last_ch = cw, ch
    # ... 实际渲染 ...
```

### 模式4：实时循环进度防护（_updating 标志）

**问题**：后台线程每 N 秒触发 UI 更新，如果网络慢或 UI 卡顿，多个 `after(0, update)` 堆积。

**修复**：加入 `_updating` 标志，上次更新未完成则跳过本轮：

```python
def _realtime_loop(self):
    while True:
        if codes and not getattr(self, "_rt_updating", False):
            self._rt_updating = True
            self._fetch_realtime_changes(codes)
        time.sleep(3)

def _fetch_realtime_changes(self, codes):
    # ... 请求和解析 ...
    def _update():
        # ... 更新 UI ...
        self._rt_updating = False
    self.after(0, _update)
```

### 模式5：语法高亮 — 合并 regex + 批量 tag_add

**问题**：6 次独立的 `re.finditer` + 6 轮 `tag_add` 调用，每次 `tag_add` 生成 `f"1.0+{start}c"` 字符串。

**修复**：先收集所有片段 `[(start, end, tag), ...]` 统一排序后再批量 tag_add：

```python
def _highlight_code(self):
    content = self.code_text.get("1.0", END)
    if not content.strip():
        return
    for tag in ("kw", "str", "cmt", "num", "dec", "bif"):
        self.code_text.tag_remove(tag, "1.0", END)
    segments = []
    # 多个 re.finditer 收集到 segments
    for m in re.finditer(r'#[^\n]*', content):
        segments.append((m.start(), m.end(), "cmt"))
    for m in re.finditer(r'"""...', content, re.DOTALL):
        segments.append((m.start(), m.end(), "str"))
    # ... 更多 regex ...
    # 按起始位置排序，批量应用标签
    segments.sort(key=lambda x: x[0])
    for start, end, tag in segments:
        try:
            self.code_text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
        except Exception:
            pass
```

### Pitfall: file-matching 排除范围过宽

**症状**：用 `f.startswith('a52')` 排除 a521/a522/a523 时不小心把 `a520` 也排除了。

**根因**：前缀匹配不考虑长度，`'a52'` 匹配 `a520`（前三位是 a52）。

```python
# ❌ 排除 a521-a523 时误伤 a520
files = [f for f in all_files if not f.startswith('a52')]

# ✓ 正确：用更精确的 pattern
files = [f for f in all_files if not f.startswith('a52') or f[3].isalpha()]
# 或显式列出排除项
exclude = {'a521', 'a522', 'a523'}
files = [f for f in all_files if f[:4] not in exclude]
```

**教训**：任何用前缀/后缀做文件筛选的代码，验证时至少检查边界值（如 `a520_xxx.py` 和 `a521_xxx.py` 是否被正确归类）。

### 关联参考文件

| 文件 | 内容 |
|------|------|
| `references/realtime-stock-quotes.md` | 新浪免费实时行情 API 接入模式 |

## ⚠️ 关键原则：非必要不修改核心功能

本会话中反复出现的教训——**不要随意改动以下关键部分，除非得到用户明确指示**：

1. **布局几何管理器** — `pack()` / `grid()` / `place()` 不能互相替代或混用。重构时保留原始管理器类型，只微调参数。
2. **按钮命令回调** — `command=self.xxx` 的绑定关系、按钮的 `state` 初始状态、按钮集群的排列顺序，都不应在非相关的重构中改变。
3. **事件处理器** — `<<TreeviewSelect>>`、`<Button-3>` 等事件的绑定方法名和签名，即使重构到新方法中也必须保持原有行为。
4. **子进程调用方式** — `subprocess.Popen` 的参数（shell/creationflags/env/args 格式）与特定运行环境强绑定，改变可能导致功能完全失效。
5. **数据读写路径** — `LIVE_DIR`、`RESULTS`、`STRATEGIES_DIR`、`DATA_DIR` 的解析方式（`__file__` 相对路径 vs `expanduser` 绝对路径）不能随意改变。

**黄金法则**：如果重构目标是减少重复代码/拆分模块，只改导入路径和函数签名，不改调用逻辑、布局顺序、事件绑定。

**更严格的黄金法则**：如果用户说「只让你改位置/颜色/字体」，则**只做那一件事**。不要顺手优化附近代码、不要重构未提及的方法、不要删除看起来「没用」的按钮/方法/引用——你可能不知道它们在什么时候被调用。

**实战反例（2026-05-20 删除底部指标栏）**：用户要求去掉 stats 文本框让图表直达底部。我应该只：
```
□ 删除 btm Frame 创建代码
□ 删除 stats_text 创建 + tag_configure + pack
□ 删除 open_btn 创建 + pack
□ 删除 stats_text 所有引用（clear_detail + show_detail 中的 delete/insert）
□ 删除 open_btn 所有引用（clear_detail + show_detail 中的 config）
□ 删除 open_chart 方法
□ 调整 notebook row 3→2
□ 调整 rowconfigure 3→2
```

但我**多做了**：除了上述清单，还额外删了 `open_chart` 方法签名中 `self.current_equity` 的引用、动了 `show_detail` 中的未提及代码、删了按钮状态管理。这些多余改动导致图片不显示——用户质问「只让你改位置，你把功能都改坏了」。

**教训**：修改 UI 布局时，列出精确的工作清单并逐项检查。清单外的内容不碰。如果发现「顺手就能优化」的代码，记下来，下次单独提 PR。

## 启动优化 — 延迟加载 + 后台 IO 线程

窗口启动时必须**优先显示**，IO 密集型操作全部延迟到窗口可见后再执行。

### after() 链式启动

```python
# _build_ui() 最后：先显示窗口空壳，再逐步填充数据

self.after(50, self._update_data_status)    # 50ms：加载 NPZ 元数据（已优化，只读 codes/dates）
self.after(200, self.refresh_live)           # 200ms：读取 JSON + 加载持仓 NPZ（后台线程内）
```

### 后台线程 _refresh_positions_from_npz + after(0) 回主线程

`refresh_live()` 末尾调用 `_refresh_positions_from_npz()` 逐策略读 `position_matrix.npz`，这是 IO 密集型操作，**必须在后台线程执行**：

```python
def refresh_live(self):
    # ... 策略列表渲染（JSON读取，毫秒级）...
    self.after(0, lambda: self.strat_tree.tag_configure("total", ...))

    # 后台加载持仓 → 完成后回主线程刷新组合持仓
    import threading
    def _bg_load():
        try:
            self._refresh_positions_from_npz()  # 逐个读取 NPZ，IO 密集
        finally:
            self.after(0, self.refresh_combined_positions)  # 主线程刷新 UI
    threading.Thread(target=_bg_load, daemon=True).start()
```

### TK 模式总结

| 操作类型 | 执行方式 | 示例 |
|----------|---------|------|
| 读 NPZ 全量矩阵 ~100MB | **禁止** — 启动时绝不加载 | 已改为只读 codes/dates |
| 读 NPZ 元数据 codes/dates | self.after(50) 延迟 | _update_data_status |
| 读 JSON + 文件 mtime | 主线程直接执行 毫秒级 | load_live_strategies |
| 读 position_matrix.npz IO | threading.Thread + after(0) | _refresh_positions_from_npz |
| 等比缩仓计算 | after(0, callback) 在主线程 | refresh_combined_positions |
| 新浪实时行情轮询 | daemon 后台线程 3秒循环 | _realtime_loop |

### NPZ 元数据读取优化

`_update_data_status()` 在启动时显示数据概览，但**绝对不能**加载 `close` / `data` 全量矩阵：

```python
# 错误：加载 ~100MB 矩阵
d = np.load(npz, allow_pickle=True)
close = d["close"]                          # 5241x2427 float64 ~ 95MB
n_stocks, n_days = close.shape
valid_last = (close[:, -1] > 0.5).sum()

# 正确：只读 codes/dates 元数据
d = np.load(npz, allow_pickle=True)
dates = d["dates"]
codes = d["codes"]
n_stocks, n_days = len(codes), len(dates)   # 从 codes/dates 推断 shape
last_date = pd.Timestamp(dates[-1]).date()
mtime = datetime.fromtimestamp(os.path.getmtime(npz)).strftime("%m-%d %H:%M")
# 不再需要 close 和 valid_last
```

同理，基本面 NPZ 也只读 `codes`/`dates`/`fields`，不读 `data`。

**注意：np.load(npz) 本身是惰性的** — 创建 NpzFile 对象，数组在访问时解压加载。所以 d["codes"] 只解压 codes（几十 KB），但 d["close"] 会解压整个 ~95MB 的 close 矩阵。不要碰你没打算用的键。

## 数据更新后自动生成 NPZ 缓存

`update_data.py` 的 `main()` 完成增量下载后自动执行 `_build_cache()`，从更新后的 CSV 直接构建 NPZ：

```python
# core/update_data.py 末尾，替换原 _clean_cache()
_build_cache()
```

`_build_cache()` 读取 CSV - 透视字段 - 前向填充 - np.savez_compressed 保存，结构与回测引擎的 `_load_data()` 完全一致。

**关键步骤**：
1. 用 pandas pivot_table 将行格式（多行/股票/日期）转成 (n_stocks, n_days) 矩阵
2. 前向填充停牌日（ffill(axis=1).fillna(0.0)）
3. 过滤非 A 股代码前缀（必须与 get_all_stocks() 同步）
4. 同步 is_st 和 exchange 数组（通过 names.index 映射）

**A 股有效前缀**（必须在 get_all_stocks() 和 _build_cache() 两处一致过滤）：

```python
a_prefixes = {"000","001","002","003","300","301","302","303",
              "600","601","603","605","688"}
```

未过滤时 NPZ 含 6691 只（含 B 股/债券/基金代码），过滤后 5241 只。

**清理进度日志文件**：非 A 股过滤后，`_update_progress.txt` / `_update_errors.txt` / `_update_log.txt` / `_fund_errors.txt` 中的旧记录（包含非 A 股代码）已无效，需手动清理。CSV 也需重新清洗过滤（脱敏前含 1450 只非 A 股 = 318 万行）。

## Pitfall: read_stats CSV 读取格式 — csv.DictReader vs csv.reader

`core/app_utils.py` 中的 `read_stats()` 必须使用 `csv.DictReader`（返回 dict），**不能**用 `csv.reader`（返回 list）：

```python
# ✓ 正确：返回 {"总收益率": "134.17%", "年化收益率": "12.5%", ...} — 全部字段
def read_stats(csv_path):
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row
    return {}

# ❌ 错误：只返回 {header[0]: val, header[1]: val} — 只有前2列
def read_stats(csv_path):
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    header = rows[0]
    return {header[0]: row[0], header[1]: row[1]}
```

**症状**：`populate_tree()` 中 `stats.get("总收益率", "—")` 全部返回 "—"，策略列表所有统计数据显示为横线。同时影响 "添加到实盘" 功能（`cum_ret = stats.get("总收益率", "—")` 取不到值）。

**原因**：`csv.DictReader` 使用 CSV 首行作为 key，返回 `OrderedDict`。`csv.reader` 返回 `list`，手动构建 dict 时容易遗漏字段。

**在 `read_stats` 从 app.pyw 迁移到 core/app_utils.py 时必须检查**：旧版内联的是 DictReader，新版若误写成 reader 就会导致此 bug。

## Pitfall: 代码拆分时函数实现差异

将函数从 `app.pyw` 移到 `core/app_utils.py` 时，**必须逐行对比新旧实现**，不能只看函数签名和返回值。本例中 `read_stats` 和 `_parse_label` 的实现在迁移过程中与内联版本不一致，导致数据读取异常。

检查清单：
1. 数据格式（DictReader vs reader）
2. 正则模式（单引号 `'"'` vs 双引号 `'"'` 的处理差异）
3. 错误处理（return {} vs raise）
4. 导入依赖（csv / re 是否在函数内 import）

最佳实践：迁移后运行一次全量回测列表刷新，观察统计数据是否正常显示。

## 关联参考文件

| 文件 | 内容 |
|------|------|
| `references/realtime-stock-quotes.md` | 新浪免费实时行情 API 接入模式 |
| `references/a-share-code-filtering.md` | A股代码前缀白名单过滤（排除B股/债券） |
| `references/fundamentals-api.md` | 基本面数据 API 选择与转置逻辑 |
| `references/auto-develop-visible-terminal.md` | 自动研发 visible 终端模式 |
| `references/editable-treeview-cell.md` | Treeview 可编辑单元格 |
| `references/last-position-date.md` | 策略最后持仓日期的读取 |
| `references/realtime-stock-quotes.md` | 新浪免费实时行情 API 接入模式（含代码格式/响应解析） |
| `references/resource-leak-audit.md` | 资源泄漏审计 |
| `references/stock-code-leading-zeros.md` | 股票代码前导零修复 |
| `references/windows-schtasks-from-gitbash.md` | Windows 任务计划程序从 git-bash 操作 |