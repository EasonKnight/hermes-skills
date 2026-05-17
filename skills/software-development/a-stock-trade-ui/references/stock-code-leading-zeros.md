# 股票代码前导0丢失修复

## 问题

NPZ/CSV 数据在存储时去掉了股票代码的前导0（`000019` → `"19"`），所有从 `position_matrix.csv` / `stock_map.json` 读取的代码都是短码。

## 根因

原始 CSV 的「股票代码」列读入时被 `pandas` 转为整数或 category 时掉了前导0，NPZ 缓存即无前导0的短码。`stock_map.json` 的 keys 均为整数形态（如 `19`, `2101`, `600519`），非6位字符串。

## 修复方式：三步全面应用 `.zfill(6)`

股票代码在3处显示路径各需补0：

### 1. `calc_strat_positions()` — 新计算的持仓

```python
# 从 CSV header 拿到 idx_val（短码如 "19"）
code_6 = idx_val.zfill(6)
positions.append((code_6, name, lots, round(price, 2), final_amount))
```

### 2. `refresh_combined_positions()` — 组合持仓聚合

```python
for code, name, lots, _, amount in pos:
    code = code.zfill(6)  # ✅ 兼容已有JSON中的短码
    ...
```

### 3. `refresh_live_strat_detail()` — 单策略持仓详情

```python
for code, name, lots, price, amount in pos:
    code = code.zfill(6)
    ...
```

## 关键原则

- **在显示路径补0，不在数据源改** — `strategies.json` 可以保持短码，显示时自动补0
- **`.zfill(6)` 幂等** — 已经6位的代码不受影响（"600519".zfill(6) = "600519"）
- **stock_map 查找仍用 `int(code)`** — `int("000019")` = 19，和 stock_map 的 int key 匹配

## 数据一致性

如果先在 `calc_strat_positions()` 中存了6位码到 JSON，而旧数据是短码，用 `.zfill(6)` 统一处理显示层即可，不需要迁移 JSON 数据。
