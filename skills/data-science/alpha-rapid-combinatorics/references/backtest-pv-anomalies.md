# 回测 PV 异常诊断指南

## 现象：首月（或初期）出现大幅异常收益

典型表现：
- 首月 10 个交易日累计 128% 收益
- 每日收益 5%~16%，但持仓股票的加权实际收益仅 ±2%
- 首月后收益曲线急剧变平

## 诊断步骤

### 1. 检查位置矩阵是否每日更新

```python
pm = np.load('results/<FOLDER>/position_matrix.npz', allow_pickle=True)
pos = pm['pos_value']
for t in range(15):
    print(f'Day {t}: {pos[:, t].sum():.2f}')
```

**正常**：位置市值应每天变化（股价波动）
**异常**：days 2~10 完全相同 → 引擎未正确追踪每日盯市

### 2. 对比 CSV daily_return 与实际持仓加权收益

读取持仓和 close 数据，手动计算每日加权收益：

```python
held = np.where(pos[:, t] > 0)[0]
if len(held) > 0 and t > 0:
    rets = close[held, t] / close[held, t-1] - 1
    wsum = pos[held, t].sum()
    w_ret = np.sum(pos[held, t] * rets) / wsum
    print(f'Day {t}: CSV ret={daily.iloc[t].daily_return*100:+.2f}%, w_ret={w_ret*100:+.2f}%')
```

**异常**：两者差异明显（如 CSV=+14.79% vs w_ret=+2.16%）

### 3. 检查 PV 是否异常收敛到 fixed_base

当 `pos_value` 每天相同时，检查 `pv[t]` 是否总是 = fixed_base：

```python
# pv[t] = has_cash + stock_mv
# 如果 stock_mv 每天不变，且 has_cash 被 net_pnl 吸血
# PV 会被锁定在 INIT_CAP 附近
```

### 4. 检查 index_returns 是否在叠加

```python
# 引擎 line 841-847:
# pv[t] += cash_part * index_returns[t]
# 这会在已有 PV 上额外叠加收益
```

## 根因模式

### alpha_mode + 月频信号 + 每日再平衡 的矛盾

**问题产生机制**：

1. **alpha_mode 每天重建仓位**（即使月频信号不变）
   - 非调仓日 `shares[:, t] != shares[:, t-1]`
   - 每天用 `alloc_base * w / close[:, t]` 重新计算目标持股数
   - 由于 `max_position_pct` 限仓，每天部署金额相同
   - 结果：位置矩阵 days 2~10 完全相同（`pos_value = shares * close` 被固定）

2. **net_pnl 错误吸走价差**
   ```python
   net_pnl = sum(cur_pos) - sum(new_pos)   # cur_pos = mark-to-market
   has_cash += net_pnl                       # 价差进入现金
   ```
   当天股价上涨 → `cur_pos > new_pos` → `net_pnl > 0` → 现金增加
   但这个价差是股价变动带来的真实收益，不应作为"调仓 surplus"处理。
   同时如果股价下跌，现金被抽走来填补持仓市值缺口。

3. **index_returns 二次叠加**
   ```python
   prev_stock_mv = sum(shares[:, t-1] * close[:, t-1])
   cash_part = max(0, fixed_base - prev_stock_mv)
   pv[t] += cash_part * index_returns[t]
   ```
   在 PV 已经通过 rebalance 计算完成后，又额外加上现金部分的指数收益。
   对于仅 87.6M 持仓、12.4M 现金的组合，如果指数涨 2%，PV 被额外加 248K。

4. **固定基准法放大幻觉**
   ```python
   daily_ret[t] = (pv[t] - pv[t-1]) / fixed_base
   ```
   P&L 除以 1 亿，不除以实际持仓市值。在 PV 跟踪出错时，分母固定的特性使得错误 P&L 表现为百分比。

### 核心缺陷

月频信号在 `generate_alpha` 中通过 `monthly_filter` 限制信号变化，但 alpha_mode 的引擎仍然每天按目标权重重新调仓。本质上，alpha_mode 的"按权重持仓"逻辑无视了 `forward_fill_alpha` 保留的月频特性——它每天 rebuild 仓位来匹配目标权重，而不是保留前一日的持股。

## 修复方案

### 方案 A：非调仓日不调仓（核心修复）

在 `BacktestEngine.run` 的"正常再平衡"段开头加入检查：
如果 `alpha_mode` 且两日 `signal` 矩阵（raw alpha 得分）完全相同，
说明是同一调仓日 forward-filled 的数据 → 直接延续前一日仓位。

**关键点**：必须比较 **raw signal 矩阵**（`signal[:, t-1] == signal[:, t]`），
而不是比较引擎处理后得出的选股集（`sig_t`）。因为 `_alpha_to_weights` 过滤
了 valid mask/trading rules，导致选股集与真实持仓不一致从而跳过检查。

```python
# 正确：比较 raw alpha 得分向量
if self.alpha_mode and t > 0:
    prev_sig = signal[:, t-1]
    curr_sig = signal[:, t]
    if np.array_equal(prev_sig, curr_sig):
        pos_mv = np.sum(shares[:, t-1] * close[:, t])
        pv[t] = has_cash + pos_mv
        turnover[t] = 0.0
        tc[t] = 0.0
        shares[:, t] = shares[:, t-1].copy()
        continue
```

### 方案 B：移除 `max_position_pct` 限仓双重计费

**问题**：`has_cash += excess_val`（line 815）与 `has_cash += net_pnl`（line 823）
重复计算了限仓释放的现金，导致每日 P&L 虚增（S66 首月 14%/天的根源）。

**机制**：
1. `max_position_pct` 限仓后，`sum(new_pos)` 小于 `alloc_base`
2. `excess_val = sum(target_pos) - sum(capped_pos)` → 现金 +excess_val
3. `net_pnl = sum(cur_pos) - sum(new_pos_after_cap)` → 现金 +net_pnl
4. net_pnl 已经包含了 capped_pos 减少的差值（即 excess_val），重复加回

**修复**：删除 `has_cash += excess_val`，让 `net_pnl` 统一处理所有现金调整。

```python
# 错误（双重计费）：
has_cash += excess_val        # ① 限仓释放的现金
has_cash += net_pnl            # ② net_pnl 里也包含了 cap 释放的部分

# 正确（只留 net_pnl）：
# has_cash += excess_val      ← 删除
has_cash += net_pnl            # 统一处理所有调整
```

**影响范围**：所有使用 `alpha_mode=True` 且 `max_position_pct < 1.0` 的策略。
`excess_val` 和 `net_pnl` 双重加回导致 PV 被系统性高估。修复后总收益率
下降约 30~60 个百分点（S66: 227%→166%, S108: 287%→160%）。

### 方案 C：涨跌停买卖逻辑按实盘规则修正

A 股规则：
- 涨停：不可买，但可卖（之前不可卖，导致无法止盈）
- 跌停：不可卖，但可买（之前不可买，导致无法抄底）

```python
# 错误：
can_buy = ~limit_up & ~limit_down
can_sell = ~limit_up & ~limit_down

# 正确：
can_buy = ~limit_up          # 涨停不可买，跌停可买
can_sell = ~limit_down       # 跌停不可卖，涨停可卖
```

## 完整修复记录（2026-05-18）

| # | commit | 问题 | 效果 |
|---|--------|------|------|
| 1 | 58e37f0 | alpha_mode 非调仓日每日再平衡（比较选股集过于严格） | 修复首月 128% 幻觉（第一版） |
| 2 | 46ab3fc | 涨跌停买卖不对称 | 涨停可卖不可买, 跌停可买不可卖 |
| 3 | 3576644 | 比较 raw signal 替代选股集 + 移除 excess_val 双重计费 | S66 首月 14%/天 → 2%/天 |

## 快速验证修复

跑一个已知策略的前后对比：

```python
# 修复前：首月 128% or 日收益 11-14%
# 修复后：首月+-2% 附近，日收益 0-4%
# 修复后的首月等于次月收益水平
```
