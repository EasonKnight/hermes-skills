# _compute_limits 中的视图修改陷阱

## 问题

在 `backtest_utils.py` 的 `TradingRules._compute_limits()` 方法中：

```python
def _compute_limits(self):
    self.limit_up = np.zeros_like(self.close)
    self.limit_down = np.zeros_like(self.close)
    for t in range(1, self.n_days):
        prev = self.close[:, t-1]          # <--- 这是 VIEW，不是 COPY！
        prev[prev == 0] = self.close[:, t][prev == 0]  # <--- 修改了 self.close 原始数据！
        pct = self.limit_pct
        self.limit_up[:, t] = np.round(prev * (1 + pct), 2)
        self.limit_down[:, t] = np.round(prev * (1 - pct), 2)
```

`self.close[:, t-1]` 在 NumPy 中返回一个**视图**（view），而非副本（copy）。`prev[prev == 0] = ...` 实际上是在修改 `self.close` 的原始数据。

## 影响

- 如果某只股票在前一天停牌（close=0），它的历史收盘价会被**永久改写**为今天的收盘价
- 这不会导致回测直接出错，但会**污染历史数据**
- 影响：后续所有依赖 `close` 的指标计算（如收益率、波动率、移动平均线）会使用被修改后的价格
- 数据加载一次后缓存到 NPZ，再次加载时已污染的数据会从 NPZ 读入

## 修复方法

```python
def _compute_limits(self):
    self.limit_up = np.zeros_like(self.close)
    self.limit_down = np.zeros_like(self.close)
    for t in range(1, self.n_days):
        prev = self.close[:, t-1].copy()    # <--- 显式 COPY()！
        prev[prev == 0] = self.close[:, t][prev == 0]
        pct = self.limit_pct
        self.limit_up[:, t] = np.round(prev * (1 + pct), 2)
        self.limit_down[:, t] = np.round(prev * (1 - pct), 2)
```

## 验证方法

```python
# 修复前：修改原始数据
original = loader.close.copy()
rules = TradingRules(close, ...)
# 检查 close 是否被修改
print(np.allclose(original, loader.close))  # False!

# 修复后：原始数据不变
print(np.allclose(original, loader.close))  # True
```

## 教训

NumPy 的切片操作默认返回视图。任何 `arr_slice[condition] = value` 的操作，如果 `arr_slice` 来自切片，都会修改原数组。判断方法：

```python
arr = np.zeros((10, 100))
view = arr[:, 5]    # 视图
copy = arr[:, 5].copy()  # 副本
print(view.base is arr)   # True — 是视图
print(copy.base is arr)   # False — 是副本
```

在需要修改切片值的场景，始终使用 `.copy()`。
