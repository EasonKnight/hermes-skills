# Lightweight Q&A Setup

Users who want quick Q&A style interaction (no tool loading, no memory, no compression) can use these patterns:

## Method 1: Optimized Hermes Profile

Create a dedicated profile stripped down for pure chat:

```bash
# Create profile
hermes profile create qa --clone

# Strip overhead
hermes -p qa config set agent.max_turns 3
hermes -p qa config set memory.memory_enabled false
hermes -p qa config set compression.enabled false
hermes -p qa config set display.show_cost false
hermes -p qa config set display.tool_progress false

# Disable all unnecessary toolsets
hermes -p qa tools disable terminal
hermes -p qa tools disable file
hermes -p qa tools disable web
hermes -p qa tools disable browser
hermes -p qa tools disable session_search
hermes -p qa tools disable skills
hermes -p qa tools disable delegation
hermes -p qa tools disable cronjob
hermes -p qa tools disable code_execution
hermes -p qa tools disable vision
hermes -p qa tools disable image_gen
hermes -p qa tools disable tts
hermes -p qa tools disable todo
hermes -p qa tools disable messaging
hermes -p qa tools disable video

# Usage
hermes -p qa chat -q "Your question" -Q
```

The `-Q` (quiet) flag suppresses banner, spinner, tool previews.

A profile alias is auto-created at `~/.local/bin/<name>` so the user can type `qa chat -q "..." -Q` directly.

## Method 2: Standalone API CLI (Zero Hermes Overhead)

For true zero-overhead Q&A, create a standalone CLI script that calls the LLM API directly via Python:

```bash
# ~/.local/bin/ds — one-shot Q&A
ds 法国的首都是什么
ds "What is the capital of France?"
echo "question" | ds
```

Key design decisions:
- Use Python's `urllib.request` (stdlib, no pip deps) instead of curl to avoid MSYS/git-bash Unicode encoding issues with Chinese text in shell variables
- Read API key from Hermes `.env` files as fallback chain (profile-specific → global)
- Auto-detect Chinese vs English input for system prompt language hint
- Support both positional args and stdin pipe

### Script structure (bash wrapper → Python inline):

```bash
#!/usr/bin/env bash
PYTHON="/c/Users/Mayn/AppData/Local/hermes/hermes-agent/venv/Scripts/python"
exec "$PYTHON" -c "
import json, os, sys, urllib.request, urllib.error

# Read API key from Hermes .env
env_paths = [
    os.path.expanduser('~/AppData/Local/hermes/profiles/qa/.env'),
    os.path.expanduser('~/AppData/Local/hermes/.env'),
]
...

# Build and send request
data = json.dumps({
    'model': 'deepseek-v4-flash',
    'messages': [
        {'role': 'system', 'content': f'You are a helpful assistant. {lang_hint}'},
        {'role': 'user', 'content': prompt},
    ],
    'stream': False,
}).encode('utf-8')
...
" "$@"
```

## Method 3: Interactive REPL (Sustained Conversation)

For ongoing back-and-forth with DeepSeek, create an interactive REPL:

```bash
# ~/.local/bin/deepseek — interactive chat session
deepseek
```

The REPL supports these commands:
- `/exit` or `/quit` — exit
- `/new` or `/reset` — start fresh conversation
- `/clear` or `cls` — clear screen

Implementation pattern: a Python script with an infinite `while True` loop calling `input()`, building up the `messages` array across turns for conversational context.

Pitfall: `readline` module is not available on Windows — use plain `input()`.

## When to Recommend Which

| User wants | Recommend |
|---|---|
| Still want Hermes ecosystem (session, history, memory control) | Optimized profile (Method 1) |
| Fastest possible response, no framework at all | Standalone CLI (Method 2) |
| Ongoing conversation without restarting | Interactive REPL (Method 3) |
| Both one-shot + interactive | Create both — they share the same API key |

## Pitfalls

- **Windows `python3` stub**: git-bash resolves `python3` to the Microsoft Store stub, not real Python. Always use full path to a known Python (Hermes venv python at `~/AppData/Local/hermes/hermes-agent/venv/Scripts/python`) or use a bash wrapper that calls the Python binary directly.
- **Chinese text in bash -d data**: MSYS/git-bash mangles Unicode in inline JSON. Use Python to build the JSON string programmatically instead of shell string interpolation.
- **Tool changes need session restart**: Hermes tools/skills config is read at session startup. Setting `memory_enabled` or disabling tools takes effect on next session, not mid-conversation.
- **`exec "$PYTHON" -c "..."` vs `python3 -c`**: The bash wrapper with exec + inline Python works reliably on Windows because it controls exactly which Python binary is used and avoids the broken `python3` stub.
- **Embedding variables in Python -c strings**: Bash expands `$` variables inside double-quoted `-c` strings. Use differently escaped quotes or pass values via `"$@"` at the end to avoid injection issues.
