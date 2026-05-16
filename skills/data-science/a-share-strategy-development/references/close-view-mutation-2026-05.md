# `self.close` 视图污染 Bug（2026-05-15）

## 根因

`TradingRules._compute_limits()` 中：

```python
for t in range(1, self.n_days):
    prev = self.close[:, t-1]          # ← 这是 VIEW，不是 COPY
    prev[prev == 0] = self.close[:, t][prev == 0]  # ← 通过 VIEW 修改了原始数据！
```

`self.close[:, t-1]` 返回的是原始 `self.close` 数组的 **view**（不是 copy）。
当 `prev[prev == 0] = ...` 执行时，它直接修改了 `self.close` 中的值。
这意味着历史收盘价（第 `t-1` 天的数据）被悄悄改成第 `t` 天的值。

## 影响

| 阶段 | 受影响的收盘价 | 后果 |
|------|:------------:|:----|
| 第1次循环（t=1） | close[:, 0] 被改成 close[:, 1] | 第0天的价格丢失 |
| 后续循环 | 累积扩散 | 越靠前日期的价格越不准确 |

此 bug 不影响现有策略的 limit_up/down 计算（因为计算自洽），但**任何在 TradingRules 构造后读取 `loader.close` 的代码都会看到错误的历史价格**。

## 修复

```python
for t in range(1, self.n_days):
    prev = self.close[:, t-1].copy()   # ← 加 .copy() 切断 view
    prev[prev == 0] = self.close[:, t][prev == 0]
```

## 验证

```python
loader = DataLoader().load()
close_before = loader.close.copy()
rules = TradingRules(...)
# 修复前：np.any(close_before != loader.close) → True（数据被污染）
# 修复后：np.allclose(close_before, loader.close) → True（数据完好）
```

## 教训

**在 NumPy 中，切片返回的是 view 不是 copy。** 任何需要修改切片内容的场景都需加 `.copy()`：

| 操作 | 是否 View | 需要 .copy() |
|------|:---------:|:-----------:|
| `arr[:, t-1]` | ✅ View | 如果要修改该切片 |
| `arr[t-1:t+1]` | ✅ View | 同上 |
| `arr[[1,3,5]]` | ✅ Copy | 无需（花式索引返回 copy） |
| `arr[arr > 0]` | ✅ Copy | 无需（布尔索引返回 copy） |
