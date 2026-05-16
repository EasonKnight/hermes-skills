# App.py 增强：排序 & 无终端启动

## Treeview 点击排序

在 `App.__init__()` 中添加：

```python
self.sort_col = "ret"
self.sort_rev = True
```

为每列绑定 `command`：

```python
for col_id, col_text, col_width, _, _ in COLUMNS:
    self.tree.heading(col_id, text=col_text,
                      command=lambda c=col_id: self.sort_by(c))
```

**`sort_by()` 实现：**

```python
def sort_by(self, col_id):
    if col_id == self.sort_col:
        self.sort_rev = not self.sort_rev
    else:
        self.sort_col = col_id
        self.sort_rev = (col_id != "name")
    self.strategies.sort(
        key=lambda item: self._get_sort_key(col_id, item),
        reverse=self.sort_rev)
    self.populate_tree()
    for cid, col_text, _, _, _ in COLUMNS:
        arrow = " ▲" if cid == col_id and not self.sort_rev else \
                " ▼" if cid == col_id else ""
        self.tree.heading(cid, text=col_text + arrow)
```

**解析函数：** 百分比字符串 `"+134.17%"` → float 134.17，"—" → None 排末尾。

## 列配置常量

```python
COLUMNS = [
    ("name",   "策略名称", 180, None, None),
    ("ret",    "总收益率", 100, _parse_pct, "总收益率"),
    ("sharpe", "超额夏普",  90, _parse_num, "夏普比率"),
    ("dd",     "最大回撤", 100, _parse_pct, "最大回撤"),
]
```

与 `stats.csv` 中的 key 名对应。如果重命名了指标列，COLUMNS 需要同步更新。

## 无终端启动

### 方法一：.pyw 后缀

Windows 下 `.pyw` 关联 `pythonw.exe`，双击不弹出控制台。

### 方法二：VBS 启动器

```vbs
' app.vbs
CreateObject("WScript.Shell").Run _
    "C:\Users\Mayn\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe """ _
    & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) _
    & "\app.pyw""", 0, False
```

双击 `app.vbs` → WScript 调用 `pythonw.exe app.pyw`，无任何窗口。

### 方法三：ctimes delay-thread fallback（2026-05-16 更新 — 最可靠）

```python
import threading
def _hide_console():
    import time, ctypes
    time.sleep(0.1)
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 0)
        kernel32.FreeConsole()
threading.Thread(target=_hide_console, daemon=True).start()
```

**不要在模块顶层直接调用** `ShowWindow(GetConsoleWindow(), 0)`——此时控制台可能尚未创建，`GetConsoleWindow()` 返回 0。延时线程确保窗口已创建。详见 `references/app-gui-patterns-2026-05.md`。
