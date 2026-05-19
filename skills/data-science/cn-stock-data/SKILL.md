---
name: cn-stock-data
title: Chinese Stock Market Data (A-Share)
description: "Download, filter, and manage A-share stock K-line data AND financial/fundamental data from Chinese data sources (baostock, akshare)"
trigger: user asks for A-share stock data, K-line, OHLC data, financial data, fundamentals, 基本面, 财务数据, Chinese stock market historical prices
tags: [finance, stocks, a-share, k-line, baostock, data-acquisition]
---

# Chinese Stock Market Data (A-Share)

## Data Source Selection

| Source | Auth | Coverage | Speed | Notes |
|--------|------|----------|-------|-------|
| **baostock** | Free, no token | ~2025-12-31 (lags 4-5 months) | Fast | Preferred — stable, no proxy issues |
| **akshare** | Free, no token | Real-time | Moderate | Fallback — East Money API may fail behind proxies |

On Chinese networks or behind proxies, **favor baostock**. akshare's East Money backend often hits proxy errors.

## baostock Workflow

### 1. Install
```bash
pip install baostock
```

### 2. Login/Logout Pattern
```python
import baostock as bs
lg = bs.login()
bs.logout()
```

### 3. Get All A-Share Stocks
```python
rs = bs.query_all_stock('2025-12-31')
stocks = []
while rs.next():
    row = rs.get_row_data()
    code, status, name = row
    if status == '1':
        stocks.append((code, name))
```

### 4. Filter A-Share Stocks (Exclude Indices)
| Prefix | Type |
|--------|------|
| sh.60xxxx | Shanghai主板 |
| sh.68xxxx | 科创板 |
| sz.00xxxx, sz.01xxxx | Shenzhen主板 |
| sz.30xxxx | 创业板 |
| sz.20xxxx | 中小企业板 |

### 5. Download K-Line Data
```python
rs = bs.query_history_k_data_plus(
    'sh.600000',
    'date,code,open,high,low,close,preclose,volume,amount,turn',
    start_date='2023-01-01', end_date='2025-12-31',
    frequency='d', adjustflag='3')
```

## Batch Download with Resume

1. Maintain `.download_progress.txt` with completed stock codes
2. On restart, skip already-downloaded stocks
3. Append to CSV (don't overwrite)
4. Log errors without aborting

## akshare 全市场下载（多进程版）

### 两种日K API

| API | symbol 格式 | 日期格式 |
|-----|------------|---------|
| `ak.stock_zh_a_daily(symbol, start_date, end_date, adjust)` | `sh600000` / `sz000001` | `YYYYMMDD` |
| `ak.stock_zh_a_hist(symbol, period, start_date, end_date, adjust)` | `600000` | `YYYYMMDD` |

adjust: `"qfq"`=前复权, `"hfq"`=后复权.

**为什么要多进程**：akshare 内部用 `py_mini_racer` 解析 East Money 的 JS 接口，多线程崩溃 → spawn 模式多进程。

## References

- `references/akshare-multiprocess-download.md` — 多进程全市场下载方案
- `references/incremental-update-data.md` — 增量更新方案
- `references/limit-price-data-sources.md` — 涨跌停价格数据源
- `references/fundamental-data-download.md` — 基本面数据下载细节
- `references/fundamentals-data-pipeline.md` — 基本面数据流水线完整文档

---

## 基本面/财务数据下载

一键运行（下载季度报表 + 展开为日频 NPZ）：

```bash
cd ~/Desktop/a_stock_trade
python core/fetch_fundamentals.py
```

输出 `data/a_stock_fundamentals.npz`（13MB，轴序 `(n_stocks, n_dates)` 与 K 线一致）。

### 核心 API

| API | 说明 | 格式 |
|-----|------|------|
| `ak.stock_yjbb_em(date="YYYYMMDD")` | 指定季度末日期，返回全市场业绩报表 | `"20251231"` |

重命名字段：`code`, `name`, `eps`, `revenue`, `revenue_yoy`, `revenue_qoq`, `net_profit`, `net_profit_yoy`, `net_profit_qoq`, `bps`, `roe`, `cf_ps`, `gross_margin`, `industry`, `announce_date`。

### 与 K-line 下载器对比

| 方面 | K-line | 基本面 |
|------|--------|--------|
| API | `stock_zh_a_daily(symbol, ...)` | `stock_yjbb_em(date, ...)` |
| 并行粒度 | 按股票（~5200 task） | 按季度（~42 task） |
| 输出 NPZ | `a_stock_kline_3y.npz` | `a_stock_fundamentals.npz` |
| 轴序 | `(n_stocks, n_dates)` | `(n_stocks, n_dates)` ✅ |
| 数据组织 | 每股票多日时序 | 季度横截面→前向填充日频 |

### 策略中加载

```python
from core.data_loader import DataLoader, load_fundamentals
d = DataLoader().load()
fund = load_fundamentals(d.codes)
roe_z = zscore_rank(fund["roe"][:, t], v)  # [:, t] 取 t 日截面
```

### 可用基本面因子（alpha_utils.py）

| 函数 | 逻辑 |
|------|------|
| `alpha_fund_roe(t, fund, close_at_t)` | 高 ROE |
| `alpha_fund_eps(t, fund, close_at_t)` | 高 EPS |
| `alpha_fund_eps_yoy(t, fund, close_at_t)` | 净利润同比增长 |
| `alpha_fund_revenue_yoy(t, fund, close_at_t)` | 营收同比增长 |
| `alpha_fund_profit_growth(t, fund, close_at_t)` | 利润+营收双增 |
| `alpha_fund_bp(t, fund, close_at_t)` | B/P = bps/price（价值） |
| `alpha_fund_gross_margin(t, fund, close_at_t)` | 高毛利率 |
| `alpha_fund_cf_quality(t, fund, close_at_t)` | 经营现金流/EPS |
| `alpha_fund_quality(t, fund, close_at_t)` | (ROE+毛利+现金流)/3 |
| `alpha_fund_eps_growth_price(t, fund, close)` | EPS增长+动量复合 |

### 性能参考

| 项目 | 数值 |
|------|------|
| 季度数 | 43 个（2015Q4 ~ 2026Q2，多取一个季度给前向填充缓冲） |
| 原始季度数据行数 | ~330,000 |
| NPZ 非空率 | ~93%（修复 disclose date bug 后） |
| 下载耗时 | ~50 秒（4 进程） |
| 展开耗时 | ~10 秒 |
| NPZ 大小 | 10MB（float32 + 重复值高压缩比 63x） |
| CSV 抽样 | 29MB（每季度末一天 x 5203 只，42个交易日） |

---

## Next Step: Backtesting

After downloading data, see the `a-stock-backtesting` skill for vectorized
strategy evaluation patterns.

## 增量数据更新（K-line）

`core/update_data.py` 是 `download_data.py` 的增量版：

```bash
cd ~/Desktop/a_stock_trade
python core/update_data.py
python core/update_data.py --force 20260501  # 强制从指定日期重下
```

### NPZ 缓存重建

更新完成后自动从 CSV 重建 NPZ 缓存（`_build_cache()`），而非简单地删除旧缓存。NPZ 结构同回测引擎的 `DataLoader._load_data()`，包含：

```
close, open, volume, high, low   → (n_stocks, n_days) float64
codes                              → (n_stocks,)
dates                              → (n_days,) datetime64[ns]
names                              → (n_stocks,)
is_st                              → (n_stocks,) bool
exchange                           → (n_stocks,) str ("main"/"chinet"/"star"/"other")
```

构建耗时约 35-40 秒（~5241 只 A 股 × ~2427 个交易日，1.5GB CSV），完成后回测引擎直接读缓存无需再加载 CSV。

### Pitfall: akshare 返回非 A 股代码（B 股/债券/基金）

`ak.stock_info_a_code_name()` 返回的股票列表包含深市 B 股（`200xxx`）、沪市 B 股（`900xxx`）、各类债券（`1xx`/`5xx`/`7xx` 短代码）和基金。其中 B 股 200xx-299xx 区间约 1500 个代码会混入 CSV，导致 NPZ 中非 A 股占比 ~22%。

**修复**：`get_all_stocks()` 和 `_build_cache()` 两处都须用 A 股前缀白名单过滤：

```python
a_prefixes = {"000","001","002","003","300","301","302","303",
              "600","601","603","605","688"}
if code[:3] not in a_prefixes:
    continue
```

A 股有效前缀对应：深市主板（000-003）、创业板（300-303）、沪市主板（600-605）、科创板（688）。

**清洗存量数据**：如果 CSV 已混入非 A 股数据，须用 pandas 按前缀过滤后重写 CSV 并重建 NPZ：

```python
df = pd.read_csv(csv, dtype={'股票代码': str})
mask = df['股票代码'].str[:3].isin(a_prefixes)
df[mask].to_csv(csv, index=False, encoding='utf-8-sig')
```

同时清理 `_update_progress.txt`、`_update_errors.txt`、`_update_log.txt` 等进度缓存，避免旧代码残留干扰后续增量更新。

### 定时任务退出码

`update_data.bat` 末尾应加 `exit /b 0` 兜底，避免 Windows 任务计划程序误报退出码 2（即使所有 Python 脚本成功）。

## Path Resolution & Pitfalls on Windows

### Pitfall: core/platform.py 与 stdlib platform 冲突

`core/platform.py` 内 `import pandas as pd`，pandas 依赖 `import platform`（stdlib）。
运行 `python core/<script>.py` 时 `core/` 进入 `sys.path[0]` → 循环引用崩溃。

**修复**：
```python
import os, sys
if sys.path and sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path.pop(0)
```

### Pitfall: NPZ axis convention 混淆

基本面 NPZ 必须与 K 线 NPZ 同轴序 `(n_stocks, n_dates)`。

**正确**：`fund["roe"][:, t]` 取 t 日截面
**错误**：`fund["roe"][t, :]` 取第 t 只股票的所有日期

### Pitfall: `最新公告日期` 不可信（最关键）

`ak.stock_yjbb_em()` 的 `最新公告日期` 是**最后修订日期**，不是首次披露。直接用做前向填充会导致 2016-2017 年覆盖率降到 80% 以下。

**方案**：用季度末 + 法定披露时滞估算生效日（年报120天，中报60天，季报45天）。详见 `references/fundamental-data-download.md` 的「关键坑」章节。

### Pitfall: fetch_fundamentals.py 清理顺序

临时 CSV 必须 expand 完成后才删除：
```python
temp = download_all_quarters()
expand_to_daily(temp)   # ✓ 先用
os.remove(temp)         # ✓ 后删
```

### Pitfall: `最新公告日期` 不可信（最关键）

`ak.stock_yjbb_em()` 的 `最新公告日期` 是**最后修订日期**，不是财务报告的实际首次披露日。例如平安银行2015年报API显示公告日2017-03-17，实际在2016年就已披露。

**修复方案**：用季度末 + 法定披露时滞估算生效日期，不用 announce_date：

| 报表 | 时滞 | 估算生效日 |
|------|------|-----------|
| 一季报/三季报 (Q1/Q3) | 45天 | 季度末+45天 |
| 中报/半年报 (Q2) | 60天 | 季度末+60天 |
| 年报 (Q4) | 120天 | 季度末+120天 |

**修复效果**：2016年覆盖率 1% → **76%**，平安银行首个EPS从 t=227 → **t=0**（回测第一天就有数据），总覆盖率 80.0% → **92.9%**。

### Pitfall: fetch_fundamentals.py 清理顺序thlib import Path
DATA_DIR = Path.home() / "Desktop" / "a_stock_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
```
