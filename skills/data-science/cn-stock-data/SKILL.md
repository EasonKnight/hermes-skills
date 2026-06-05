---
name: cn-stock-data
title: Chinese Financial Market Data (A-Share + Futures)
description: "Download, filter, and manage Chinese financial market data — A-share stock K-line AND fundamentals, plus Chinese futures K-line (daily/minute). Covers baostock, akshare, and multi-process batch download patterns for both stocks and futures. Also covers futures settlement reconciliation: PDF parsing, cross-checking program-generated reports against exchange statements, and balance-equation validation."
trigger: user asks for A-share stock data, K-line, OHLC data, financial data, fundamentals, 基本面, 财务数据, Chinese futures data, 期货数据, CTA data, commodity futures, index futures, Chinese stock market historical prices, multi-process Chinese financial data download, futures settlement reconciliation, 结算单 cross-check, or PDF settlement parsing
tags: [finance, stocks, a-share, futures, k-line, baostock, data-acquisition, cta, multi-process, settlement, reconciliation, PDF-parsing]
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
- `references/windows-scheduled-tasks.md` — Windows 定时任务 (schtasks) 约定

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

---

## Futures Market Data

Chinese futures K-line data (daily continuous contracts + 5-min intraday) is also available
via the same akshare → Sina Finance free source. Covers all 76 products across 6 exchanges
(SHFE, DCE, CZCE, CFFEX, INE, GFEX).

For the full futures symbol table, contract month rules, multi-process minute-data batch
download script, and futures-specific pitfalls, see `references/futures-market-data.md`.

**Quick example — daily continuous contract:**
```python
import akshare as ak
df = ak.futures_zh_daily_sina(symbol="RB0")  # RB0 = rebar continuous
df = ak.futures_zh_minute_sina(symbol="RB2005", period="5")  # 5-min bars
```

The same multi-process batch download pattern (`spawn` context, `Pool.imap_unordered`,
progress files, resume support) used for stocks also applies to futures minute data.

**Critical rule**: Keep futures data projects **separate** from stock projects
(`a_stock_trade`). Do not mix or reference files across domains.

---

## Futures Settlement Reconciliation

When you've downloaded futures data and need to cross-check program-generated monthly
settlement reports against official exchange PDFs, see the full reconciliation
workflow in `references/futures-settlement-reconciliation.md`. It covers:

- PDF parsing (exchange settlement format with two row types: individual trades and aggregated close summaries)
- XLSX parsing with dynamic section-header detection
- Balance equation validation: `期末结存 = 期初结存 + 出入金 + 平仓盈亏 - 手续费 + 权利金收入`
- Option P&L script pitfalls (same-month exercise detection, variable scoping, key name typos)

**Quick verification:** Run `verify_monthly_report.py` in the monthly_report project
directory — it compares fund fields, daily fees/P&L, aggregated trade groups, and
validates the balance equation.

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

## NPZ 缓存

全量下载 (`download_data.py`) 和增量更新 (`update_data.py`) 完成后**均自动构建**
`data/a_stock_kline_3y.npz`，无需手动操作。构建函数逻辑一致（`_build_npz` /
`_build_cache`）：

1. 读取 CSV → pivot 透视 → 过滤 A 股前缀 → ffill 填充停牌 → `np.savez_compressed`
2. 字段：`close, open, volume, high, low, codes, dates, names, is_st, exchange`
3. 回测引擎 `DataLoader` 优先读 NPZ 缓存（0.1s vs CSV 的 6s）

如果 CSV 已存在但 NPZ 缺失，再次运行 `download_data.py` 会在"全部完成"路径中
自动检测并构建。

### NPZ → CSV 回退原则（核心设计原则）

**不要让 NPZ 格式拖累整个工程。** 每个需要加载 K 线数据的地方都必须：
NPZ 优先（快）→ CSV 兜底（慢但总能工作）。

| 加载点 | 文件 | 函数 | 回退链 |
|--------|------|------|--------|
| 回测数据 | `backtest_utils.py` | `DataLoader.load()` | NPZ → CSV → 自动重建 NPZ |
| 股票映射 | `data_loader.py` | `load_stock_name_map()` | NPZ → JSON缓存 → CSV |
| 股票映射 | `app_utils.py` | `load_stock_name_map()` | NPZ → JSON缓存 → CSV |
| 状态栏显示 | `app.pyw` | `_update_data_status()` | NPZ → CSV |
| 基本面展开 | `fetch_fundamentals.py` | `expand_to_daily()` | K线NPZ → K线CSV |
| 基本面加载 | `data_loader.py` | `load_fundamentals()` | NPZ → None（调用方处理） |

`_build_stock_map_from_csv()` 是 NPZ 缺失时的兜底函数，从 CSV 的 `股票代码/股票名称/close`
列构建 `{code_int: [name, latest_close]}` 映射。两个文件（`data_loader.py` /
`app_utils.py`）均已实现。

### 进度文件陷阱 [已自动修复]

`_update_progress.txt` 记录每只股票的上次更新状态用于断点续传。**代码已在所有退出点
自动调用 `_clean_progress()` 清理**，确保每次增量更新从头开始。如果仍出现
`total_todo` 异常少（< 100 只），手动删除进度文件后重跑：

```bash
rm data/_update_progress.txt   # 备用手动清理
python core/update_data.py
```

同时，`_clean_cache()` 函数已于 2026-06-01 补上（之前被调用但未定义，会导致
早期退出路径崩溃）。`_update_errors.txt` 每次运行前自动清理。

**全量下载 (`download_data.py`) 同样受影响**：其 `_progress.txt` 和 `_errors.txt`
也需每次运行后清理。已于 2026-06-01 修复：CSV 写入先于进度记录（safe flush），
完成后自动调用 `_clean_progress_and_errors()`。

**跨文件审计清单**：修改任何数据脚本时，必须检查 `update_data.py`、`download_data.py`、
`update_fundamentals.py` 三文件是否共享相同模式：
safe flush、文件清理、编码一致性（utf-8-sig）、log_fh 异常安全（try/finally）。
详见 `a-stock-trade` skill 的 `references/data-pipeline.md`。

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

### Pitfall: 项目文件与 stdlib 同名冲突（platform.py → runner.py）

**根因**：`core/platform.py` 与 stdlib `platform` 同名。当 akshare → pandas 执行
`import platform` 时，Python 发现 `core/` 在 `sys.path` 中 → 导入项目文件而非
标准库 → `AttributeError: module 'platform' has no attribute 'python_implementation'`。

**永久修复**：重命名 `core/platform.py` → `core/runner.py`，更新所有引用：

| 文件 | 修改 |
|------|------|
| `core/platform.py` | → `core/runner.py`，docstring 中 `core.platform` → `core.runner` |
| `app.pyw` | `python -m core.platform run` → `python -m core.runner run` |
| `batch_run.py` / `run_all.py` | 注释中的 `platform.py` → `runner.py` |
| `core/download_data.py` | 移除 `sys.path.pop(0)` workaround（不再需要） |
| `core/update_data.py` | 同上 |
| `core/fetch_fundamentals.py` | 同上 |
| `core/update_fundamentals.py` | 同上 |

**不推荐**旧方案（`sys.path.pop(0)` workaround）：治标不治本，每个新脚本都会踩坑。

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
