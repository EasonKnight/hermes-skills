# 10年回测配置与Bug修复 (2026-05-16)

## 10年回测改动
- `BACKTEST_START` 从 `"2021-05-17"` 改为 `"2016-05-17"`（`core/backtest_utils.py` 第25行）
- 数据覆盖：2016-05-17 ~ 2026-05-15，2426个交易日，2930只股票
- CSI1000成分股覆盖：2016年399只 → 2026年775只（成分股列表是静态的当前成分股）
- 10年等权周频基准总收益：+195.18%（约年化11.4%）

## 新股上市日inf Bug（Bug #6）
- **现象**：`close[t-1] = 0`（新股上市前一交易日无数据）→ `close[t]/close[t-1] - 1 = inf` → `np.nanmean` 不处理inf → 基准NAV = inf
- **修复**（`_compute_benchmark`中的基准循环）：
  ```python
  rets = close[held, t] / close[held, t-1] - 1
  rets = np.where(np.isfinite(rets), rets, 0.0)  # 排除inf
  daily_ret[t] = np.nanmean(rets)
  ```

## 成本回收效应修复（Bug #4完整版）
成本在买入日从pv扣除，但次日在无成本再平衡中 pv 重新计算（全市场价），成本消失又回来了。

**修复方案：** 成本嵌入 `has_cash`，永久扣除，不再出现在pv的重新计算中：
```python
# 所有 deploy 分支统一模式
has_cash = available - mv - cost  # 成本永不回来
pv[t] = has_cash + mv             # pv = 现金 + 市值
```

**受影响的分支（3个）：**
1. t=0 首次建仓
2. 重新部署（capital_deployed=False时买入）
3. 再平衡（已有 `has_cash -= cost` 正确处理）

## 超额百分比收益修复（Bug #5）
**问题**：策略用固定基准法（`daily_ret[t] = (pv[t]-pv[t-1])/1亿`），基准用百分比法（`cumprod(1+平均股票收益率)`）。当 pv > 1亿 时，固定基准法放大超额；pv < 1亿 时缩小超额。

**修复**：超额统一用百分比收益计算：
```python
pct_ret[t] = self.pv[t] / self.pv[t-1] - 1
strategy_pct_nav = np.cumprod(1 + pct_ret)
excess_nav = 1 + strategy_pct_nav - benchmark_nav
```

同时修复了超额统计（信息比/跟踪误差）也使用百分比日收益。

## 图表布局（Visualizer 更新）
原3子图：净值+回撤折线图+超额 → 改为：净值+中证1000超额+等权超额
- 子图2移除回撤折线图，改为中证1000超额曲线（橙色`#f97316`）
- 中证1000指数通过 akshare 下载：`ak.stock_zh_index_daily(symbol="sh000852")`
- 下载失败时子图2显示"中证1000数据不可用"

## 等权策略超额不应为正
等权策略(s01/s02)的超额应始终≤0（因为有成本），但实际上因策略每日再平衡而基准每周再平衡，出现微幅正超额。这是真实的差异而非bug，用户选择保留现状。

## S118 策略说明
- POOL必须保持 "csi1000"（用户明确要求不改成"all"）
- CSI1000下S118日均仅12只持股，年化-13.14%，属于策略自身逻辑问题
- 不要乱改pool设置
