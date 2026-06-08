---
name: python-project-deployment
description: Deploy Python projects on this Windows machine — venv, pip mirror, env config, verification.
version: 1.0.0
platforms: [windows]
---

# Python Project Deployment (Windows)

Deploy/install a Python project from source (cloned repo or extracted archive) on the user's Windows 10 machine. Covers the full pipeline: venv creation, dependency install, env config, and smoke-test verification.

## Triggers

- "deploy", "install", "setup", "run" + a Python project/repo
- "pip install ." in a project directory
- User hands you a downloaded/extracted project folder and wants it running

## Key Preferences

- **pip always uses Tsinghua mirror**: `-i https://pypi.tuna.tsinghua.edu.cn/simple`
- **No conda**: user doesn't have conda installed. Use `python -m venv` with system Python.
- **Venv in project root**: `venv/` at the project directory, not global.
- **.env from .env.example**: always copy first, then populate with user's API keys.
- **Chinese git mirrors are unreliable**: gitclone.com and similar frequently timeout. Don't iterate through mirrors — tell the user and let them handle the download if direct GitHub clone fails.

## Workflow

### 1. Assess the project
```bash
ls                  # confirm it's a Python project
cat pyproject.toml  # or setup.py / requirements.txt
```
Identify Python version requirement and install method (usually `pip install .`).

### 2. Create venv
```bash
python -m venv venv
```
System Python 3.11 is always available at `python` or `python3`.

### 3. Copy and populate .env
```bash
cp .env.example .env   # always copy first — never create from scratch
```
For API keys, check hermes `auth.json` at `~/AppData/Local/hermes/auth.json` — it may have keys (partially redacted). Ask the user for the full key if needed. Write DEEPSEEK_API_KEY etc. directly into .env.

### 4. Install with Tsinghua mirror
```bash
./venv/Scripts/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple .  2>&1
```
Run in background with `terminal(background=true)` — installs can take minutes. Set `notify_on_complete=true`.

**Pitfall**: do NOT use `pip install -r requirements.txt` unless the file actually lists dependencies. Some projects (like TradingAgents) have `requirements.txt` containing just `.` (self-reference). Always check the file first.

### 5. Verify
```bash
# Check entry point
./venv/Scripts/<command> --help

# Verify config/env loaded correctly
./venv/Scripts/python -c "
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(usecwd=True))
from tradingagents.default_config import DEFAULT_CONFIG
print('provider:', DEFAULT_CONFIG.get('llm_provider'))
print('model:', DEFAULT_CONFIG.get('deep_think_llm'))
"
```
Adapt the config import path to the project's actual module.

## Pitfalls

- **requirements.txt = "."**: some projects do this. Read the file before blindly `pip install -r`.
- **pip default source is slow in China**: always add `-i https://pypi.tuna.tsinghua.edu.cn/simple`. If the user says "用国内源", you forgot this.
- **`git clone` from GitHub in China**: direct GitHub may be slow but usually works with `--depth 1`. Mirror services (gitclone.com, ghproxy) are unreliable — don't try more than one. If they fail, tell the user and ask them to download manually.
- **Partially cloned repos**: if a previous clone is interrupted, the directory exists but is broken. `rm -rf` it before retrying.

## Project-Specific References

- `references/tradingagents-deepseek.md` — DeepSeek .env template, verification snippet, and launch commands for TradingAgents specifically.
