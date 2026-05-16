# App开发陷阱记录

## 1. `_get_sort_key()` COLUMNS索引 ≠ 数据元组索引

**现象**：点击"创建时间"列头排序不生效，顺序始终不变。

**根因**：`_get_sort_key()` 用 `enumerate(COLUMNS)` 拿到 `idx`，然后试图用 `item[idx]` 从策略数据元组取值。但 `COLUMNS` 是展示列定义（6列），而数据元组是 `(label, stats, equity, src_path, created)`（5字段），两者的索引**从第2项开始就不同了**：

| 字段 | COLUMNS idx | 数据元组 idx | 是否对齐 |
|:----|:----------:|:-----------:|:-------:|
| name | 0 | 0 | ✅ |
| ret (从stats取) | 1 | — | ✅ (不走item) |
| csi_sharpe (从stats取) | 2 | — | ✅ (不走item) |
| eq_sharpe (从stats取) | 3 | — | ✅ (不走item) |
| turnover (从stats取) | 4 | — | ✅ (不走item) |
| dd (从stats取) | 5 | — | ✅ (不走item) |
| created | **6** | **4** | ❌ item[6]越界→空串→`float("-inf")` |

**修正**：对 `col_id == "created"` 特殊处理，读 `item[4]`：

```python
if col_id == "created":
    val = item[4] if len(item) > 4 else ""
else:
    val = item[idx] if idx < len(item) else ""
```

**教训**：任何从 `item[idx]` 取值的列，必须手动验证 COLUMNS 索引与数据元组索引是否对齐。更安全的做法是用显式映射（如 `{"created": 4}`）而不是沿用 COLUMNS 的枚举索引。

## 1b. 添加新列的完整检查清单

**无论加任何新列，必须验证以下 3+2 步：**

### 必须改的 3 处：
| # | 位置 | 操作 |
|:-:|:----|:----|
| 1 | `COLUMNS` 列表 | 加一行 `(id, 显示名, 宽度, 解析函数, stats_key)` |
| 2 | `Treeview(columns=(..., "新id", ...))` | 把 id 加入列元组 |
| 3 | `populate_tree()` 的 `values=(...)` | 读出新值加入元组，列序要对齐 |

### 必须验证的 2 点：
| # | 验证项 | 检查方法 |
|:-:|:-------|:--------|
| ⚠️ | `_get_sort_key` 是否踩数据元组索引坑 | 如果新列的 `stat_key` 不为 `None`（从 stats dict 取值），安全；如果 `stat_key is None` 且 parser 存在，必须确认 `item[idx]` 不越界 |
| ⚠️ | `on_select()` 中的 `item["values"]` 索引引用 | `item["values"][0]` 是策略名，如果代码用硬编码 `item["values"][5]` 等取特定列值，索引必须与新列对齐 |

**安全原则**：新列优先用 stats dict 存放数据（`stat_key` 不为 None），避免碰数据元组索引。

## 2. 添加扫描维度时漏更新元组解包

`scan_strategies()` 返回 `[(name, stats, equity, src_path, created)]` (5元素) 是 app 的核心数据管道。
**每次修改这个元组的结构**，必须检查以下所有解包点：

| 位置 | 代码 | 后果 |
|------|------|------|
| `_get_sort_key()` | `name = item[0]; stats = item[1]` | 索引偏移报错 |
| `populate_tree()` | `name, stats = entry[0], entry[1]; created = entry[4]` | 索引偏移报错 |
| `on_select()` | `n, stats, equity, src_path = entry[0], entry[1], entry[2], entry[3]` | 同上 |
| `show_detail()` 参数 | `def show_detail(self, name, stats, equity, src_path)` | 调用签名不匹配 |

**教训**：只要动 `scan_strategies()` 的返回元组，就要搜索所有解包它的 `for` 循环和函数签名。

## 3. 双前缀策略文件扫描（s* + a*）

新策略统一用 `a` 前缀后，`scan_strategies()` 需要同时扫描两个 glob：

```python
# ✅ 正确做法
s_files = glob.glob(os.path.join(STRATEGIES_DIR, "s[0-9]*.py"))
a_files = glob.glob(os.path.join(STRATEGIES_DIR, "a[0-9]*.py"))
strategy_files = sorted(s_files + a_files)
```

**注意**：不要用单个 `"[sa][0-9]*.py"` glob——它可能匹配其他无文件（如 `x[0-9]*.py`）。显式列出前缀更安全。

## 4. 前缀 dict 扫描导致策略遗漏

```python
# ❌ 错误做法：用 sNN 前缀做 dict key
glbs = {}
for f in glob.glob("s*.py"):
    prefix = f.split("_")[0]  # "s39_tuned_top3" → "s39"
    glbs[prefix] = f  # "s39_top8_daily.py" 会覆盖 "s39_tuned_top3.py"!
```

当两个策略文件共享 `sNN` 前缀（如 `s39_tuned_top3.py` 和 `s39_top8_daily.py`），dict 模式只保留最后扫描的一个。

**修复**：改用文件路径列表，每个文件独立扫描和解析 label：
```python
# ✅ 正确做法：按文件路径排序扫描
for src_path in sorted(glob.glob("s[0-9]*.py")):
    label, folder = _parse_label(src_path)
    # 每个文件独立处理，不依赖 prefix
```

## 5. 旧结果目录造成列表冗余

`results/` 下可能残留旧版策略的文件夹（如 `S11-双均线金叉`），文件夹名与当前策略的 `folder` 变量不一致（如当前是 `S11-双均线金叉日频`）。如果无 source code 匹配的旧结果也加入列表，用户会看到大量无源码垃圾条目。

**原则**：`scan_strategies()` 只输出 `strategies/` 中有代码文件的策略，`results/` 仅作为 stats/equity 的补充关联。

## 6. `app.vbs` 无终端启动

```vb
CreateObject("Wscript.Shell").Run "app.pyw", 0, False
```

- `0` = 隐藏窗口
- `False` = 不等待退出
- `.pyw` 扩展名本身也会抑制控制台窗口，但 `.vbs` 更可靠
- 放在项目根目录，双击运行

## 7. 代码编辑器 save_code() 需要 compile() 检查

保存前必须 `compile(code, path, "exec")` 做语法检查，否则坏代码会直接写入策略文件，下次回测报错。
语法错误用 `SyntaxError.lineno` 定位行号，展示给用户。

## 8. 结果目录名后缀不匹配（全市场/中证1000）

当策略的 `folder = "S01-等权日频"` 但实际 results 目录是 `S01-等权日频（全市场）` 时，app.py 找不到 stats。

**修复**：`scan_strategies()` 需要智能匹配，按优先级尝试：

```python
# 1) 精确匹配 folder
if folder in results_map: ...
# 2) 尝试 +"（全市场）" 后缀
alt1 = folder + "（全市场）"
# 3) 从 label 提取括号内容用作文本后缀
m = re.search(r'（(.+?)）', label)
alt2 = folder + "（" + m.group(1) + "）"
# 4) 前缀模糊匹配 — 任何以 folder 开头的目录名
for d in results_map:
    if d.startswith(folder): ...
```

这个模式在 `STOCK_POOL` 默认从 "all" 切换到 "csi1000" 后自动生效，
无需手动修改 `folder` 变量。
