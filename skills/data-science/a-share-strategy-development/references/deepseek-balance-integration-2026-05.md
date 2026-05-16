# DeepSeek Balance & Consumption Integration (2026-05-16)

## Overview

Added a `💰` button to `app.pyw` header that opens a modal `BalanceWindow` showing:
- DeepSeek account balance (total / granted / topped-up)
- Monthly API consumption estimated from Hermes agent.log

## DeepSeek API: Get User Balance

**Endpoint**: `GET https://api.deepseek.com/user/balance`
**Auth**: `Authorization: Bearer <DEEPSEEK_API_KEY>`
**Response**:
```json
{
  "is_available": true,
  "balance_infos": [{
    "currency": "CNY",
    "total_balance": "110.00",
    "granted_balance": "10.00",
    "topped_up_balance": "100.00"
  }]
}
```

## API Key Source

Read from Hermes auth.json:
```
C:\Users\Mayn\AppData\Local\hermes\auth.json
→ credential_pool.deepseek[0].access_token
```
Fallback: `DEEPSEEK_API_KEY` env var.

## Monthly Consumption via agent.log

There is **no DeepSeek API for billing history**. Consumption is estimated by parsing:
```
C:\Users\Mayn\AppData\Local\hermes\logs\agent.log
```

### Log Format

Successful calls (INFO level):
```
2026-05-16 14:42:08,708 INFO [...] API call #17: model=deepseek-v4-flash provider=deepseek in=50307 out=215 total=50522 latency=2.1s cache=49152/50307 (98%)
```

Failed calls (WARNING level, no token data — skip):
```
2026-05-16 12:34:34,410 WARNING [...] API call failed ...
```

### Regex

```python
pattern = re.compile(r"API call #\d+: model=(\S+) provider=deepseek in=(\d+) out=(\d+)")
cache_pattern = re.compile(r"cache=(\d+)/(\d+)")
```

Only process lines starting with current month prefix (e.g. `2026-05`).

### Pricing Table (USD per 1M tokens)

| Model | Input | Output | Cache Input |
|-------|-------|--------|-------------|
| deepseek-v4-flash | $0.30 | $0.50 | $0.03 |
| deepseek-v4-pro | $0.50 | $0.80 | $0.05 |
| deepseek-chat | $0.28 | $0.42 | $0.028 |
| deepseek-reasoner | $0.55 | $2.19 | $0.055 |
| deepseek-reasoner-v4 | $0.60 | $2.50 | $0.06 |

Cost formula:
```
input_cost  = (input_tokens - cache_tokens) * input_price / 1_000_000
cache_cost  = cache_tokens * cache_input_price / 1_000_000
output_cost = output_tokens * output_price / 1_000_000
total_cost  = input_cost + cache_cost + output_cost
```

### Limitations
- Log exists from 2026-05-12 only, so full monthly data unavailable
- Pricing estimated by most-used model (v4-flash); actual cost varies if other models used
- Failed API calls have no token data and are excluded

## BalanceWindow Implementation

```python
class BalanceWindow(Toplevel):
    """Modal Dracula-themed window, 380x280, centered on parent."""
    # Uses urllib.request (stdlib) to avoid extra deps
    # Async via threading + polling pattern
    # Falls back gracefully if auth.json or log unavailable
```

### Tkinter Patterns
- `transient(parent) + grab_set()` for modal behavior
- `loading` label shown during fetch, hidden when data arrives
- `info_frame` packed/forgotten to swap loading ↔ content
- Polling: `_poll_worker(thread, result)` checks `thread.is_alive()` at 200ms intervals
- Error text in `error_label` with red foreground, wraplength=340

### Thread Safety
- API call and log parsing run in a background thread
- Result dict: `{"ok": {...}, "consumption": {...}}` or `{"err": "..."}`
- Only `after()` callbacks modify Tkinter widgets
