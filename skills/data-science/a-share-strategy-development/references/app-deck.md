# app.py / app.pyw — 桌面策略平台

## 无终端启动 (Windows)

On Windows, Python GUI scripts need `pythonw.exe` to avoid a console window:

| 方式 | 文件 | 原理 |
|------|------|------|
| 推荐 | `app.vbs` | VBScript 调用 `pythonw.exe`，WScript 本身无窗口 |
| Fallback | `app.pyw` | `.pyw` 关联到 `pythonw.exe`；内部也加 `ctypes` 主动隐藏 |

**`app.vbs` 内容**（无黑框闪过）：
```vbs
CreateObject("WScript.Shell").Run "C:\path\to\pythonw.exe """ & _
    CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & _
    "\app.pyw""", 0, False
```

**`app.pyw` 顶部的 fallback：**
```python
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass
```

## Treeview 点击列头排序

全量排序实现（非 Treeview 内置 sort）：

```python
COLUMNS = [
    ("name",   "策略名称", 180, None, None),
    ("ret",    "总收益率", 100, _parse_pct, "总收益率"),
    ("sharpe", "超额夏普",  90, _parse_num, "夏普比率"),
    ("dd",     "最大回撤", 100, _parse_pct, "最大回撤"),
]

def _parse_pct(s):  # "+134.17%" → 134.17, "—" → None
def _parse_num(s):  # "0.72" → 0.72, "—" → None

class App(Tk):
    def __init__(self):
        self.sort_col = "ret"       # 排序列
        self.sort_rev = True        # 默认降序

        for col_id, col_text, col_width, _, _ in COLUMNS:
            self.tree.heading(col_id, text=col_text,
                              command=lambda c=col_id: self.sort_by(c))

    def _get_sort_key(self, col_id, item):
        """item = (name, stats_dict, equity_path)"""
        name, stats, _ = item
        if col_id == "name":
            return name.lower()
        for cid, _, _, parser, stat_key in COLUMNS:
            if cid == col_id and parser and stat_key:
                val = stats.get(stat_key, "—")
                return parser(val) if parser(val) is not None else float("-inf")
        return ""

    def sort_by(self, col_id):
        if col_id == self.sort_col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col = col_id
            self.sort_rev = (col_id != "name")  # 名称升序，数值降序

        self.strategies.sort(
            key=lambda item: self._get_sort_key(col_id, item),
            reverse=self.sort_rev
        )
        self.populate_tree()

        # 表头箭头
        for cid, col_text, _, _, _ in COLUMNS:
            arrow = " ▲" if cid == col_id and not self.sort_rev else \
                    " ▼" if cid == col_id else ""
            self.tree.heading(cid, text=col_text + arrow)
```

## 策略列表过滤

`scan_strategies()` 必须跳过非策略目录（如 `30策略对比`）：
```python
def scan_strategies():
    for d in sorted(os.listdir(RESULTS)):
        full = os.path.join(RESULTS, d)
        if not os.path.isdir(full) or d == "30策略对比":
            continue
        ...
```
