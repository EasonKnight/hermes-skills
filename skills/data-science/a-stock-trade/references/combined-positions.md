# Combined Positions Panel (组合持仓)

Right column of "实盘策略" tab. Shows portfolio after proportional position scaling (等比缩仓), with real-time price updates via Sina API.

## Bottom Bar (`pos_bar_lbls`)

8 labels created by `make_aligned_bar(pos_sec, POS_COLS)`:

```
POS_COLS = [("code","股票代码",120), ("pname","股票名称",105),
            ("lots","总手数",75), ("price","参考价",85),
            ("amount","总市值",100), ("change_pct","涨跌幅",85),
            ("strategies","涉及策略",100), ("weighted","加权涨跌",85)]
```

| Index | Column | Content in bar | Source |
|-------|--------|---------------|--------|
| `[0]` | 股票代码 | `合计X只(N→X)` | `len(adjusted)`, `_pos_agg_size` |
| `[1]` | 股票名称 | (empty) | — |
| `[2]` | 总手数 | total lots | `sum(x[2])` |
| `[3]` | 参考价 | average price/share | `total_amt / (total_lots * 100)` |
| `[4]` | 总市值 | `¥X,XXX,XXX` | `sum(x[3])` |
| `[5]` | 涨跌幅 | `合计 +X.XX%` | weighted return rate, colored |
| `[6]` | 涉及策略 | `分配 ¥X,XXX` | `total_alloc` |
| `[7]` | 加权涨跌 | `收益 ¥+X,XXX` | daily profit amount (signed, colored) |

Color convention: `#f85149` (red) for positive, `#56d364` (green) for negative (international convention, NOT A-share traditional).

## Calculation Flow

```
refresh_combined_positions()
  ├── Aggregate positions from live strategies
  ├── Proportional scaling (equal-proportion weight reduction)
  │   ├── Scale = total_alloc / sum(amounts)
  │   ├── actual_amt < 20000 → drop stock (threshold)
  │   └── Best subset = largest k stocks all ≥ 20k
  ├── _populate_pos_tree()  → renders tree + bar
  │   ├── Sort by current column
  │   ├── wret_total = Σ(amount/total_amt × change_pct)  ← weighted return
  │   ├── profit_amt = total_amt × wret_total / 100       ← daily profit CNY
  │   ├── pos_bar_lbls[5] = "合计 +X.XX%"  (return rate)
  │   └── pos_bar_lbls[7] = "收益 ¥+X,XXX" (profit amount, {profit_amt:+,.0f})
  └── _save_signal_json(adjusted) → signal.json
```

## signal.json Auto-Save

### Method: `_save_signal_json(adjusted=None)`

Location: `core/app_live.py` — AppLiveMixin method.

```python
def _save_signal_json(self, adjusted=None):
    if adjusted is None:
        adjusted = getattr(self, "_pos_data", None)
    if not adjusted:
        # Write empty array
        json.dump([], f)
    # Map code prefix → exchange suffix
    prefix_map = {"000":"SZ","001":"SZ","002":"SZ","003":"SZ",
                  "300":"SZ","301":"SZ","302":"SZ","303":"SZ",
                  "600":"SH","601":"SH","603":"SH","605":"SH","688":"SH"}
    # Build: shares = lots * 100
    for code, _, lots, _, _, _ in adjusted:
        signal_data.append({"stock": f"{code}.{suffix}", "volume": lots * 100})
```

### Trigger Points

1. **App startup** (`app.pyw` line ~583): `self.after(1500, lambda: self._save_signal_json())` — 1500ms delay ensures `refresh_live` → `refresh_combined_positions` → `_pos_data` is populated
2. **"运行全部实盘" button** → `_run_all_live_strategies` → `refresh_live` → `refresh_combined_positions` → `_save_signal_json(adjusted)`
3. **Any manual refresh** → `refresh_combined_positions` always calls `_save_signal_json(adjusted)` with actual data

### Format

```json
[
  {"stock": "600000.SH", "volume": 300},
  {"stock": "000001.SZ", "volume": 200}
]
```

- `stock`: 6-digit code + `.SH` or `.SZ`
- `volume`: number of **shares** (手数 × 100), NOT lots
- Empty portfolio → `[]`

## Real-time Quote Updates

`_fetch_realtime_changes` runs every 3 seconds via background daemon thread. It fetches Sina API data and updates:
- Each row's `change_pct` column (colored tags: `up`/`down`)
- Each row's `weighted` column
- Bottom bar labels `[5]` (return rate) and `[7]` (profit amount)

Must duplicate the same profit calculation as `_populate_pos_tree`:
```python
profit_amt = total_amt * wret / 100
self.pos_bar_lbls[5].config(text=f"合计 {sign}{wret:.2f}%", fg=wcolor)
self.pos_bar_lbls[7].config(text=f"收益 ¥{profit_amt:+,.0f}", fg=wcolor)
```

`{profit_amt:+,.0f}` auto-appends `+` for positive and `-` for negative values.

## Proportional Scaling Threshold

In `refresh_combined_positions`:
```python
if actual_amt < 20000:   # Drop stocks below ¥20,000 after scaling
    ok = False
    break
```

The threshold was raised from ¥10,000 to ¥20,000.
