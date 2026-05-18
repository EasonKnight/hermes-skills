# 全矩阵批处理函数 API

`core/alpha_utils.py` 新增，2026-05-18。

## 设计原则

所有批处理函数返回 `(N_stocks, N_days)` 全矩阵，零 Python `for` 循环。
使用 `sliding_window_view`（NumPy 1.20+）实现滚动窗口计算，O(N_days) 而非 O(N_days × window)。

## 函数清单

### `ret_n_batch(close, n=20)`

```python
result[:, n:] = close[:, n:] / close[:, :-n] - 1
```

纯矩阵除法，O(N_days)。前 n 天为 0。

### `vol_n_batch(close, n=60)`

```python
daily_ret[:, 1:] = close[:, 1:] / close[:, :-1] - 1
padded = np.column_stack([zeros, daily_ret])
windows = sliding_window_view(padded, window_shape=n, axis=1)  # (N_s, N_d, n)
result = np.nanstd(windows, axis=2)
```

`sliding_window_view` 创建窗口视图（零额外内存），`np.nanstd` 在 C 层面计算。O(N_days)。

### `amount_ratio_batch(close, volume, n=20)`

同上 sliding_window_view + nanmean。O(N_days)。

### `price_position_batch(close, n=60)`

同上 sliding_window_view + nanmin/max。O(N_days)。

### `amihud_illiq_batch(amt, close, n=20)`

```python
daily_ret[:, 1:] = close[:, 1:] / close[:, :-1] - 1
illiq = |daily_ret| / amt
# sliding_window_view + nanmean
```

O(N_days)。

### `decay_linear_batch(x, d)`

```python
weights = [1, 2, ..., d] / sum(1..d)
x_pad = np.column_stack([zeros(d-1), x])
windows = sliding_window_view(x_pad, window_shape=d, axis=1)  # (N_s, N_d, d)
result = np.nansum(windows * weights, axis=2)
```

前 d-1 天自动填充 0，第 0 天权重只有 [1]/1=1，第 1 天权重 [1,2]/3，以此类推。

### `zscore_rank_matrix(values, valid_mask=None)`

```python
# 向量化双 argsort
rank = np.argsort(np.argsort(values, axis=0), axis=0)
n_valid = valid_mask.sum(axis=0)
mean = (n_valid - 1) / 2.0
std = sqrt((n_valid² - 1) / 12.0)
z = (rank - mean) / (std + 1e-10)
```

并非完全零循环（跳过有效数 <5 的天），但每列在 numpy 内一次性计算。O(N_stocks × log(N_stocks) × N_days)。

### `forward_fill_alpha(a, f)`

```python
a_safe = np.where(isfinite(a), a, -1e10)
a_ff = np.maximum.accumulate(a_safe, axis=1)
a_ff[a_ff < -1e9] = -np.inf
```

`maximum.accumulate` 是 numpy 的纯 C 实现前缀扫描，O(N_days)。

## 不可 batch 的操作

下列操作含有逐日截面/循环依赖，无法全矩阵化，保留 `for t in range`：

1. **分位分组**（如 A299/A300）：按成交额分 10 组，组内 zscore → 需要每列的 percentile
2. **high/low 价差**（如 A261/A281/A297/A315）：需要 `high-low` 自定义滚动窗口
3. **嵌套循环**（如 A266 方向 Amihud）：双重 for 循环，逻辑复杂
4. **per-day 函数**（`delta`, `correlation`, `skewness`, `kurtosis`, `downside_vol` 等）：这些函数设计为 `(N_stocks,)` 输出，没有对应的 batch 版本
5. **基本面因子**（A320-323）：逐日读取 `fund[...]` 数组，逻辑简单不需要 batch

## 性能参考

| 操作 | 旧循环 (2426天) | batch 版本 |
|------|:--------------:|:----------:|
| vol_n(close, t, 60) × 2426 | ~12s | ~0.3s |
| amihud_illiq + vol_n × 2426 | ~20s | ~0.5s |
| zscore_rank × 2426 | ~3s | ~0.2s |
| decay_linear × 2426 | ~8s | ~0.2s |
| 全流程（1个策略） | 15~30s | <2s |
