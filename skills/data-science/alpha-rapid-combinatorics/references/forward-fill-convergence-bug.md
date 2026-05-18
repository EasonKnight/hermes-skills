# forward_fill_alpha 收敛漏洞

## 发现时间
2026-05-18，用户反馈"几乎所有策略的回测表现都变得差不多了"

## 根因
`forward_fill_alpha` 使用 `np.maximum.accumulate(a_safe, axis=1)` 对 z-score 值做累计最大值前向填充。

**机制**：
- z-score 是跨截面归一化得分（约 50% 正、50% 负，范围 -3~+3）
- `np.maximum.accumulate` 取的是沿 time 轴的 **running maximum**
- 某股 t=1 时 z=+3.5，t=2 时 z=-2.0 → 因为 +3.5 > -2.0，α 被保持在 +3.5
- 几周后几乎每只股票都累积了足够高的历史最大 z-score → 全部 α > 0 → 全被选中
- 所有策略最终持有同样的股票池 → 表现完全趋同

## 影响范围
所有使用 `forward_fill_alpha` 的 alpha 策略（约 90+ 个策略）。修复前：
- 所有策略年化收益率集中在 8.5%~8.75%（+-0.2%）
- 日均选股 ~420 只（CSI1000 前 50%）
- 超额收益 -16%~-20%，夏普 -0.09~-0.12

修复后：
- A212 非流动性溢价：12.77% 年化，超额 +83.48%
- A202 低波：8.88% 年化，超额 -13.15%
- A201 反转：6.58% 年化，超额 -57.51%
- A357 流动性改善：4.91% 年化，超额 -84.81%
- 日均选股降至 200~250 只（分化正常）

## 修复

**错误实现**（v2 转换器遗留）：
```python
def forward_fill_alpha(a, f):
    n_s, n_d = a.shape
    a_safe = np.where(np.isfinite(a), a, -1e10)
    a_ff = np.maximum.accumulate(a_safe, axis=1)  # 对 z-score 取累计最大值！
    a_ff[a_ff < -1e9] = -np.inf
    a_ff[:, 0] = np.where(f[0], a[:, 0], -np.inf)
    return a_ff
```

**正确实现**：
```python
def forward_fill_alpha(a, f):
    n_s, n_d = a.shape
    idx = np.where(f, np.arange(n_d), -1)      # 调仓日标记索引
    ff_idx = np.maximum.accumulate(idx)          # 向前传播最后一个调仓日的列号
    return a[:, ff_idx]                          # 用 ff_idx 查 α
```

## 验证方法

跑两个逻辑差异大的策略，检查年化收益之差：
```bash
# 预期修复后差值 > 3%（修复前 < 0.2%）
python strategies/a212_amihud_illiq_weekly.py | grep "年化收益率"
python strategies/a357_illiq_imp_momentum_weekly.py | grep "年化收益率"
```
