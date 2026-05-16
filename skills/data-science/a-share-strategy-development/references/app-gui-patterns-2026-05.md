# App GUI Patterns & Pitfalls

## Window Layout & Widgets

### PanedWindow vs Notebook

PanedWindow (split pane) 让图表和代码同时可见，但有两个问题：
1. `PanedWindow.add(child, weight=1)` 在 tkinter 中不支持 —— `weight` 不是合法参数，会抛出 `_tkinter.TclError: unknown option "-weight"`
2. 用户最终偏好标签页切换而非同时显示

**结论**：用 `Notebook` 标签页分隔图表和代码，不要用 `PanedWindow`。

### Chart Canvas Auto-Resize

```python
self._raw_pil_img = None  # 存储原始 PIL Image

def show_detail(self, ...):
    self._raw_pil_img = Image.open(equity)
    self._render_chart()
    # 绑定时用 add="+" 避免覆盖其他绑定
    self.img_canvas.bind("<Configure>", self._on_canvas_resize, add="+")

def _on_canvas_resize(self, event=None):
    if self._raw_pil_img:
        self._render_chart()

def _render_chart(self):
    cw = self.img_canvas.winfo_width() - 16
    ch = self.img_canvas.winfo_height() - 16
    if cw < 100 or ch < 100:
        return
    ratio = min(cw / img.width, ch / img.height)
    new_w = max(200, int(img.width * ratio))
    new_h = max(150, int(img.height * ratio))
    img_small = img.resize((new_w, new_h), Image.LANCZOS)
    self._tk_img = ImageTk.PhotoImage(img_small)
    # 居中显示
    x = (cw - new_w) // 2 + 8
    y = (ch - new_h) // 2 + 8
    self.img_canvas.create_image(x, y, anchor="nw", image=self._tk_img)
```

**要点**：
- `self._tk_img` 必须保存为实例属性，否则被 GC 回收图片不显示
- 画布不需要滚动条（图片自适应画布大小）
- 先检查尺寸是否有效（`<Configure>` 在 widget 刚创建时会触发，此时宽高可能为零）

### Running Subprocess from Tkinter GUI

**问题**：在 tkinter 无控制台窗口（.pyw）环境中，`subprocess.run(capture_output=True)` 以及复杂的管道处理容易因编码/缓冲/控制台句柄问题失败。

**解决方案**：直接打开 Windows cmd 窗口运行命令，不捕获输出。

```python
d = os.path.dirname(os.path.abspath(__file__))
subprocess.Popen(
    f'start "标题" cmd.exe /k "cd /d {d} && python -m core.platform run"',
    shell=True)
```

**参数说明**：
- `start "标题"` —— 设置 cmd 窗口标题，方便识别
- `cmd.exe /c` —— 运行完自动关闭（用户要求不保留窗口）
- `shell=True` —— 必需，因为 `start` 是 cmd 内置命令
- 路径如果含空格需要用 `"` 包裹

**"全量回测"按钮注意**：
- `run_all.py` 使用 `multiprocessing.Pool`，在 GUI 子进程中因 Windows 多进程 fork 限制不可用
- 改用 `core.platform run`（顺序运行，无此问题）

### 刷新按钮记住选中策略

```python
def refresh(self):
    prev_name = self._selected_name
    self.strategies = scan_strategies()
    self.sort_by(self.sort_col)
    if prev_name:
        for n, stats, equity, src_path in self.strategies:
            if n == prev_name:
                self.show_detail(n, stats, equity, src_path)
                for row in self.tree.get_children():
                    if self.tree.item(row, "values")[0] == n:
                        self.tree.selection_set(row)
                        self.tree.focus(row)
                        self.tree.see(row)
                        break
                return
    # 找不到则清空详情
```

## Console Hiding (Windows)

### 问题

在 Windows 上，即使 `.pyw` 文件关联了 `pythonw.exe`，仍可能出现控制台窗口。

### 多级方案（按可靠性排序）

**方案 1 — launch.vbs（最可靠）**：
```vb
CreateObject("Wscript.Shell").Run "app.pyw", 0, False
```
参数 `0` = 隐藏窗口。无任何闪动。

**方案 2 — 延时线程 + ShowWindow + FreeConsole（app 内）**：
```python
import threading
def _hide_console():
    import time, ctypes
    time.sleep(0.1)  # 等待控制台创建
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 0)  # SW_HIDE
        kernel32.FreeConsole()      # 分离控制台
threading.Thread(target=_hide_console, daemon=True).start()
```

**方案 3 — 直接 FreeConsole（可能失效）**：
```python
ctypes.windll.kernel32.FreeConsole()
```
如果控制台尚未创建，`FreeConsole()` 无效果。所以需要延时。

**不要用** `user32.ShowWindow(kernel32.GetConsoleWindow(), 0)` 写在模块顶层——窗口尚未显示时获取不到 handle。

## Python Syntax Highlighting in tkinter Text Widget

基于正则的逐行高亮方案：

```python
self.code_text.tag_configure("kw", foreground="#ff79c6")
self.code_text.tag_configure("str", foreground="#f1fa8c")
self.code_text.tag_configure("cmt", foreground="#6272a4")
self.code_text.tag_configure("num", foreground="#bd93f9")
self.code_text.tag_configure("dec", foreground="#50fa7b")
self.code_text.tag_configure("bif", foreground="#8be9fd")
self.code_text.bind("<KeyRelease>", lambda e: self._highlight_code())

def _highlight_code(self):
    import re
    for tag in ("kw", "str", "cmt", "num", "dec", "bif"):
        self.code_text.tag_remove(tag, "1.0", END)
    content = self.code_text.get("1.0", END)
    # 处理顺序：注释→字符串→关键字→装饰器→数字→内置函数
    for m in re.finditer(r'#[^\n]*', content):
        self.code_text.tag_add("cmt", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
    for m in re.finditer(r'""".*?"""|\'\'\'.*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'',
                         content, re.DOTALL):
        self.code_text.tag_add("str", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
    keywords = r'\b(?:def|class|if|elif|else|for|while|...)\b'
    for m in re.finditer(keywords, content):
        self.code_text.tag_add("kw", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
    # ... 装饰器、数字、内置函数同理
```

**注意**：每次 `<KeyRelease>` 触发全量重绘，在长文件（>500行）时可能有轻微卡顿。不要在重绘中加入复杂逻辑（如避开字符串内的匹配）。

## Dracula Theme Final Colors

定稿于 2026-05-16：

| 元素 | 颜色 | 用途 |
|------|------|------|
| BG_PRIMARY | `#282a36` | 主背景 |
| BG_SECONDARY | `#2d2f3e` | 面板背景 |
| BG_TERTIARY | `#383a4a` | 代码区、输入框 |
| FG_PRIMARY | `#f8f8f2` | 主文字 |
| FG_SECONDARY | `#6272a4` | 次要文字、注释 |
| FG_GREEN | `#50fa7b` | 正收益 |
| FG_RED | `#ff5555` | 负收益 |
| ACCENT_BLUE | `#8be9fd` | 蓝色强调 |
| ACCENT_GREEN | `#1f883d` | 绿按钮 → 改为 `#1a5e2a`（更深） |
| ACCENT_RED_BG | `#da3633` | 红 |
| ACCENT_GOLD | `#ffb86c` | 警告/金色 |
| BORDER | `#44475a` | 边框、分割线 |
| TABLE_STRIPE | `#222432` | 表格交替行 |
| HOVER | `#44475a` | 悬停 / 选中行背景 |
| SELECT_BG | `#bd93f9` | 紫色选中行背景 |
| SELECT_FG | `#1a1a2e` | 选中行文字（深色确保在紫色上可读） |

**按钮颜色**：\n- "全量回测"：默认 `#1a5e2a`（深绿），悬停 `#0f4a1e`\n- "运行选中"：默认 `#2b6cb0`（深蓝），悬停 `#1a56db`\n- 禁用状态：使用 `disabledforeground="white"` 保持白色文字

**表格选中行**：紫色 `#bd93f9` + 深色文字 `#1a1a2e`（非白色，因为亮紫+白字看不清）。头两轮尝试了 `#44475a`（用户说太浅）和亮青色（用户说刺眼），最终紫色最合适。

## Tuple Unpacking Future-Proofing

**问题**：当策略元组从4元素扩展为5元素（新增「创建时间」列）时，所有固定元组解包（如 `for n, stats, equity, src_path in ...` 和 `name, stats, _, _ = item`）都会引发 `ValueError: too many values to unpack`，导致排序和列表加载崩溃。

**修复**：所有策略数据访问改用索引而非解包：

```python
# ❌ 固定解包（加列就崩）
for n, stats, equity, src_path in self.strategies:
    ...

# ✅ 索引访问（加列也兼容）
for entry in self.strategies:
    n, stats, equity, src_path = entry[0], entry[1], entry[2], entry[3]
    ...

# ✅ _get_sort_key 同理
name = item[0]
stats = item[1]
```

同样适用于 `populate_tree()` 和任何访问 `self.strategies` 元组的地方。

## 自动研发按钮（2026-05-16 新增）

紫色按钮 `#6d28d9`，点击后打开 cmd 窗口运行 Hermes 并传入提示词自动开发策略：

```python
def auto_develop(self):
    import subprocess, tempfile, os
    prompt = "调用你的股票量化策略开发skill，新编写一个量化策略"
    # 写提示词到临时文件，避免 cmd 中文编码问题
    tmp = os.path.join(tempfile.gettempdir(), "hermes_prompt.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(prompt)
    d = os.path.dirname(os.path.abspath(__file__))
    cmd = f'start "🤖 自动研发" cmd.exe /k "type {tmp} | hermes & del {tmp}"'
    subprocess.Popen(cmd, shell=True)
```

**注意事项**：
- 中文提示词通过临时文件传递，避免 cmd 命令行编码问题
- 使用 `type {tmp} | hermes` 管道输入，`& del {tmp}` 清理临时文件
- `cmd.exe /k` 保持窗口打开，方便查看 Hermes 输出

策略列表新增「创建时间」列，显示策略文件创建日期（`mm-dd HH:MM` 格式）。

```python
def _fmt_time(fp):
    try:
        ts = os.path.getctime(fp)
        from datetime import datetime
        return datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")
    except:
        return ""
```

需要同步更新的地方：
1. `COLUMNS` 列表添加 `("created", "创建时间", 110, None, None)`
2. `scan_strategies()` 返回的元组从4元素扩展为5元素 `(label, stats, equity, src_path, created)`
3. `self.tree` 的 columns 参数添加 `"created"`
4. `populate_tree()` 解包和 `insert()` values 中增加 `created`
5. 所有 `for n, stats, equity, src_path in self.strategies` 改为 `for n, stats, equity, src_path, _ in self.strategies`

`created` 列可通过 `_parse_time()` 排序。`COLUMNS` 中配置 `("created", "创建时间", 110, _parse_time, None)`。`_get_sort_key()` 中新增分支：当 `parser` 存在但 `stat_key` 为 `None` 时，从策略元组对应列索引取数据：`val = item[idx] if idx < len(item) else ""`。需确保 `for cid, ... in enumerate(COLUMNS):` 拿到 `idx`。

当删除策略文件时，必须同时清理：

1. **策略文件**：`strategies/sNN_xxx.py`
2. **结果目录**：`results/SXX-名称/`（如果不清理，app.py 中的 `scan_strategies()` 扫描 strategies/ 时不会再找到这些策略，但僵尸结果目录会残留）

```bash
# 先删策略文件
rm strategies/s41_top10_volume.py
# 再删对应的结果目录
rm -rf "results/S41-涨幅TOP10%+量放大"
```

**Tip**：使用 `core/platform.py` 的 `discover()` 模式可以快速找出无对应策略文件的空壳结果目录。
