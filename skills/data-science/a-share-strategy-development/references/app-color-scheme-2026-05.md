# app.pyw 配色迭代记录 (2026-05-16)

## 最终定稿：Dracula 主题 (v9)

### 颜色常量

```python
# ── 配色方案（Dracula）──
BG_PRIMARY = "#282a36"        # 主背景
BG_SECONDARY = "#2d2f3e"      # 面板背景
BG_TERTIARY = "#383a4a"       # 代码区/输入框
FG_PRIMARY = "#f8f8f2"        # 主文字（暖白）
FG_SECONDARY = "#6272a4"      # 次要文字（注释紫灰）
FG_GREEN = "#50fa7b"          # 正收益（Dracula 绿）
FG_RED = "#ff5555"           # 负收益（Dracula 红）
ACCENT_BLUE = "#8be9fd"       # 蓝色强调（Dracula 青）
ACCENT_GREEN = "#2e8b57"      # 绿按钮
ACCENT_RED_BG = "#da3633"     # 红按钮
ACCENT_GOLD = "#ffb86c"       # 警告（Dracula 橙）
BORDER = "#44475a"            # 边框（当前行色）
TABLE_STRIPE = "#222432"      # 表格交替行
HOVER = "#44475a"             # 悬停（当前行色）
```

### 选中行

背景 `#bd93f9`（Dracula 紫），文字 `#1a1a2e`（深色），通过 style.map 实现：

```python
style.map("Treeview", background=[("selected", "#bd93f9")],
          foreground=[("selected", "#1a1a2e")])
```

### Python 语法高亮（v9 新增）

代码编辑器绑定 `<KeyRelease>`，使用 `Text.tag_configure` + 正则分词：

| 元素 | Dracula 色号 | 说明 |
|------|-------------|------|
| 关键字 | `#ff79c6` | def, class, if, for, import... |
| 字符串 | `#f1fa8c` | "...", '...', """...""" |
| 注释 | `#6272a4` | # 开头到行末 |
| 数字 | `#bd93f9` | 整数、浮点数 |
| 装饰器 | `#50fa7b` | @staticmethod 等 |
| 内置函数 | `#8be9fd` | print, len, range... |

### 运行按钮

列表标题下方（左侧面板），`▶ 全量回测`（绿#1f883d）和 `▶ 运行选中`（蓝，调用时从ACCENT_BLUE取值）。点击后调用 `subprocess.Popen(f'start "标题" cmd.exe /k "cd /d {dir} && python ..."', shell=True)` 弹出新的 cmd 窗口。

---

## 迭代历程

| 版本 | 主题 | 问题 |
|------|------|------|
| v1 | 原版 `#0f172a/#1e293b` | 灰蒙蒙看不清 |
| v2 | 高对比 `#000000/#ffffff` | 太刺眼，红绿大色块 |
| v3 | 高级暗色 `#0a0a0c/#d4d4d8` | 又看不清了 |
| v4 | 高对比 v2 `#0c0c0f/#ffffff` | 强调不够 |
| v5 | VS Code 暗色 | 用户要 Monokai |
| v6 | Monokai `#272822/#f8f8f2` | 用户要 Dracula |
| v7 | Dracula 初版 | 选中行亮色看不清 |
| v8 | Dracula + 选中行深色定稿 | OK |
| v9 | Dracula + Python 语法高亮 + cmd窗口运行 | OK |

### 关键教训

1. **颜色要一次到位**：来回改配色比写代码还耗时。最好先确认主题（Dracula），再微调（选中色）。
2. **红绿行着色被拒**：整行变红/绿来表示收益正负的做法用户认为"不高级"。改用中性交替行，保留红绿色号供指标文字使用。
3. **三层底色必须有明显亮度梯度**：初始版本 BG 三阶层差 <10%，在普通显示器上全部糊成一片黑。最终版差距约 10%/15% 亮度阶梯（`#282a36 → #2d2f3e → #383a4a`），分层清晰可辨。
4. **tag_configure 必须在 self.tree 创建之后调用**：否则报 `AttributeError: '_tkinter.tkapp' object has no attribute 'tree'`。
5. **tkinter Treeview 不支持单列着色**：tag foreground 作用于整行，无法只给"总收益率"列单独着绿色。要么整行着色，要么不做。
6. **subprocess 内嵌日志窗口不可行**：无控制台环境下 `subprocess.PIPE` 有编码/缓冲问题。改用 `start cmd.exe /k` 弹出原生 cmd 窗口更可靠。
7. **FreeConsole + 延迟线程**：`FreeConsole()` + `ShowWindow(GetConsoleWindow(), 0)` 双重控制台隐藏，延迟 0.1s 确保窗口已创建。
