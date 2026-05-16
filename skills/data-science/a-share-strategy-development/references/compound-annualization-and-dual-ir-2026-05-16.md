# 复利年化+双IR修复 (2026-05-16)

## 问题1：年化收益率用单利，IR用复利，不一致

`_compute_stats` 在固定基准模式下用单利：`ann_ret = total_ret / years`
等权基准IR用百分比复利：`ann_excess = strat_pct_ann - bm_pct_ann`

结果：年化收益率（单利22.50%）远高于IR隐含的年化超额（复利~1%），用户看到22.50%但IR只有0.08，感觉"全是负数"。

## 修复
`_compute_stats` 统一用复利法，删除固定基准特殊分支：

```python
# ❌ 旧
if fixed_base is not None:
    ann_ret = total_ret / years  # 单利
else:
    ann_ret = (1 + total_ret) ** (1 / years) - 1

# ✅ 新
ann_ret = (1 + total_ret) ** (1 / years) - 1  # 统一复利
```

效果：S110从22.50%变为12.56%，与IR一致。

## 问题2：年化超额用总点数差/年数

原先：`ann_excess = (excess_nav[-1] - 1) / years`
这相当于 `(strat_total_ret - bm_total_ret) / years`。当策略和基准差距很大时（如策略+500% vs 中证+50%），点差450%/10年=45%年化超额，虚高。

## 修复
改为年化相减：`ann_excess = strat_ann - bm_ann`

```python
# ❌ 旧
csi_excess_ret = self.csi1000_excess_nav[-1] - 1.0
ann_csi = csi_excess_ret / years

# ✅ 新
strat_ann = (strat_pct_nav[-1]) ** (1.0 / years) - 1.0
csi_ann = (csi_vals[-1]) ** (1.0 / years) - 1.0
ann_csi = strat_ann - csi_ann
```

## 问题3：CSI1000中证IR计算

`self.csi1000_excess_nav = 1 + strat_pct_nav - csi_vals`
跟踪误差用每日超额的标准差

年化超额 = 策略年化 - 中证年化
跟踪误差 = std(daily_excess) * sqrt(245)
中证IR = 年化超额 / 跟踪误差

注意中证1000指数10年仅+9%（年化0.88%），等权周频基准10年+195%（年化11.55%）。同样策略的中证IR(0.78)远高于等权IR(0.08)。
