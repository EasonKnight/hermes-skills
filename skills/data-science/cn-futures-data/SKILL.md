---
name: cn-futures-data
category: data-science
tags: [futures, china, cta, kline, data-download, akshare, sina-finance]
triggers:
  - user asks to download Chinese futures K-line data
  - user wants futures data for CTA/quant analysis
  - user needs continuous contract data for any Chinese futures product
  - task involves futures, CTA, commodity futures, index futures
  - user mentions getting data for "all futures contracts"
  - user asks for futures minute data, intraday data
  - user wants to download all historical futures minute data (batch/multi-process)
  - user needs multi-process download for Chinese financial data
description: "Download, manage, and update Chinese futures K-line data using free sources (AKShare -> Sina Finance). Covers all 6 exchanges: SHFE, DCE, CZCE, CFFEX, INE, GFEX."
---

# Chinese Futures Data (cn-futures-data)

Download Chinese futures continuous contract daily K-line data via AKShare's Sina Finance source. **Free, no account needed.**

## Quick Start

```python
import akshare as ak

# Single product: CU0 = copper continuous, RB0 = rebar continuous, CF0 = cotton continuous
df = ak.futures_zh_daily_sina(symbol="CU0")

# Returns DataFrame with columns: date, open, high, low, close, volume, hold, settle
```

## Symbol Convention

Sina continuous contract symbols = **product code + "0"** suffix:

| Exchange | Product Codes |
|----------|---------------|
| SHFE (上期所) | CU, AL, ZN, PB, NI, SN, AU, AG, RB, HC, SS, BU, RU, FU, SP, WR |
| DCE (大商所) | C, CS, A, B, M, Y, P, FB, BB, JD, L, PP, V, EG, J, JM, I, PG, EB, RR, LH, LG, BZ |
| CZCE (郑商所) | TA, OI, RS, RM, WH, JR, SR, CF, ZC, FG, MA, AP, CJ, UR, SA, SF, SM, CY, PF, PK, LR, RI, PM |
| CFFEX (中金所) | IF, IC, IH, IM, T, TF, TS, TL |
| INE (上期能源) | SC, LU, BC, NR |
| GFEX (广期所) | SI, LC |

Append "0": `CU0`, `RB0`, `IF0`, `SC0` etc.

Full symbol table with Chinese names in `references/futures_symbol_db.md`.

## Output Structure

```
期货K线数据/
├── 上期所/    (17 products)
│   └── 品种名/
│       └── 品种名_主连日线.csv
├── 大商所/    (23 products)
├── 郑商所/    (23 products)
├── 中金所/    (8 products)
├── 上期能源/  (3 products)
├── 广期所/    (2 products)
└── 下载汇总.json
```

CSV columns: `日期,开盘,最高,最低,收盘,成交量,持仓量`

## Data Coverage

- **Source**: Sina Finance via AKShare (`ak.futures_zh_daily_sina`)
- **Period**: From listing date to present (some products back to 2005)
- **Typical volume**: ~5000 bars for old products
- **Total**: ~210,000 K-lines across all 76 products

## Data Coverage (Verified)

| Metric | Value |
|--------|-------|
| Products with minute data | 76/76 (all exchanges) |
| Contracts with minute data | 12,648 |
| Total data rows | 11.8M (5-min bars) |
| File size | 981 MB (all_futures_5min.csv) |
| Earliest data | ~2019 |
| Coverage per contract | ~last 2 months before expiry (1023 bars) |
| Download speed | ~18 contracts/sec with 6 workers |
| Bad rows (validation) | ~10 per 3.15M rows (0.0003%) from concurrent write |

## Workflow

1. Check `pip list | grep akshare` — install if missing: `pip install akshare`
2. Create output directory on Desktop (isolated from stock projects)
3. Run `python download_futures_kline.py` — script in `scripts/`
4. Summary saved to `下载汇总.json`

## Minute Data (Multi-Process Batch Download)

### API

```python
# Single contract 5-minute data (period: "1"/"5"/"15"/"30"/"60")
df = ak.futures_zh_minute_sina(symbol="RB2005", period="5")
```

**Returns** ~1023 bars per contract, covering ~last 2 months before expiry.
Includes night session data. Columns: `datetime, open, high, low, close, volume, hold`

### Symbol Convention (Specific Contracts)

Format: `PRODUCT_CODE` + `YY` + `MM` (uppercase, e.g. `RB2005`, `CU2501`, `IF2206`)

### Contract Month Rules

Each product only trades certain months. See `references/futures_minute_api.md` for
the full per-product month table. Key patterns:
- **SHFE metals**: all 12 months
- **DCE grains**: 1,3,5,7,9,11 (odd months)
- **DCE industrial**: all 12 months
- **CZCE agricultural**: mostly 1,3,5,7,9,11
- **CFFEX index**: all 12 months; **T-bond**: 3,6,9,12
- **CFFEX T-bond**: 3,6,9,12
- **INE/GFEX**: all 12 months

### Multi-Process Download Pattern

For downloading all 76 products (~9000+ contracts), use the multi-process script:

```bash
python scripts/download_futures_minute_mp.py
```

This follows the **same pattern as `a_stock_trade/core/download_data.py`**:

1. **`spawn` multiprocessing context** (not fork) — each worker loads akshare independently
2. **`Pool.imap_unordered()`** — results processed as they complete
3. **Buffer + periodic CSV flush** (every 20 contracts)
4. **Progress file** (`_progress_*.txt`) — supports resume if interrupted
5. **Error isolation** — contract failures don't abort the batch

#### Output

Single CSV: `all_futures_5min.csv` (~300MB+ for full dataset)

Columns: `合约代码, 品种代码, 品种名称, 交易所, datetime, open, high, low, close, volume, hold`

#### Progress Tracking

| File | Purpose |
|------|---------|
| `_progress_5min.txt` | Each line: `contract,product_code,name,status,row_count` |
| `_errors_5min.txt` | Failed contracts with error messages |
| `_log_5min.txt` | Timestamped log for long runs |

### Resume Pattern

```python
def load_done_set():
    if not os.path.exists(PROGRESS_FILE): return set()
    done = set()
    with open(PROGRESS_FILE) as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 1: done.add(parts[0])
    return done
```

On restart, contracts in the done set are skipped. Re-run the same command.

## Multi-Process Pattern (Generic, for Any Chinese Data)

When the user wants to batch-download Chinese financial data (stocks, futures, options),
prefer this proven pattern over single-threaded approaches:

```
multiprocessing.get_context("spawn").Pool(workers=6).imap_unordered()
```

Key rules:
- **Always use `spawn` context** — akshare's JS engine crashes with `fork`
- **Each worker imports akshare independently** — avoids thread-safety issues
- **Progress file for resume** — essential for 5000+ item batches
- **Buffer + periodic CSV flush** — avoid memory blowout and partial data loss
- **Single output CSV** with identifier columns (品种代码, 品种名称, 交易所)
- **Export concurrency as config var** (`WORKERS = 6`) so user can adjust

## Pitfalls

- **Cross-contamination**: Keep futures data projects **separate** from stock projects (`tq_real_trade`, `a_stock_trade`). Do not mix or reference files across domains without explicit permission.
- **tqsdk not preferred**: Use AKShare/Sina (free, no account) over tqsdk for one-off data downloads. tqsdk requires a 快期 account.
- **Rate limiting**: Sina API tolerates ~1.5s interval; shorter gaps may trigger HTTP 503.
- **Some products retired**: ZC0, JR0, WH0, LR0, RI0, PM0 have data ending ~2022-2023.
- **NR0 ambiguity**: NR0 appears in both SHFE and INE contract info — deduplicate by symbol not exchange.
- **Sina data covers only main continuous contracts**: Use `ak.get_futures_daily()` for full exchange data with all individual contract months.
- **Data may be a few days behind** real-time on Sina's free feed.

### Minute Data Pitfalls

- **Empty DataFrame crash**: `futures_zh_minute_sina()` may return a 0-row DataFrame
  for non-existent contracts. `df.insert()` on 0 rows raises "Length mismatch". Fix:
  check `len(df) == 0` explicitly, AND catch "Length mismatch" in except to return "empty".
- **Large CSV encoding**: 3M+ row CSVs may hit `UnicodeDecodeError` on read. Write with
  `encoding="utf-8-sig"`, read with `encoding="utf-8"`.
- **Progress file contamination**: Old error entries from pre-fix runs pollute stats.
  Either clear `_errors_*.txt` or ignore error file count.
- **Background output buffering**: Python `-u` flag doesn't guarantee real-time output
  in Hermes' process tool. Check progress/CSV files for actual status.
- **Contract generation vs. reality**: Generated contract codes may not exist
  (e.g. EG1801 before EG listing in Dec 2018). Returns "empty" — expected.
- **Sina rate limits**: With 4-6 concurrent workers, keep per-worker delay at ~0.2s.
  With a single worker, use ~1.5s delay.
- **~2 month coverage per contract**: Each contract only returns the last ~2 months
  of 5-minute data. Products with monthly contracts provide continuous coverage;
  quarterly-month products have gaps.
- **Multi-process CSV corruption**: `Pool.imap_unordered()` + buffer-flush to single CSV
  can produce ~10 corrupted lines per 3.15M rows. Patterns found:
  1. **Two rows concatenated**: Missing `\n` between lines → 2x expected columns.
     Fix: split at known contract-code boundaries (FB, PP, L(, V( etc.) or at
     EXPECTED_COLS intervals.
  2. **Truncated first field**: Line starts with partial bytes from previous row's end.
     Fix: decode with `'utf-8'` + `errors='replace'`, validate via `is_valid_line()`.
  3. **Encoding glitch**: Isolated bytes from interleaved writes.
  Use `scripts/fix_csv.py` to detect + repair + remove bad lines. The fix script
  validates each row: contract code regex, datetime format, 11 columns, numeric prices.

## References & Scripts

| File | Description |
|------|-------------|
| `references/futures_symbol_db.md` | Full symbol table for daily continuous contracts (all 76 products) |
| `references/futures_minute_api.md` | Minute data API, contract month rules, multi-process pattern details |
| `scripts/download_futures_kline.py` | Single-threaded daily K-line downloader |
| `scripts/download_futures_minute_mp.py` | Multi-process minute data downloader (all contracts, resume support) |
| `scripts/fix_csv.py` | Detect + repair + remove bad lines from multi-process CSV output |
