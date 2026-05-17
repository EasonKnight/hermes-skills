# Amihud 非流动性因子优化追踪

## 问题

`core/alpha_utils.py` 中的 `amihud_illiq(close, volume, t, n=20)` 每次调用都计算 `amt = np.maximum(close * volume, 1)`——即 **5203×2426 的全矩阵乘法**。若在策略的日循环中调用（如 `for t in range(n_days): h[:,t]=amihud_illiq(...)`），就是 2426 次全矩阵乘法，每次创建临时数组约 100MB。

## 修复

在 `amihud_illiq` 之后新增 `amihud_illiq_fast(amt, close, t, n=20)`：

```python
def amihud_illiq_fast(amt, close, t, n=20):
    """amihud_illiq 的预计算成交额版——amt=close*volume 只需算一次。
    amt : ndarray (N_stocks, N_days) 预计算的成交额矩阵。"""
    start = max(0, t - n)
    if t - start < 5:
        return np.zeros(close.shape[0])
    rets = close[:, start+1:t+1] / np.maximum(close[:, start:t], 1e-10) - 1
    amt_win = amt[:, start+1:t+1]
    ill = np.abs(rets) / amt_win
    return np.nanmean(ill, axis=1)
```

## 已修复策略（8个）

| 策略 | 原循环 | 修复内容 |
|------|--------|----------|
| a212_amihud_illiq_weekly | `range(n_days)`, amihud_illiq w=20 | `range(20,n_d)`, amihud_illiq_fast + 预计算amt |
| a213_amihud_lowvol_weekly | `range(n_days)`, amihud_illiq w=20 | `range(61,n_d)`, amihud_illiq_fast + 预计算amt |
| a215_amihud_monthly | `range(n_days)`, amihud_illiq w=20 | `range(20,n_d)`, amihud_illiq_fast + 预计算amt |
| a219_illiq_40d_weekly | `range(n_days)`, amihud_illiq w=40 | `range(40,n_d)`, inline Amihud计算 + 预计算amt |
| a264_liquidity_slope_weekly | `range(n_d)`, amihud_illiq×2 (w=5, w=40) | `range(40,n_d)`, amihud_illiq_fast×2 + 预计算amt |
| a268_amihud_price_pos_weekly | `range(60,n_d)`, amihud_illiq w=20 | amihud_illiq_fast + 预计算amt |
| a269_amihud_vol_ratio_weekly | `range(20,n_d)`, amihud_illiq w=20 | amihud_illiq_fast + 预计算amt |
| a280_lowprice_illiq_weekly | `range(40,n_d)`, amihud_illiq w=40 | amihud_illiq_fast + 预计算amt |

## 性能对比（5203只股票，2426交易日）

| 指标 | 原版 | 优化后 |
|------|------|--------|
| a212 回测耗时 | ~数分钟 | ~2-3秒 |
| a219 回测耗时 | ~数分钟 | ~1-2秒 |
| 数据加载 | 每次策略~1.5s | 仅一次~1.5s(batch_run) |

## 排查清单

未来发现任何策略回测异常慢时：
1. 检查策略循环内是否调用了 `amihud_illiq`、`np.nanmean(close, axis=1)` 或其他涉及全维度矩阵的操作
2. 将全矩阵操作提到循环外预计算
3. 检查 loop range 是否合理（不要 `range(n_days)` 从0开始，应从 lookback 窗口开始）
