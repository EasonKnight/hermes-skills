# 年化收益率复利法统一 & 双超额夏普 修复记录

## 问题1：年化收益率与IR不一致

### 症状
`_compute_stats` 中固定基准法使用单利 `ann_ret = total_ret / years`，而IR使用百分比复利法。例如S110年化显示22.50%(单利)，但IR基于的百分比年化仅12.56%。两者不一致导致IR数值偏低。

### 修复
`_compute_stats()`：去掉 `fixed_base` 分支，统一用 `(1 + total_ret) ^ (1/years) - 1` 复利法。

```python
# ❌ 旧：固定基准用单利
if fixed_base is not None:
    ann_ret = total_ret / years  # 22.50%
else:
    ann_ret = (1 + total_ret) ** (1/years) - 1

# ✅ 新：统一复利
ann_ret = (1 + total_ret) ** (1/years) - 1  # 12.56%
```

## 问题2：年化超额计算方式

### 症状
`ann_excess = csi_excess_ret / years` 用总点数差/年数，当超额很大时虚高IR。如S110的中证IR达1.25。

### 修复
改为 `ann_excess = strat_ann - bm_ann`（复利年化相减）。同步应用于等权超额和中证超额。

```python
# ❌ 旧：总点数差/年数
ann_csi = csi_excess_ret / years  # 205%/10=20.5% → IR=1.25

# ✅ 新：复利年化相减
strat_ann = (strat_pct_nav[-1]) ** (1/years) - 1
csi_ann = (csi_vals[-1]) ** (1/years) - 1
ann_csi = strat_ann - csi_ann  # 12.56%-0.88%=11.68% → IR=0.78
```

## 问题3：新股上市日导致基准NAV=inf

### 症状
新股上市首日 close[t-1] = 0，`close[t]/close[t-1]-1 = inf`，np.nanmean(inf)=inf，污染基准NAV。

### 修复
```python
rets = close[held, t] / close[held, t-1] - 1
rets = np.where(np.isfinite(rets), rets, 0.0)  # 过滤inf
daily_ret[t] = np.nanmean(rets)
```

## 问题4：双超额夏普（app列表和CSV）

### 新增列
| stats key | app列名 | 含义 |
|-----------|---------|------|
| `信息比率` | 等权夏普 | 策略 vs 等权周频组合的信息比 |
| `中证信息比` | 中证夏普 | 策略 vs 中证1000指数的信息比 |
| `中证超额` | (CSV) | 超额收益差值 |
| `中证跟踪` | (CSV) | 跟踪误差 |

### app.pyw修改
```python
COLUMNS = [
    ("name",    "策略名称", 180, None, None),
    ("ret",     "总收益率", 100, _parse_pct, "总收益率"),
    ("csi_sharpe", "中证夏普",  90, _parse_num, "中证信息比"),
    ("eq_sharpe",  "等权夏普",  90, _parse_num, "信息比率"),
    ("dd",      "最大回撤", 100, _parse_pct, "最大回撤"),
    ("created", "创建时间", 110, _parse_time, None),
]
```

### platform.py CSV修改
在 run_one 的 row 字典中加入 `中证超额/中证跟踪/中证信息比` 三列。
