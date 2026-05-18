# 回测引擎修改记录

## 2026-05-18: 印花税 + 基准修复

### 印花税分买卖计算

**改前**：统一 `cost_rate = commission + slippage = 0.0013` 不分买卖。

**改后**：`STAMP_DUTY = 0.0005`（万分之五，仅卖出），分设两个成本率：
- `buy_cost_rate = commission + slippage = 0.0013`
- `sell_cost_rate = commission + slippage + stamp_duty = 0.0018`

引擎中有 4 个成本计算点需要修改：
1. 初始建仓（纯买入）→ `buy_cost_rate`
2. 清仓（纯卖出）→ `sell_cost_rate`
3. 重新部署（纯买入）→ `buy_cost_rate`
4. 正常再平衡（买卖混合）→ 拆分为 `buy_sum × buy_rate + sell_sum × sell_rate`

### 等权基准前视偏差修复

**改前**：
```python
if first[t]:
    portfolio = valid[:, t]   # 立即换新股票
# 然后用新股票算当天的收益（前视偏差！）
held = portfolio
rets = close[held, t] / close[held, t-1] - 1
```

**改后**（先算收益再更新组合）：
```python
if t > 0:
    held = portfolio  # 用旧组合算当天收益
    rets = close[held, t] / close[held, t-1] - 1
if first[t]:
    portfolio = valid[:, t]  # 调仓日收盘才更新
```

### 等权基准幸存者偏差修复

**改前**：`load_csi1000_codes()` 用当前成分股列表（775只）回溯整个10年。

**改后**：使用 `index_stock_cons(symbol="000852")` 返回的 `纳入日期` 字段，每只股票只在进入指数后才计入基准：
```python
def get_csi1000_at_date(df, date):
    return set(df[df["纳入日期"] <= pd.Timestamp(date)]["品种代码"].astype(str).str.zfill(6).tolist())
```

**效果**：基准从 +224% 降到 +145%（10年），年化从 12.5% 降到 9.3%。

### 等权基准增加交易成本

每周调仓时按换手率扣除成本：
```python
turnover = (outgoing + incoming) / (old + new)
avg_cost = commission + stamp_duty * 0.5
daily_ret[t] -= turnover * avg_cost
```

实际影响很小（CSI1000 周频成分股变化小，换手~5%/周，成本~0.05%/周）。
