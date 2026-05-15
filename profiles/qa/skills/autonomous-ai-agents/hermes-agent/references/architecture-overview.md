# Hermes Agent Architecture Overview

## Core Philosophy

Hermes is an **orchestration framework** — not a model, not a neural network. It:
- Sits between the user and an LLM API (DeepSeek, Claude, GPT, Gemini, local, etc.)
- Manages context, tools, memory, skills, and multi-platform delivery
- Does NOT reason or generate text itself; the LLM does that
- The LLM decides **when** to call a tool; Hermes **executes** the tool call

Analogy: LLM = brain (thinks, reasons), Hermes = nervous system + hands (builds context, executes actions, feeds results back).

---

## Layered Architecture

```
┌─────────────────────────────────────────────────┐
│              User Interface Layer                │
│  CLI (prompt_toolkit) │ TUI (Ink/React)          │
│  Telegram │ Discord │ Slack │ Web API │ ACP      │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Gateway Layer                       │
│  Route messages, authenticate, manage sessions   │
│  Platform adapters in gateway/platforms/         │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│            Agent Core Loop (run_agent.py)        │
│                                                  │
│  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Prompt Builder│  │ Memory   │  │ Compression│  │
│  │ (agent/)      │  │ (memory) │  │ (agent/)   │  │
│  └──────────────┘  └──────────┘  └───────────┘  │
│  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Tool Dispatch │  │ Skills  │  │ Delegation │  │
│  │ (model_tools) │  │ (skills/)│ │ (tools/)   │  │
│  └──────────────┘  └──────────┘  └───────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│             LLM Provider Layer                   │
│  DeepSeek │ Anthropic │ OpenAI │ OpenRouter     │
│  Google Gemini │ Ollama │ Custom OpenAI-compat   │
│  + credential pools, fallback, rotation          │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│           Tool Execution Layer                   │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────┐ │
│  │ terminal │ │ file     │ │ web    │ │code  │ │
│  │ (bash)   │ │ (rw/sear)│ │(search)│ │exec  │ │
│  └──────────┘ └──────────┘ └────────┘ └──────┘ │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────┐ │
│  │ cron     │ │ MCP      │ │ vision │ │deleg │ │
│  │ (sched)  │ │ (ext)    │ │ (img)  │ │(sub) │ │
│  └──────────┘ └──────────┘ └────────┘ └──────┘ │
│              + plugin system                     │
└─────────────────────────────────────────────────┘
```

---

## Agent Loop (The "Consequence Engine")

In `run_agent.py::AIAgent.run_conversation()`:

```
loop:
  1. Build messages array = system prompt + history + user message
  2. Call LLM chat.completions.create(model, messages, tools=schemas)
  3. If LLM returns text → display, exit loop
  4. If LLM returns tool_calls:
     a. For each tool_call:
        - Look up handler in tools/registry.py
        - Call handler(tool_call.args)
        - Append result as tool-role message
     b. Go back to step 2 (continue reasoning with tool results)
```

Key constraint: **message role alternation** (never two assistant or two user messages in a row). Hermes enforces this automatically by inserting tool-role messages between assistant tool calls and the next LLM request.

---

## Tool Dispatch Chain

How a terminal command flows from user question to execution:

```
User: "check disk space"
  ↓
① LLM returns: tool_call(name="terminal", args={command: "df -h"})
  ↓
② model_tools.py :: handle_function_call()
   → looks up "terminal" in registry
   → calls terminal_tool(command="df -h")
  ↓
③ tools/terminal_tool.py :: terminal_tool()
   → reads config: TERMINAL_ENV (local|docker|modal|vercel)
   → selects backend via tools/environments/
  ↓
④ tools/environments/local.py :: LocalEnvironment._run_bash()
   → _find_bash() → e.g. /usr/bin/bash / C:\Program Files\Git\bin\bash
   → builds env (filters API keys, sets PATH, TMPDIR, etc.)
   → subprocess.Popen([bash, "-c", command], cwd=..., env=...)
  ↓
⑤ OS executes the command in a real shell
  ↓
⑥ stdout + stderr captured, returned as JSON:
   {"output": "...", "exit_code": 0, "error": ""}
  ↓
⑦ Appended to messages as {"role": "tool", ...}
  ↓
⑧ Back to LLM for next reasoning step
```

---

## Local Terminal Execution Details

### How `subprocess.Popen` is called (local.py:436)

```python
proc = subprocess.Popen(
    [bash, "-c", command],    # e.g. ["bash", "-c", "df -h"]
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # merge stderr into stdout
    stdin=subprocess.PIPE,     # if stdin_data provided
    cwd=resolved_cwd,          # fall back to nearest existing ancestor
    env=sanitized_env,         # API keys stripped
    preexec_fn=os.setsid,      # process group for kill (POSIX only)
)
```

### Windows-specific adaptations

- Bash located via `_find_bash()` (checks `%ProgramFiles%\Git\bin\bash.exe`, `%USERPROFILE%\scoop\apps\git\...`, etc.)
- MSYS path `/c/Users/...` converted to `C:\Users\...` for `Popen(cwd=...)`
- Temp dir: `~/.hermes/cache/terminal/` instead of `/tmp`
- No `preexec_fn=os.setsid` (Unix-only); Windows uses `taskkill /f /t`
- API key filtering: `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. stripped from subprocess env

### CWD resilience

If the working directory is deleted mid-session (e.g. `rm -rf` on current folder), Hermes walks up parent directories to find the nearest existing ancestor — prevents `FileNotFoundError` on next `Popen` call. Uses `_resolve_safe_cwd()`.

---

## System Prompt Assembly

Every LLM request gets a dynamically composed system prompt:

```
System prompt = 
  ├── Core identity ("You are Hermes Agent, capable of...")
  ├── Execution environment (OS, cwd, shell type)
  ├── Memory injection (cross-session facts from memory tool)
  ├── Skill injection (active skills' SKILL.md content)
  ├── Tool schemas (JSON schema for every enabled tool)
  ├── Conversation rules (role alternation, format guidelines)
  └── Platform-specific instructions (CLI vs Telegram vs Discord)
```

This is typically 3k-6k tokens. Hermes uses **prompt caching** (supported by DeepSeek, Anthropic, OpenAI) so repeated system prefix doesn't incur full cost.

---

## Context Compression

When conversation exceeds 50% of context window, Hermes triggers compression:
1. Old exchanges sent to an auxiliary LLM for summarization
2. Key facts (file paths, errors, user preferences) preserved in summary
3. Side-effects (file writes, terminal commands) are immutable — summarizer warned not to fabricate them
4. Summarized block replaces original exchanges, retaining original message boundaries

---

## Skills vs Memory vs Config

| Concern | Stored in | Injected when | Example |
|---------|-----------|---------------|---------|
| How to do X | Skill (SKILL.md) | Session start + /skill | "Deployment steps, testing workflow" |
| Who user is | Memory (user) | Every turn | "Prefers concise answers" |
| Environment facts | Memory (memory) | Every turn | "Steam at D:\..." |
| Secrets | .env | Never injected | API keys |
| Settings | config.yaml | Startup | Model, timeout, cwd |
