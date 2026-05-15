---
name: cn-stock-data
title: Chinese Stock Market Data (A-Share)
description: Download, filter, and manage A-share stock K-line data from Chinese data sources (baostock, akshare)
trigger: user asks for A-share stock data, K-line, OHLC data, Chinese stock market historical prices
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
lg = bs.login()   # global connection
# ... queries ...
bs.logout()
```

Each `bs.login()` is a global singleton — call once per process.

### 3. Get All A-Share Stocks
```python
rs = bs.query_all_stock('2025-12-31')  # pass a known-good date
stocks = []
while rs.next():
    row = rs.get_row_data()
    code, status, name = row
    if status == '1':
        stocks.append((code, name))
```

### 4. Filter A-Share Stocks (Exclude Indices)
Indices (sh.000xxx, sz.399xxx) are mixed in. Filter by code prefix:

| Prefix | Type |
|--------|------|
| sh.60xxxx | Shanghai主板 |
| sh.68xxxx | 科创板 |
| sz.00xxxx, sz.01xxxx | Shenzhen主板 |
| sz.30xxxx | 创业板 |
| sz.20xxxx | 中小企业板 |

```python
prefix = code.split('.')[1][:2]
is_stock = False
if code.startswith('sh.') and prefix in ('60', '68'):
    is_stock = True
elif code.startswith('sz.') and prefix in ('00', '30', '20', '01'):
    is_stock = True
```

### 5. Download K-Line Data
```python
rs = bs.query_history_k_data_plus(
    'sh.600000',
    'date,code,open,high,low,close,preclose,volume,amount,turn',
    start_date='2023-01-01',
    end_date='2025-12-31',
    frequency='d',          # d=日K, w=周K, m=月K
    adjustflag='3'          # 1=不复权, 2=前复权, 3=后复权
)
rows = []
while rs.next():
    rows.append(rs.get_row_data())
```

**Field reference in templates/a-share-kline-download.py**

## Batch Download with Resume

Use a resume-capable pattern for 5000+ stocks:
1. Maintain `.download_progress.txt` with completed stock codes
2. On restart, skip already-downloaded stocks via `load_progress()`
3. Append to CSV (don't overwrite)
4. Log errors to `.error_log.txt` without aborting
5. Report progress every 50 stocks

### Run in Background
Use `background=true` + `notify_on_complete=true` for long runs.

## Pitfalls

- **baostock data lags**: Data only up to last full calendar year (~Dec 31). Not real-time.
- **query_all_stock date**: Must be a valid trading day. Future dates return 0 results.
- **Global login**: Don't call `bs.login()` from concurrent threads.
- **Output buffering**: Background Python scripts buffer stdout. Check CSV/progress file for actual status.
- **CSV size**: 5171 stocks x ~642 days ≈ 3.3M rows, ~300MB.
- **No batch API**: Each stock = one API call. ~1.5 hrs for full market.

## akshare 全市场下载（多进程版）

akshare 通过 East Money 接口获取数据，支持多进程全市场下载。

### 两种日K API

| API | symbol 格式 | 日期格式 | 说明 |
|-----|------------|---------|------|
| `ak.stock_zh_a_daily(symbol, start_date, end_date, adjust)` | `sh600000` / `sz000001` | `YYYYMMDD` | 可获取近 3 年数据 |
| `ak.stock_zh_a_hist(symbol, period, start_date, end_date, adjust)` | `600000`（纯代码） | `YYYYMMDD` | 更轻量 |

两者 adjust 参数：`"qfq"`=前复权, `"hfq"`=后复权, 留空=不复权。

### 多进程方案

> 详细实现见 `references/akshare-multiprocess-download.md`

**为什么要多进程**：akshare 内部用 `py_mini_racer` 解析 East Money 的 JS 接口，多线程/单进程多 worker 会导致崩溃。解决方案是 **spawn 模式的多进程**，每个 worker 独立加载 akshare。

**核心模式**：
1. `ak.stock_info_a_code_name()` 获取全市场股票列表
2. 按代码前缀过滤：`6`→`sh`，`0`/`3`→`sz`
3. `mp.get_context("spawn")` 创建进程池
4. `pool.imap_unordered()` 按完成顺序取结果，每 N 只 flush 一次 CSV
5. 进度文件支持断点续传

```python
code_to_symbol = {
    "6": "sh",     # 上海主板、科创板
    "0": "sz",     # 深圳主板
    "3": "sz",     # 创业板
}
symbol = f"{prefix}{code}"
```

### 运行建议

- 用 `background=true` + `notify_on_complete=true` 后台跑，约 9 分钟完成 5200 只
- 后台输出可能被缓冲，检查 `_log.txt` / `_progress.txt` 确认状态
- 数据输出到 `~/Desktop/a_stock_trade/data/a_stock_kline_3y.csv`（~400MB）

⚠️ akshare connects to East Money — may fail behind proxies.

## Next Step: Backtesting

After downloading data, see the `a-stock-backtesting` skill for vectorized
strategy evaluation patterns (signal generation, portfolio simulation, cost
accounting, visualization).

## Path Resolution on Windows (MSYS/Git Bash)

When using `os.path.expanduser("~/Desktop/...")` inside MSYS git-bash, `~`
resolves to `C:\Users\<username>` correctly, but the resulting path may have
mixed slashes (`C:\Users\Mayn/Desktop/a_stock_data/...`). This can cause
subtle failures in downstream scripts.

**Best practice**: use `pathlib` and resolve explicitly:
```python
from pathlib import Path
DATA_DIR = Path.home() / "Desktop" / "a_stock_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
```

Or pass the full Windows path as a config variable rather than relying on
`os.path.expanduser()` inside the script.
