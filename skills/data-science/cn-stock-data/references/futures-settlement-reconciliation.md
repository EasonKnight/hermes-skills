# Futures Settlement Reconciliation

Cross-check program-generated monthly settlement Excel reports against official exchange PDF settlement statements. Covers PDF parsing, aggregation comparison, and balance-equation validation.

## Workflow

1. Parse the generated xlsx (funds, fees, futures trades, option trades) using dynamic section-header detection
2. Parse the official PDF — extract both fund summary fields and trade records
3. Compare funds section field-by-field
4. Compare daily P&L and fee totals
5. Aggregate trades by (date, contract, direction) and compare
6. Validate the balance equation: `期末结存 = 期初结存 + 出入金 + 平仓盈亏 - 手续费 + 权利金收入`

## PDF Parsing (Exchange Settlement Format)

The exchange PDF trade section has TWO types of rows:
- **Individual trades**: `日期 交易所 品种 合约 买/卖 投保 成交价 手数 成交额 开/平 手续费 平仓盈亏 权利金`
- **Aggregated close summaries**: Same format but `bs='-'`, lots = total close lots — these are NOT trades, skip them

Column indices (split by whitespace):
```
[0]=date(8-digit) [1]=exchange [2]=product [3]=contract [4]=bs [5]=hedge
[6]=price [7]=lots [8]=turnover [9]=oc [10]=fee [11]=pnl_or_premium [12...]=etc
```

### Pitfalls
- Lines split across PDF pages — reassemble by checking for `^\d{8}\s` as new-line marker
- Page headers/footers like `第 X 页/共 Y页` must be filtered
- Contract names with hyphens (e.g., `eb2607-C-9800`) may cause split-lines
- Option rows have premium instead of pnl in column [11]

## XLSX Parsing

Use dynamic section detection — search for header keywords (`期货成交汇总`, `期权成交汇总`) rather than hardcoded row numbers. Column layout varies between versions.

## Option P&L Script (`期权收益.py`) Pitfalls

When working with `期权收益.py` in the monthly_report project:

1. **Same-month exercise not detected**: The original logic only checks `last_month_num < current_month_num` for expiry. Options opened and exercised/assigned within the same month (e.g., PX607 opened 05-07, exercised 05-27) fall into `ongoing` instead of `expired`. Fix: when `last_month_num == current_month_num` and position != 0, check if `contract_last_seen < last_trading_day_of_month`. If the contract disappeared from daily 持仓汇总 before month-end, it was exercised.

2. **`all_pnl`/`all_fee` scoping**: These totals are computed inside `if expired_trades:` but also used outside it for Excel generation. Must define them before any `if` blocks that reference them to avoid `UnboundLocalError`.

3. **Key name typo**: `trades[0].get('expiry', '')` should be `trades[0].get('expiry_date', '')`.

4. **Dead accumulators**: `all_close_pnl`, `all_close_fee`, `all_exp_pnl`, `all_exp_fee` in `generate_option_report_xlsx` accumulate but are never used — safe to remove.

## Verification

Run `verify_monthly_report.py` in the project directory. It compares:
- All 12 fund fields
- Daily fees and P&L totals  
- Aggregated trade groups by (date, contract, direction)
- Balance equation validation
