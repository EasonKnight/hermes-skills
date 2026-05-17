# tkinter 量化桌面 GUI 设计模式

## 三点布局：ttk.PanedWindow（垂直可拖拽）

```python
pw = ttk.PanedWindow(parent, orient=VERTICAL)
pw.grid(row=0, column=0, sticky="nsew", padx=8)
pw.add(section_frame, weight=N)  # 权重 = 初始高度比例
```

用 PanedWindow 替代 `grid rowconfigure weight`，用户可拖拽 sash 自由调整区域高度。

## 列对齐合计条

Treeview 合计行放在表格外固定显示（不随滚动）：

```python
def make_aligned_bar(parent, col_cfgs):
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
```

## Treeview 样式 — 无红绿色着色

**禁止** row-level 的绿色/红色文字标记。所有 Treeview 文字保持统一白色 `#fafafa`。

```python
style.configure("Treeview", foreground=FG_PRIMARY, ...)  # 纯白
style.configure("Treeview.Heading", ..., foreground=ACCENT_CYAN, borderwidth=0, relief="flat")
style.map("Treeview", background=[("selected", "#404040")],
          foreground=[("selected", "#ffffff")])
style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # 去边框
```

> 收益数字仅在详情面板的 stats_text 中显示，不标颜色区别正负。

## 后台线程（避免 I/O 卡 UI）

```python
result = {}
def worker():
    try: result["data"] = expensive_io()
    except Exception as e: result["error"] = str(e)
def poll():
    if not result: self.after(200, poll); return
    # 处理 result
thread = threading.Thread(target=worker, daemon=True).start()
self.after(200, poll)
```

## 轻量缓存（预计算 JSON 代替大文件）

从大文件（NPZ/CSV）提取所需字段到小 JSON，2ms 加载：

```python
def build_cache(npz_path, json_path):
    mtime(npz) > mtime(json) → 从 NPZ 提取 → 写 JSON
    json.load(json_path) → 2ms 加载
```

## 右键菜单

```python
self.tree.bind("<Button-3>", self.show_menu)
self.menu = Menu(self, tearoff=False, bg=..., fg=...)
self.menu.add_command(label="❌ 移除", command=self.remove_item)

def show_menu(self, event):
    iid = self.tree.identify_row(event.y)
    if iid:
        self.tree.selection_set(iid)
        self.menu.post(event.x_root, event.y_root)
```
