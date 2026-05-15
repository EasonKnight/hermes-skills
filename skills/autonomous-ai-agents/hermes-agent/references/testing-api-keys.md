# Testing API Keys

When diagnosing provider issues, you often need to test whether an API key is valid directly. The `read_file` tool automatically redacts secrets in `.env`, so you cannot copy-paste the key from its output. Use `terminal` + `grep` to extract the real key and test with curl.

## Quick Test Pattern

```bash
export KEY=$(grep '^<PROVIDER>_API_KEY=' "$HOME/AppData/Local/hermes/.env" | cut -d= -f2-)
curl -s -w "\nHTTP_CODE:%{http_code}" https://api.<provider>.com/v1/models \
  -H "Authorization: Bearer $KEY" \
  -H "Accept: application/json" | tail -20
```

## Provider Endpoints

| Provider | Models endpoint |
|----------|----------------|
| DeepSeek | `https://api.deepseek.com/v1/models` |
| OpenAI | `https://api.openai.com/v1/models` |
| Anthropic | Not applicable (different auth format) |
| OpenRouter | `https://openrouter.ai/api/v1/models` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/models` |

## Interpretation

- **HTTP 200** + model list → key is valid, provider is reachable
- **HTTP 401** "invalid api key" → key is expired, revoked, or incorrect
- **HTTP 403** → key lacks permissions or account is not authorized
- **Connection timeout** → provider endpoint is unreachable (network/firewall issue)

## Pitfalls

- `read_file` on `.env` redacts keys with `...` (e.g., `sk-d74...2afd`). Always use `grep` via `terminal` to get the real value.
- `hermes doctor` "API Connectivity" checks may show `✓` even when the key is invalid — the check tests network reachability, not authentication.
- In `execute_code` sandbox, `read_file` tool format differs from direct usage — don't rely on it for key extraction there either.
- Never echo the full key in visible output — always mask with `head -c8` / `tail -c4` or equivalent.
