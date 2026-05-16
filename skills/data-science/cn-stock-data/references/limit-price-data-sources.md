# 涨跌停价格数据源

## 问题

`ak.stock_zh_a_hist()` 返回的日 K 数据 **没有** `high_limit` / `low_limit`（涨停价/跌停价）字段。仅有：

```
日期, 股票代码, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
```

东方财富原始 K 线 API（push2his）有 15 个字段（f51-f65），多出的 f62-f65 **可能**包含涨停价/跌停价，但 akshare 未暴露。

## 可选方案

| 方案 | 数据类型 | 适合回测？ | 局限 |
|------|---------|-----------|------|
| **akshare `stock_zt_pool_em(date)`** | 当日涨停股池（含涨停价、封板资金等） | ❌ | 仅近期日期有效，非逐股逐日格式 |
| **akshare `stock_zt_pool_previous_em(date)`** | 昨日涨停股池 | ❌ | 同上，历史日期可能不可用 |
| **akshare `stock_em_zt_pool_dtgc(date)`** | 跌停股池 | ❌ | 同上 |
| **TuShare Pro `pro.stk_limit()`** | 逐股逐日 high_limit / low_limit | ✅ | 需注册 + API token |
| **聚宽 JQData `get_preopen_infos()`** | 含 high_limit / low_limit | ✅ | 需聚宽账号 |
| **手动计算（TradingRules）** | 前收盘 × (1 ± 涨跌幅%) | ✅ | 需正确判断板块和 ST 状态 |

## 推荐：手动计算方案

涨跌停价格 = `round(前收盘 × (1 ± 涨跌幅限制), 2)`，规则固定：

| 板块 | 代码前缀 | 涨跌幅限制 |
|------|---------|-----------|
| 主板 | 600/601/603/605/000/001/002 | ±10% |
| 创业板 | 300 | ±20% |
| 科创板 | 688 | ±20% |
| 北交所 | 8 | ±30% |
| ST/*ST 股票 | 名称含 ST/退/PT | ±5%（部分为 ±10%） |

### 历史 ST 状态判断

手动计算的最大不确定性是 ST 状态的历史变化。可以从日 K 数据的 `股票名称` 字段中通过 `str.contains("ST|退|PT")` 推断——如果数据中包含每日的股票名称。

akshare `stock_zh_a_hist()` 返回的字段中有 `股票代码`，但不包含每日的 `股票名称`，所以 ST 状态变化无法从该接口直接获取。

替代方案：
- 使用 akshare `stock_zh_a_st_em()` 获取当前 ST 板股票列表（仅最新）
- 使用 baostock 的历史 K 线数据（包含 `code` 字段，但同样不包含每日名称）
- TuShare Pro 包含 `st_status` 标记

### 涨停/跌停命中判定

```python
limit_up   = round(prev_close * (1 + limit_pct), 2)
limit_down = round(prev_close * (1 - limit_pct), 2)
is_limit_up   = (close[t] == limit_up)   # exact match，不使用容差
is_limit_down = (close[t] == limit_down)
```

**必须用精确 `==` 匹配**。即使是 0.2% 的容差也会把涨了 8-9%（未涨停）的股票误判为涨停，导致组合被错误地禁止买入这些股票，产生集中度失真。
