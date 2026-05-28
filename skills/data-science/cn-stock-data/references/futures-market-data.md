# Chinese Futures Market Data

Download Chinese futures K-line data (daily and minute) via AKShare → Sina Finance. **Free, no account needed.**

## Daily K-line (Continuous Contracts)

```python
import akshare as ak
df = ak.futures_zh_daily_sina(symbol="CU0")  # CU = copper continuous
# Returns: date, open, high, low, close, volume, hold, settle
```

Symbol = product code + "0": `CU0`, `RB0`, `IF0`, `SC0`, etc.

### Exchanges & Products (76 total)

| Exchange | Products |
|----------|----------|
| SHFE (上期所) | CU, AL, ZN, PB, NI, SN, AU, AG, RB, HC, SS, BU, RU, FU, SP, WR (17) |
| DCE (大商所) | C, CS, A, B, M, Y, P, FB, BB, JD, L, PP, V, EG, J, JM, I, PG, EB, RR, LH, LG, BZ (23) |
| CZCE (郑商所) | TA, OI, RS, RM, WH, JR, SR, CF, ZC, FG, MA, AP, CJ, UR, SA, SF, SM, CY, PF, PK, LR, RI, PM (23) |
| CFFEX (中金所) | IF, IC, IH, IM, T, TF, TS, TL (8) |
| INE (上期能源) | SC, LU, BC, NR (4) |
| GFEX (广期所) | SI, LC (2) |

Data from listing date to present. ~210,000 K-lines total. Some products retired (ZC0, JR0, WH0, LR0, RI0, PM0 — data ends ~2022-2023).

## Minute Data (5-min bars)

```python
df = ak.futures_zh_minute_sina(symbol="RB2005", period="5")
```

Symbol format: `PRODUCT_CODE` + `YY` + `MM` (e.g. `RB2005`, `CU2501`, `IF2206`).
~1023 bars per contract, covers ~last 2 months before expiry. Includes night session.

### Contract Month Rules

- SHFE metals: all 12 months
- DCE grains: 1,3,5,7,9,11 (odd months)
- DCE industrial: all 12 months
- CZCE agricultural: mostly 1,3,5,7,9,11
- CFFEX index: all 12 months; T-bond: 3,6,9,12
- INE/GFEX: all 12 months

### Multi-Process Batch Download

For full dataset (~76 products × ~120 contracts = ~9,000+ contracts, ~11.8M rows):

```bash
python scripts/download_futures_minute_mp.py
```

Same pattern as `a_stock_trade/core/download_data.py`:
1. `multiprocessing.get_context("spawn").Pool(workers=6).imap_unordered()` — akshare's JS engine crashes with `fork`
2. Buffer + periodic CSV flush (every 20 contracts)
3. Progress file for resume
4. Error isolation per contract

Output: single `all_futures_5min.csv` (~981MB) with columns: `合约代码, 品种代码, 品种名称, 交易所, datetime, open, high, low, close, volume, hold`.

## Futures-Specific Pitfalls

- **Empty DataFrame from non-existent contracts**: `futures_zh_minute_sina()` returns 0-row DataFrame. Check `len(df) == 0` AND catch "Length mismatch" on `df.insert()`.
- **Large CSV encoding**: 3M+ row CSVs → write with `encoding="utf-8-sig"`, read with `encoding="utf-8"`.
- **Multi-process CSV corruption**: `imap_unordered` + buffer-flush to single CSV can produce ~10 bad lines per 3.15M rows (concatenated rows, truncated fields, encoding glitches). Use `scripts/fix_csv.py` to detect + repair.
- **NR0 ambiguity**: Appears in both SHFE and INE contract info — deduplicate by symbol.
- **Sina rate limiting**: ~1.5s interval for single worker; ~0.2s per worker with 4-6 concurrent workers.
- **Cross-contamination**: Keep futures data projects separate from stock projects. Don't mix files across domains.
- **~2 month coverage per contract**: Quarterly-month products have data gaps between contracts.

## Output Structure (Daily)

```
期货K线数据/
├── 上期所/ (17 products)
├── 大商所/ (23)
├── 郑商所/ (23)
├── 中金所/ (8)
├── 上期能源/ (4)
├── 广期所/ (2)
└── 下载汇总.json
```
