# DeepSeek API — 余额 & 消费查询

## 余额接口

```
GET https://api.deepseek.com/user/balance
Authorization: Bearer <API_KEY>
Accept: application/json
```

### 响应

```json
{
  "is_available": true,
  "balance_infos": [
    {
      "currency": "CNY",
      "total_balance": "110.00",
      "granted_balance": "10.00",
      "topped_up_balance": "100.00"
    }
  ]
}
```

- `is_available`: 余额是否充足
- `currency`: `CNY` 或 `USD`
- `total_balance`: 总余额（含赠送+充值）
- `granted_balance`: 未过期的赠送余额
- `topped_up_balance`: 充值余额（不过期）

## 消费估算（从 agent.log 解析，`estimate_deepseek_consumption()`）

Hermes 日志路径：`~/AppData/Local/hermes/logs/agent.log`

### 函数位置

定义在 `app.pyw` 末尾，`BalanceWindow` 类之前。在 `refresh()` 的 worker 线程中异步调用：

```python
consumption = estimate_deepseek_consumption()  # 返回 dict
result["consumption"] = consumption
```

返回结构：`{calls, cost, token_str, tokens: {input, output, cache}}`

### 日志格式

```
2026-05-16 14:42:08,708 INFO [...] API call #17: model=deepseek-v4-flash provider=deepseek in=50307 out=215 total=50522 latency=2.1s cache=49152/50307 (98%)
```

- 按 `YYYY-MM` 前缀过滤当月行
- 正则：`API call #\d+: model=(\S+) provider=deepseek in=(\d+) out=(\d+)`
- cache 正则：`cache=(\d+)/(\d+)`

### 定价（$ / 1M tokens, 2026年）

| Model | Input | Output | Cache Input |
|-------|-------|--------|-------------|
| deepseek-v4-flash | $0.30 | $0.50 | $0.03 (10%) |
| deepseek-v4-pro | $0.50 | $0.80 | $0.05 (10%) |
| deepseek-chat | $0.28 | $0.42 | $0.028 (10%) |
| deepseek-reasoner | $0.55 | $2.19 | $0.055 (10%) |
| deepseek-reasoner-v4 | $0.60 | $2.50 | $0.06 (10%) |

### 花费公式

默认按 `deepseek-v4-flash` 定价估算（自用最常用模型）：

```
cost = (in_tokens - cache_tokens) * input_price / 1e6
     + cache_tokens * cache_input_price / 1e6
     + out_tokens * output_price / 1e6
```

## 注意

- 不返回历史消费，仅当前余额
- 无 API 端提供月度/日度账单，需自行从日志推算
- 日志从 5月12日左右开始记录（首次安装 Hermes 时），非完整月
