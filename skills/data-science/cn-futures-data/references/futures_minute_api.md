# Futures Minute Data API Reference

## Source: Sina Finance via AKShare

```python
import akshare as ak

# Minute data for a specific contract
df = ak.futures_zh_minute_sina(symbol="RB2005", period="5")
```

### Returns

| Column | Description |
|--------|-------------|
| datetime | Timestamp (Asia/Shanghai, includes night session) |
| open | Open price |
| high | High price |
| low | Low price |
| close | Close price |
| volume | Volume |
| hold | Open interest |

### Period Choices

| Value | Meaning |
|-------|---------|
| "1" | 1 minute |
| "5" | 5 minutes |
| "15" | 15 minutes |
| "30" | 30 minutes |
| "60" | 60 minutes |

## Data Characteristics

| Property | Value |
|----------|-------|
| Bars per contract | ~1023 (fixed limit per Sina) |
| Coverage per contract | ~last 2 months before expiration |
| Earliest available data | ~2019 (limited older coverage) |
| Night session | Included (21:00~23:00, 23:00~01:00 for some) |
| Rate limit | ~0.2-0.5s per request safe with 4-6 concurrent workers |

### Coverage Pattern

Each futures contract on Sina retains approximately the last 2 months of 5-minute data before its expiration. This means:

- **Products with monthly contracts (12/year)**: Continuous coverage year-round via overlapping contracts
- **Products with quarterly contracts (4/year)**: Gaps between contract periods
- **Recently listed products**: Full coverage from listing date
- **Products listed before ~2019**: Coverage starts from the contract's last 2 months, data may be incomplete

## Symbol Convention

Specific contracts follow: `PRODUCT_CODE` + `YY` + `MM` (uppercase)

Example: `RB2005` = rebar, 2020, May; `CU2501` = copper, 2025, January

## Contract Month Rules

Each product only trades specific months. Generate contract codes using this table:

### SHFE (上期所) — 1-12 (all months)
CU, AL, ZN, PB, NI, SN, AU, AG, RB, HC, SS, BU, RU, FU, SP — all 12 months
WR — 1,3,5,7,9,11

### DCE (大商所)
C, CS, A, B, M, Y, P, FB, BB, LH, LG — 1,3,5,7,9,11
JD, L, PP, V, EG, J, JM, I, PG, EB, RR, BZ — all 12 months

### CZCE (郑商所)
OI, RM, WH, JR, SR, CF, LR, RI, PM — 1,3,5,7,9,11
RS — 7,8,9,11
AP — 1,3,4,5,10,11,12
CJ — 1,3,5,7,9,12
PK — 1,3,4,10,11,12
TA, ZC, FG, MA, UR, SA, SF, SM, CY, PF — all 12 months

### CFFEX (中金所)
IF, IC, IH, IM — all 12 months
T, TF, TS, TL — 3,6,9,12

### INE (上期能源) — all 12 months
SC, LU, BC, NR

### GFEX (广期所) — all 12 months
SI, LC

## Multi-Process Download Pattern

For batch downloading all contracts across all products (~9000+ contracts), use the
`scripts/download_futures_minute_mp.py` script.

Key architecture:

```
generate_all_contracts() → list of (contract, product_code, name, exchange)
                         ↓
    multiprocessing.Pool(workers=6).imap_unordered(tasks)
                         ↓
    _download_one(params) → each worker: ak.futures_zh_minute_sina()
                         ↓
    buffer → flush to CSV every 20 contracts
                         ↓
    _progress_5min.txt (resume support)
```

### Output Format

Single CSV: `all_futures_5min.csv`

Columns: `合约代码, 品种代码, 品种名称, 交易所, datetime, open, high, low, close, volume, hold`

### Resume Support

Progress file `_progress_5min.txt` tracks each contract as `ok`/`empty`/`error`.
On restart, already-downloaded contracts are skipped via `load_done_set()`.

### Pitfalls

1. **Empty DataFrame crash**: When Sina returns a 0-row DataFrame, `df.insert()` raises
   "Length mismatch". FIX: check `len(df) == 0` AFTER the initial None check, AND catch
   "Length mismatch" in the except block to return "empty" not "error".

2. **Large CSV encoding**: With 3M+ rows, Pandas `read_csv` may hit UnicodeDecodeError.
   Write with `encoding="utf-8-sig"`, read with `encoding="utf-8"`. If still failing:
   try `engine='python'` with `on_bad_lines='skip'`.

3. **Progress file pollution**: Old error entries from pre-fix runs contaminate stats.
   Either clear `_errors_*.txt` or ignore the error file count. Patched runs show 0 errors.

4. **Output buffering**: Background Python runs buffer stdout even with `-u` flag in the
   process tool. Check progress/error files for real status, not stdout preview.

5. **Contract generation vs. reality**: Generated contracts may not exist (e.g. EG1801
   before EG was listed in Dec 2018). These return "empty" — expected behavior.

6. **Actual download speed**: With 6 workers and ~0.2s interval, throughput is ~18
   contracts/sec. Full 9000+ contract batch takes ~8-10 minutes.
