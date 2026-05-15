# Hermes Skills Backup to GitHub (Session Reference)

Session: 2026-05-15 — backing up `%LOCALAPPDATA%\hermes\` skills/config/profiles
to `github.com/EasonKnight/hermes-skills` with daily Windows Task Scheduler job.

## What Gets Backed Up

| Source | Destination | Purpose |
|--------|-------------|---------|
| `%LOCALAPPDATA%\hermes\skills\` | `skills/` | All installed skills (user-created + bundled) |
| `%LOCALAPPDATA%\hermes\config.yaml` | `config.yaml` | Model, tools, terminal, memory settings |
| `%LOCALAPPDATA%\hermes\profiles\` | `profiles/` | Custom profiles (qa, default, etc.) |
| `.env` (redacted) | `.env.example` | Keys replaced with `KEY=***` — never push real secrets |

## Excluded

- `sessions/` — 31 MB of historical transcripts, not needed for migration
- `logs/` — runtime logs, not portable
- `.env` — contains API keys; excluded via `.gitignore`
- Curator metadata (`.usage.json`, `.curator_state`) — machine-local

## .gitignore

```
.env
sessions/
logs/
.usage.json
.curator_state
.bundled_manifest
```

## Batch Script Pattern

Full working script at `C:\Users\Mayn\Desktop\Hermes\hermes-skills\sync_hermes_skills.bat`.

Core logic:

1. `xcopy` skills/config/profiles from `%LOCALAPPDATA%\hermes\` into repo
2. `git status --porcelain > tmp` + `findstr . tmp >nul` — detect changes
3. If changes: `git add -A` → `git commit` → `git push origin main`
4. No changes: silent exit (exit /b 0)

**Key details embedded in the script:**
- `chcp 65001 >nul 2>&1` on line 2 — required for Chinese-locale Windows where
  `%date%` and `%time%` contain Unicode characters
- `findstr` not `set /p` for change detection — `set /p` with file redirect is
  fragile when the temp file path contains spaces or Unicode

## Scheduled Task Registration

Use **Python subprocess**, never MSYS bash, for `schtasks /create` with Chinese
task names. MSYS path-converts `/` flags and mangles `C:\Users` to `/c/Users`.

```python
import subprocess

task_name = "【家中】hermes-skills 每日同步"
batch = r"C:\Users\Mayn\Desktop\Hermes\hermes-skills\sync_hermes_skills.bat"

cmd = [
    "schtasks", "/create",
    "/tn", task_name,
    "/tr", batch,           # direct .bat path, no cmd /c wrapper needed
    "/sc", "daily",
    "/st", "21:00",
    "/f"
]
subprocess.run(cmd, capture_output=True, text=True, timeout=15)
```

Verification:
```python
subprocess.run(["schtasks", "/query", "/tn", task_name, "/fo", "LIST", "/v"],
    capture_output=True, text=True, timeout=15)
```

## Migration to New Machine

```bash
git clone https://github.com/EasonKnight/hermes-skills.git

# On the new machine, copy files into place:
xcopy /e /i /q hermes-skills\skills\    "%LOCALAPPDATA%\hermes\skills\"
copy /y hermes-skills\config.yaml       "%LOCALAPPDATA%\hermes\config.yaml"
xcopy /e /i /q hermes-skills\profiles\  "%LOCALAPPDATA%\hermes\profiles\"

# Then create a fresh .env with real API keys
```

## Pitfalls Encountered

- **Batch file encoding**: Writing `.bat` files through `write_file` tool with
  Chinese characters caused PowerShell parser errors (spurious `MissingFileSpecification`,
  `TerminatorExpectedAtEndOfString`). Fixed by writing the file via Python
  `execute_code` with `encoding="utf-8"`.
- **`cmd //c` vs direct execution**: The batch script runs fine standalone.
  Wrapping it in `cmd //c` is unnecessary and can obscure error messages.
- **`schtasks /run` exit code 255**: Happens when the task was created with
  `"cmd /c script.bat"` but the `.bat` had a syntax error. Fix: test the `.bat`
  standalone first, then register the task with the direct `.bat` path.
- **Git push auth on first run**: GCM opens a browser window. If the push
  happens from a scheduled task while the user isn't logged in, it will hang.
  First push should be done interactively to cache the credential.
