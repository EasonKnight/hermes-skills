# Token Consumption in Hermes — Why It's Higher Than Normal Chat

## Quick Answer

Hermes consumes **10~100× more tokens** per task than a normal chat interface (ChatGPT, Claude web) because:

1. Every request carries 20-30 tool schemas (~4k-6k tokens fixed overhead)
2. The system prompt is 3k-8k tokens vs ~100 tokens for normal chat
3. Tool-calling tasks require 2~10 API round trips instead of 1
4. Each round trip re-sends the full context (history + tool schemas)

The token cost buys tool execution capability — Hermes can run terminal commands, read/write files, search the web, and execute code. Normal chat cannot.

---

## Anatomy of One Request

### Normal Chat (ChatGPT, Claude web)

```
User: "check disk space"
               ↓
messages = [
  {role: "system", content: ~50 tokens},
  {role: "user",   content: ~5 tokens}
]
               ↓
Total input: ~100 tokens  ×  1 API call
Total cost:  negligible
```

### Hermes (same query)

```
messages = [
  system: "You are Hermes Agent. OS=Windows10, user=Mayn,
           cwd=/c/Users/Mayn, shell=git-bash.
           Memory: user prefers concise responses.
           Conversation rules: ..."       ≈ 2,000-3,000 tokens

  user: "check disk space"                 ≈ 5 tokens
]
+
tools = [
  terminal:    {name, description, params: command,timeout,
                background,workdir,pty,watch_patterns...}  ≈ 500 tokens
  read_file:   {name, description, params: path,offset,limit...} ≈ 200
  write_file:  ...                         ≈ 180
  web_search:  ...                         ≈ 220
  web_extract: ...                         ≈ 180
  search_files: ...                        ≈ 300
  patch:       ...                         ≈ 250
  execute_code: ...                        ≈ 150
  memory:      ...                         ≈ 250
  session_search: ...                      ≈ 200
  delegate_task: ...                       ≈ 500  (complex array param)
  cronjob:     ...                         ≈ 350
  process:     ...                         ≈ 250
  vision_analyze: ...                      ≈ 150
  skill_view:  ...                         ≈ 120
  skill_manage: ...                        ≈ 200
  skills_list: ...                         ≈  60
  clarify:     ...                         ≈ 180
  todo:        ...                         ≈ 150
  text_to_speech: ...                      ≈ 120
  + more depending on enabled toolsets
]                                         ≈ 4,000-6,000 tokens

Total input: ~7,000-10,000 tokens  ×  2+ API calls (tool-call loop)
                                                                  ↑
          90% of token cost is the system prompt + tool schemas  ←┘
```

---

## Why So Many Tokens: The Four Drivers

### 1. Tool Schema Overhead (4k-6k tokens, every request)

Each enabled tool is described as a full JSON Schema to the LLM. The LLM needs these to know what tools exist and what arguments they take.

Example — the `terminal` tool schema:
```json
{
  "name": "terminal",
  "description": "Execute a shell command...",
  "parameters": {
    "type": "object",
    "properties": {
      "command": {
        "type": "string",
        "description": "The shell command to execute"
      },
      "timeout": {
        "type": "integer",
        "description": "Maximum execution time in seconds"
      },
      "background": {
        "type": "boolean",
        "description": "Run in background"
      },
      "workdir": {
        "type": "string",
        "description": "Working directory"
      },
      "pty": {
        "type": "boolean",
        "description": "Use pseudo-terminal"
      },
      "notify_on_complete": {
        "type": "boolean",
        "description": "Notify when background task finishes"
      }
    },
    "required": ["command"]
  }
}
```

That's ~500 tokens for ONE tool. With 20-30 tools enabled, the tool schemas alone cost **4k-6k tokens per request**.

Normal chat = 0 tools = 0 tokens for this.

### 2. Rich System Prompt (2k-8k tokens)

Normal chat: `"You are a helpful assistant"` = ~5 tokens.

Hermes injects:
- Core agent identity (~500 tokens)
- Execution environment (OS, cwd, shell backend) (~300 tokens)
- Memory facts (~200-500 tokens)
- Skill content (if skills loaded) (~500-3000 tokens)
- Conversation rules, output format, security rules (~500 tokens)

### 3. Tool-Call Loop (2~10 API calls per task)

Normal chat: 1 API call per question → done.

Hermes:
```
User: "check disk space"
  → Call 1: LLM returns tool_call("terminal", {cmd: "df -h"})
  → Hermes executes terminal(df -h), appends result
  → Call 2: LLM sees disk info, returns human response
             (or returns another tool_call to continue)
```

Each extra call carries the full context (system prompt + tools + history) again. A multi-step task (search + read + write + final answer) can be **5-10 API calls**.

### 4. Token Counting Includes Both Input AND Output

| Direction | Hermes | Normal Chat |
|-----------|--------|-------------|
| Input per call | 7k-10k tokens | ~100 tokens |
| Output per call | 200-500 tokens | 200-500 tokens |
| Reasoning tokens (DeepSeek) | 500-2000 tokens | 0 (if not shown) |
| Calls per task | 2-10 | 1 |
| **Total per task** | **15k-100k tokens** | **~300 tokens** |

---

## Prompt Caching Mitigation

DeepSeek, Anthropic, and OpenAI all support **prompt caching**. If the system prompt + tool schemas remain identical across calls, the API provider discounts the cached prefix (typically 50-90% off).

Caching helps MOST with batch-like usage (many calls with same toolset). It helps LEAST when:
- Toolsets change mid-session (system prompt changes)
- Skills are loaded/unloaded
- Memory content changes
- Different sessions have different configurations

---

## Token Optimization Tips

### Reduce tool schema count
```bash
# Disable unused toolsets
hermes tools disable web
hermes tools disable vision
hermes tools disable image_gen
# etc. — fewer tools = less schema overhead
```

### Keep sessions short
```bash
# Start fresh to clear history
/reset      # or
hermes -q "question"
```

### Minimize skills loaded
```bash
# Don't load skills unless needed
hermes -q "(no skills loaded by default)"
# vs
hermes -s heavy-skill -q "question"   # more tokens
```

### Use `-Q` (quiet mode)
```bash
# Suppresses some verbose output
hermes -Q -q "question"
```

### Check actual usage
```bash
# In-session
/usage

# CLI
hermes sessions stats
```

### Avoid long multi-step tasks unless necessary
Each tool call means another API round trip. If you can describe what you need in one question, the answer costs less.

---

## Cost Estimate Examples (DeepSeek V4 Flash pricing)

| Task | API calls | Input tokens | Output tokens | USD cost |
|------|-----------|-------------|--------------|----------|
| "What's the weather?" | 2 | ~13k | ~300 | ~$0.002 |
| "Find file, read it, summarize" | 4 | ~30k | ~800 | ~$0.005 |
| "Refactor this project" (10+ tool calls) | 15 | ~120k | ~5000 | ~$0.02 |
| Normal chat — same first question | 1 | ~100 | ~200 | ~$0.00006 |

Hermes is ~30-50x more expensive per task than normal chat, but the tasks it performs are things normal chat simply cannot do. Compare Hermes cost against "human doing the same work" (hourly rate) rather than against "chat answer."
