# Treeview 可编辑列 — 实现参考（本次会话产出）

## 场景：实盘策略「分配金额」列改为可输入

### 需求
- 原字段 `capital_pct`（"资金占比"）改为固定分配金额（元）
- 新建策略默认 100000
- 右键菜单 + 双击列均可编辑
- 合计行显示所有策略分配金额总和

### 改动点（app.pyw）

#### 1. 导入
```python
from tkinter import simpledialog, messagebox
```

#### 2. 列头
```python
("capital_pct", "分配金额", 110),  # 原名"资金占比"，宽90
```

#### 3. 默认值（add_to_live 方法）
```python
"capital_pct": "100000",
```

#### 4. 右键菜单
```python
self.live_strat_menu.add_command(label="✏️ 设置分配金额", command=self.edit_allocation_amount)
```

#### 5. 双击绑定
```python
self.strat_tree.bind("<Double-1>", self.on_live_strat_double)
```

#### 6. 双击检测列（含崩溃防护）
⚠️ 必须加守卫，否则双击空白区域/合计行会导致程序闪退

```python
def on_live_strat_double(self, event):
    try:
        iid = self.strat_tree.identify_row(event.y)  # 用 y 定位行
        if not iid:
            return
        vals = self.strat_tree.item(iid, "values")
        if not vals or vals[0] == "📊 合计":  # 跳过合计行
            return
        region = self.strat_tree.identify_region(event.x)
        if region != "cell":
            return
        col = int(self.strat_tree.identify_column(event.x).replace("#", "")) - 1
        if col == 2:  # 分配金额列索引
            self.edit_allocation_amount()
    except Exception:
        pass  # 任何异常静默忽略，避免闪退
```

#### 7. 编辑方法（可复用模板）
```python
def edit_allocation_amount(self):
    sel = self.strat_tree.selection()
    if not sel:
        return
    item = self.strat_tree.item(sel[0])
    vals = item["values"]
    if not vals:
        return
    name = vals[0]
    cur = vals[2] if len(vals) > 2 else "100000"
    new_val = simpledialog.askstring(
        "分配金额", f"请输入「{name}」的分配金额（元）：\n留空或取消保持原值",
        initialvalue=cur, parent=self
    )
    if new_val is None:
        return
    if new_val == "":
        new_val = cur
    try:
        v = float(new_val)
        if v <= 0:
            messagebox.showwarning("无效金额", "分配金额必须大于0", parent=self)
            return
        new_val = str(int(v)) if v == int(v) else str(v)
    except ValueError:
        messagebox.showwarning("无效金额", "请输入有效数字", parent=self)
        return
    strategies = load_live_strategies()
    for s in strategies:
        if s["name"] == name:
            s["capital_pct"] = new_val
            break
    save_live_strategies(strategies)
    self.refresh_live()
    self.refresh_live_strat_detail(None)
```

#### 8. 合计行（refresh_live 方法内）
```python
total_amt = 0
for s in strategies:
    # ... insert row ...
    try:
        raw = (s.get("capital_pct") or "").strip().replace(",", "")
        total_amt += float(raw) if raw else 0
    except (ValueError, TypeError):
        total_amt += 0  # 空缺/异常按0计
total_str = f"{total_amt:,.0f}" if total_amt > 0 else ""
self.strat_tree.insert("", END,
    values=("📊 合计", "", total_str, "", "", ""),
    tags=("total",))
self.strat_tree.tag_configure("total",
    font=("Microsoft YaHei", 10, "bold"),
    foreground=ACCENT_GREEN)
```

### 注意事项
- 字段 `capital_pct` 虽然在 JSON 中命名含 pct，但已改为固定金额（元），命名未改以保持兼容
- 合计行在 `refresh_live()` 中重建，不需要手动清理旧合计行
- 双击绑定不影响原有 `<<TreeviewSelect>>` 事件（双击先触发 select 再触发 double-click）
- 验证确保 float 可转 int（整数金额不显示小数位），非整数也支持但保存为精确值
