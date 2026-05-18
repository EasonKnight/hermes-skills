# 全矩阵向量化模式速查

## 批处理函数（alpha_utils.py）

| 函数 | 用途 | sliding_window_view padding |
|------|------|:--------------------------:|
| `vol_n_batch(close, n)` | 滚动波动率 | pad `n-1` zeros |
| `amihud_illiq_batch(amt, close, n)` | Amihud 非流动性 | pad `n-1` zeros |
| `amount_ratio_batch(close, vol, n)` | 成交额比例 | pad `n-1` zeros |
| `price_position_batch(close, n)` | 价格分位 [0,1] | pad `n-1` NaN |
| `decay_linear_batch(x, d)` | 线性衰减加权MA | pad `d-1` zeros |
| `ret_n_batch(close, n)` | N日收益率 | 无padding（全量索引） |
| `zscore_rank_matrix(values, mask)` | 逐日截面z-score | 无padding |
| `forward_fill_alpha(a, f)` | 周频forward-fill | 向量化maximum.accumulate |

## sliding_window_view padding 铁律

`sliding_window_view(x, window_shape=n, axis=1)` 的输出维度 = `x.shape[1] - n + 1`。

要得到 `(N_s, N_d)` 的输出，需先 pad 到 `(N_s, N_d + n - 1)`：

```python
padded = np.column_stack([np.zeros((n_s, n - 1)), x])  # ← n-1 不是 n！
windows = sliding_window_view(padded, window_shape=n, axis=1)
result = np.nanmean(windows, axis=2)  # (N_s, N_d)
```

**常见错误**：pad `n` 列 → 输出多一维 → broadcast 报错。

## 引擎优化

`_alpha_to_weights` 在 `alpha_top_pct >= 1.0`（默认）时可全矩阵向量化：

```python
# ❌ 慢（2426次 Python 调用）
for t in range(n_days):
    sig_t, w_t = _alpha_to_weights(signal[:, t], valid[:, t], top_pct)

# ✅ 快（全矩阵一次）
sig_bool = (signal > 0) & valid
weights = np.maximum(signal, 0.0)
w_sum = weights.sum(axis=0, keepdims=True)
weights = weights / np.where(w_sum > 0, w_sum, 1.0)
```

## 周频 forward-fill

策略 `generate_alpha` 中，非调仓日 α 沿用上一周的值：

```python
a_weekly = np.where(f, a, -np.inf)
a = forward_fill_alpha(a_weekly, f)
```

## 手续费分买卖计算

| 方向 | 佣金 | 滑点 | 印花税 | 合计 |
|------|:---:|:---:|:-----:|:---:|
| 买入 | 万3 | 千1 | 0 | 千1.3 |
| 卖出 | 万3 | 千1 | 万5 | 千1.8 |
