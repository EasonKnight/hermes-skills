# 低价 + 非流动性溢价复合策略（A280）

## 因子逻辑

```
因子 = zscore(-close) + zscore(Amihud_40d)
```

两个子因子等权复合：
- **低价因子**：`-close`，绝对价格越低的股票得分越高
- **非流动性因子**：`Amihud_illiq(close, volume, t, 40)`，40天Amihud测度

## 回测结果（CSI1000周频，DECAY=5）

| 指标 | 数值 |
|:---|:----:|
| 总收益率 | +201.55% |
| 年化收益率 | 11.79% |
| 最大回撤 | -36.31% |
| 日均换手 | 3.03% |
| DECAY | 5（达标） |
| 日均选股 | 205只 |
| 中证信息比 | 0.82 |

## 关键发现

1. **换手率极低**（3.03%）。双因子都是慢变信号，天然低换手
2. **复合效果优于纯低价**（S67 11.81%），换手更低
3. **DECAY=5即达标**，无需调优

## 实现要点

```python
price_z = -(close[:,t] - np.nanmean(close[:,t])) / (np.nanstd(close[:,t]) + 1e-8)
illiq = amihud_illiq(close,volume,t,40)
illiq_z = (illiq - np.nanmean(illiq)) / (np.nanstd(illiq) + 1e-8)
h[:,t] = price_z + illiq_z
```
