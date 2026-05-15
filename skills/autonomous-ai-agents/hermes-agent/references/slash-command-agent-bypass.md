# Agent-Bypassing Slash Command — `/ds` Implementation

## What It Is

A `/ds` slash command that reads the DeepSeek API key from Hermes' `.env` files and makes a direct HTTP call to `api.deepseek.com`, printing the response inline — completely bypassing the Hermes agent loop (no tools, memory, compression, or model routing).

## Files Modified

| File | Change |
|------|--------|
| `hermes_cli/commands.py` | Added `CommandDef("ds", ..., cli_only=True)` to `COMMAND_REGISTRY` (~line 206) |
| `cli.py` | Added `elif canonical == "ds":` handler in `process_command()` (~line 7592) |

## Key Design Decisions

1. **`urllib.request` (stdlib)** — No pip deps, avoids MSYS/git-bash Unicode issues that bite `curl` in shell scripts on Windows.
2. **API key from Hermes `.env`** — Same fallback chain as the standalone `ds` CLI: `profiles/qa/.env` → `~/.hermes/.env`. No duplicate key management.
3. **Auto-detect Chinese input** — Sets `"Respond in Chinese. Be concise."` system prompt when input contains CJK characters.
4. **Rich-formatted output** — Uses `self._console_print(_rich_text_from_ansi(answer))` so the response renders with proper styling inside both the prompt_toolkit TUI and plain terminal mode.
5. **Inline imports** — `import urllib.error, urllib.request` inside the handler block avoids adding top-level imports.

## User Experience

```
/ds 法国的首都是什么
  ⚡ Direct DeepSeek query...

法国的首都是巴黎。巴黎是法国的政治、经济、文化和商业中心，也是世界上最重要的城市之一。
```

## Pitfalls

- **Fragile on update.** Both modified files live in `~/.hermes/hermes-agent/`. Running `hermes update` overwrites them. Keep a patch file or re-apply manually.
- **No gateway support.** `cli_only=True` means it won't work on Telegram/Discord. Add a handler in `gateway/run.py` for that.
- **cmd_original preserves case.** The full text is available for argument parsing; `cmd_lower` is used for dispatch matching.
