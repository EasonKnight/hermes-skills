# 小盘因子在CSI1000内研究 (2026-05-16)

## 代理变量
没有市值数据，用成交额(close×volume)作为小盘代理：
```python
amt = c * v  # close * volume
amt_thr = np.nanpercentile(amt_valid, 30)  # 后30%分位
cond_small = (amt <= amt_thr) & valid
```

## 数据特征
- Volume 是 float64，量级 10^6~10^9
- 成交额范围：970 ~ 8.55×10^10（全市场）
- 30th pctile: ~37M（全市场）
- 在 generate_signal 中通过 `volume=loader.volume` 传入

## 发现
在CSI1000（1001~2000th大市值股，中盘为主）内加成交额筛选效果有限：

| 策略 | 年化 | vs 原版 |
|:----|:---:|:-------:|
| S125 小盘均线支撑 | 21.67% | S110 22.50% ≈持平 |
| S127 小盘低价 | 21.34% | S67 20.77% 微幅增强 |

**原因**：CSI1000本身已经是中盘股，内部的"小盘"分化不够大，价差(price)比成交量更能区分尾部。

## 注意事项
- `generate_signal` 签名应包含 `volume=None, **kw` 参数
- 使用 `np.nanpercentile` 而不是 `np.percentile`（避免NaN传播）
- 成交额小盘过滤 + 价格后30%分位会过度筛选，日均持股可能<20只
- 建议设保护：`if cond.sum() < 10: cond = fallback`
