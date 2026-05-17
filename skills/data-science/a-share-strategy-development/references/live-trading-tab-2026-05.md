# 实盘策略标签页 + 右键添加入口（2026-05-17 修订版）

## 覆盖的功能

在 `app.pyw` 中新增的实盘相关功能：

### 1. 主窗口标签页架构

主窗口布局改为标题 + 顶层 `ttk.Notebook`（`self.main_notebook`，style=`"Main.TNotebook"`），现在包含：
- `📊 策略回测` — 原有策略列表 + 详情面板
- `🔴 实盘策略` — 新页面

### 2. 实盘策略标签页 (`live_tab`) — 三区 PanedWindow 布局

使用 `ttk.PanedWindow(orient=VERTICAL)` 实现 3 个可拖拽缩放的垂直分区，共 3 个合计元素：

```
┌──────────────────────────────────────┐
│ 第1区: 实盘策略列表 Treeview          │
│  - 📊 合计 行 (self.strat_tree合计行) │  ← 合计① (Treeview行, 10号)
│                                       │
├──────────────────────────────────────┤
│ 第2区: 组合持仓 Treeview + 合计条     │
│  - 📦 组合持仓 (pos_tree)            │
│  - 合计条 (pos_bar)                  │  ← 合计② (Label条, 9号)
├──────────────────────────────────────┤
│ 第3区: 策略持仓 Treeview + 合计条     │
│  - 🎯 选择上方策略查看持仓计算 (sp_tree)│
│  - 合计条 (sp_bar)                   │  ← 合计③ (Label条)
└──────────────────────────────────────┘
```

三个区用 `make_aligned_bar()` 或 `tree.insert(tags=("total",))` 展示合计：

| 合计 | 位置 | 实现方式 | 默认字号 |
|:---:|:----|:--------|:-------:|
| ① | 第1区末尾 | `self.strat_tree.insert(tags=("total",))` | 10 bold |
| ② | 第2区下方 | `make_aligned_bar(pos_sec, POS_COLS)` | 9 bold |
| ③ | 第3区下方 | `make_aligned_bar(sp_sec, SP_COLS)` | 9 bold |

### 3. 列定义

**strategy treeview** (`STRAT_COLS`): `name`(策略名称), `status`(状态), `capital_pct`(分配金额), `signal`(最新信号), `cum_return`(累计收益), `created`(创建日期)

**combined positions** (`POS_COLS`): `code`(股票代码), `pname`(股票名称), `direction`(方向), `shares`(持仓), `price`(现价), `amount`(市值), `pct`(占比)

**strategy positions** (`SP_COLS`): `code`(股票代码), `pname`(股票名称), `direction`(方向), `lots`(目标手数), `price`(参考价), `amount`(占用资金), `pct`(占比)

### 4. 数据文件

- `live/strategies.json` — 实盘策略列表（数组，每项含 name/status/capital_pct/signal/cum_return/created）
- `live/positions.json` — 持仓明细（数组，每项含 code/name/shares/cost/pnl_pct）

**必须使用空数组 `[]` 初始化，不得填充示例数据。**

### 5. 模块级函数

```python
LIVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live")

def load_live_strategies():    # → list[dict]
def save_live_strategies(list):  # 覆盖写入
def load_live_positions():     # → list[dict]
```

### 6. 右键添加到实盘

`self.tree`（回测策略列表）绑定 `<Button-3>` → `show_strat_menu(event)`：

```python
def show_strat_menu(self, event):
    iid = self.tree.identify_row(event.y)
    if iid:
        self.tree.selection_set(iid)
        self.strat_menu.post(event.x_root, event.y_root)
```

菜单（`self.strat_menu`）只有一项：`➕ 添加到实盘` → `add_selected_to_live()`

```python
def add_selected_to_live(self):
    # 1. 获取选中策略的名称和统计数据
    name = item["values"][0]
    stats = 从 self.strategies 查找 name 对应的 stats dict
    cum_ret = stats.get("总收益率", "—")
    created = item["values"][6]  # 创建时间列
    # 2. 构造新策略 dict，默认 status="运行中"
    # 3. 去重：同名不重复添加
    # 4. 追加到 live/strategies.json
    # 5. 调用 self.refresh_live() 刷新实盘页面
```

### 7. 实盘刷新方法

```python
def refresh_live(self):
    # 清空 strateg_tree → 加载 load_live_strategies()
    # 清空 pos_tree → 加载 load_live_positions()
    # 清空 sp_tree
    # 从 self.strat_tree / self.pos_tree / self.sp_tree 删除所有行后重新插入
    # 更新 3 个合计行/条
```

### 8. 回测列表实盘策略置顶

`populate_tree()` 中，读取 `live/strategies.json` 获取已添加的实盘策略名，
将 `self.strategies` 按"实盘策略在前、其余在后"排序后插入 Treeview：

```python
live_names = {s["name"] for s in load_live_strategies()}
live_entries = [e for e in self.strategies if e[0] in live_names]
other_entries = [e for e in self.strategies if e[0] not in live_names]
sorted_entries = live_entries + other_entries
```

实盘策略行使用浅绿背景 `#1a3a1a` 标记（`tag="live"`）。

### 与回测页面的关系

- 回测页面的 `self.tree`（`ttk.Treeview`）跟之前一样在 `left_frame` 中
- 回测页面的 `on_select` 绑定 `<<TreeviewSelect>>` 事件不变
- 实盘页面的三个 Treeview 只读（目前无选中事件绑定）
