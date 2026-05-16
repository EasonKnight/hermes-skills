---
name: a-share-quant-development
category: data-science
description: A股量化策略全流程开发——架构搭建、策略编写、批量回测、结果管理、桌面平台。
trigger: User asks to write, test, modify backtest strategies, mentions 'a_stock_trade', '量化', '回测', or says '进入量化app研发'/'app研发' (app development mode).
---

# A股量化策略开发工作流

## 项目结构

```
a_stock_trade/
├── core/
│   ├── backtest_utils.py    # 引擎（DataLoader, BacktestEngine, Visualizer）
│   └── platform.py          # 轻量平台（自动发现+汇总CSV，零依赖）
├── strategies/              # 每个策略一个 s*.py 文件
│   ├── s67_lowprice_weekly.py
│   └── ...
├── app.pyw                  # tkinter 桌面平台
├── run_all.py               # 旧版批量运行器
├── run_platform.py           # 新版平台入口
├── data/                    # K线数据
└── results/                 # 回测结果
    └── _summary.csv         # 汇总CSV（用于快速排名查询）
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

核心函数只需要 `generate_signal(close, dates, volume)`，返回 bool 矩阵 (N_stocks, N_days)。

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

## 批量运行与排名

```bash
# 新平台（推荐）
python -m core.platform run                     # 全量
python -m core.platform run --tags momentum     # 按标签
python -m core.platform run --names s76         # 按名字
python -m core.platform rank                    # 查排名（从CSV，秒出）
python -m core.platform compare s76 s67         # 对比

# 单个策略（兼容旧方式）
python strategies/s76_lowvol_momentum_weekly.py

# 桌面平台
# 双击 app.pyw 或 launch.vbs
```

### 全量回测 — 后台进程模式

当需要全量重跑所有策略（50+个）时，使用 background terminal 避免阻塞。用 `background=true` + `notify_on_complete=true` 启动，完成后自动通知。进程约2-3分钟跑完50个策略。

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

## app.pyw 桌面平台

### Dracula 主题配色
```python
BG_PRIMARY = "#282a36"       # 主背景
BG_SECONDARY = "#2d2f3e"     # 面板背景
BG_TERTIARY = "#383a4a"      # 代码区
FG_PRIMARY = "#f8f8f2"       # 主文字（暖白）
FG_GREEN = "#50fa7b"         # 正收益
FG_RED = "#ff5555"           # 负收益
ACCENT_BLUE = "#8be9fd"      # 蓝色强调
BORDER = "#44475a"           # 边框
TABLE_STRIPE = "#222432"     # 表格交替行
HOVER = "#44475a"            # 悬停
# 选中行：背景 #bd93f9（紫），文字 #1a1a2e（深色）
```

### 布局规范
- 左面板：策略列表（标题+刷新按钮 → 运行按钮栏 → 策略Treeview）
  - 运行按钮栏：全量回测(绿) | 运行选中(蓝) | 自动研发(紫) | 停止(暗红 #7f1d1d)
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
subprocess.Popen(f'start "标题" cmd.exe /c "cd /d {d} && python script"', shell=True)
```
- `run_all` → cmd `/c` 自动关闭
- `run_selected` → `CREATE_NEW_CONSOLE` + 后台线程等进程结束自动 refresh

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
    def run(self, close, signal, dates, ...):
        # ... 回测逻辑 ...
        self._compute_benchmark(close, dates)  # ← 自动计算基准+超额

    def _compute_benchmark(self, close, dates):
        # 从close矩阵计算等权周频组合净值（中证1000股票池）
        # 超额净值 = 1 + nav - bm_nav（差值法，非比值法）
        # 还下载中证1000指数(sh000852)计算csi1000_excess_nav用于图表
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

### 代码编辑器语法高亮
- 5列：名称 | 总收益率 | 超额夏普 | 最大回撤 | 创建时间
- 创建时间列：`os.path.getctime(fp)` → `"%m-%d %H:%M"` → `_parse_time()` 转分钟数排序
- `_get_sort_key()` 用 `enumerate(COLUMNS)` + `item[idx]` 加列即兼容

## 常见陷阱

### USERPROFILE 环境变量
Windows的 `os.path.expanduser("~")` 依赖 `USERPROFILE` 环境变量。如果被污染（如终端输出串入），需要在命令前加：
```
USERPROFILE="C:\Users\Mayn" python script.py
```

### 回测日期裁剪
通过 `core/backtest_utils.py` 中的 `BACKTEST_START` 全局变量控制，或通过 `DataLoader._crop_dates()` 自动裁切。

### 策略文件清理
定期删除无对应results目录的策略文件（使用 `core/platform.py` 的自动检测机制）。
