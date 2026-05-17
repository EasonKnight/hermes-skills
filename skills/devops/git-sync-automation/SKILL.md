---
name: git-sync-automation
description: "Bidirectional git sync between multiple machines using scheduled tasks / cron jobs. Covers the commit-pull-push pattern, credential setup, conflict detection, and Hermes cron integration."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, sync, cron, workflow, multi-machine]
    related_skills: [github-auth, github-repo-management]
---

# Git Multi-Machine Sync Automation

Set up automated bidirectional sync for a git repository across two or more machines using GitHub (or any remote) as the hub.

## When to Use

- User works on the same repo from home and office computers
- User wants daily automatic push/pull without manual git operations
- Repo belongs to the user (has push access) rather than being a read-only fork
- Scenario: "my company PC auto-pushes, my home PC needs to auto-pull and push back"

## Core Pattern

The sync script follows three steps:

```
1. git add -A && git commit     # snapshot local changes
2. git pull --rebase            # fetch remote changes
3. git push                     # push merged result back
```

## Script Template

Create a script at `~/.hermes/scripts/<name>.sh`:

```bash
#!/usr/bin/bash
REPO="/path/to/your/repo"
cd "$REPO" || exit 1

# 1. Commit local uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -m "auto-sync $(date '+%Y-%m-%d %H:%M')"
fi

# 2. Pull remote changes (try main, fallback master)
git pull --rebase origin main 2>/dev/null || git pull --rebase origin master 2>/dev/null
if [ $? -ne 0 ]; then
    echo "PULL FAILED — manual conflict resolution needed"
    exit 1
fi

# 3. Push back
git push
if [ $? -ne 0 ]; then
    echo "PUSH FAILED"
    exit 1
fi

echo "Sync complete: $(date)"
```

## Cron Job Setup (Hermes)

After creating the script, register the cron job:

```bash
cronjob action=create \
  name="【家中电脑】repo-name 每日 git pull+push 同步" \
  prompt="Execute daily git pull and push for sync" \
  schedule="0 12 * * *" \
  repeat=-1 \
  script="<script-name>.sh" \
  workdir="C:\\Users\\<user>\\path\\to\\repo"
```

**Key parameters:**
- `name`: Use descriptive multi-machine naming so it's obvious which machine owns the job. Pattern: `【地点】仓库名 功能 时间`. E.g. `【家中电脑】tq_real_trade 每日 git pull+push 同步`
- `schedule`: Use cron syntax. `0 12 * * *` = daily at noon.
- `script`: Must be a filename in `~/.hermes/scripts/` (absolute paths rejected by the cron API)
- `workdir`: Absolute path to the repo on disk (use Windows path with backslashes)
- `repeat=-1`: Run forever until manually disabled

**Verification — manually test the job after creation:**

```bash
# Run once to verify
cronjob action=run job_id=<id>

# Check result
cd /path/to/repo
git log --oneline -3
git status --short              # should be clean
```

## Machine Setup Checklist

### Machine A (e.g. company PC)
- Git installed and configured (`git config --global user.name`, `user.email`)
- Credential helper set: `git config --global credential.helper manager`
- Repo cloned locally
- Auto-push configured (either via cron or git hooks)
- **Routine**: Before leaving, run `git add -A && git commit -m "msg" && git push`

### Machine B (e.g. home PC)
- Same git config as Machine A
- Same credential helper
- Repo cloned (or pull existing)
- Auto-sync cron job installed (see above)
- **Routine**: At arrival, `git pull` checks if auto-sync already ran

## Git Credential Setup (Windows)

Git Credential Manager for Windows handles auth via browser login:

```bash
# Verify it's installed
git credential-manager --version

# Configure as credential helper
git config --global credential.helper manager

# First push/pull will open browser to authenticate with GitHub
# Subsequent operations are automatic
```

## Push-Only Variant (Single-Machine Backup)

When only **one machine** edits a repo and you just need daily backup to GitHub (no bidirectional sync), use the simpler push-only pattern:

```bash
#!/usr/bin/env bash
REPO="/path/to/repo"
cd "$REPO"

# Check for changes
if [ -z "$(git status --porcelain)" ]; then
    exit 0  # silent exit — nothing to push
fi

git add -A
git commit -m "auto backup $(date +%Y-%m-%d)"
git push origin main
```

### Hermes Cron with no_agent

Register as a `no_agent=True` cron job (pure script, no LLM overhead):

```bash
cronjob action=create \
  name="【家中】repo-name git推送 每日" \
  no_agent=true \
  script="git_autopush.sh" \
  schedule="0 21 * * *"          # daily at 21:00
```

The script name must be a file in `~/AppData/Local/hermes/scripts/` (or `~/.hermes/scripts/` on Linux/Mac). `no_agent=True` means the output is delivered verbatim — on empty output (no changes), no notification is sent.

### Naming Convention

| Pattern | Example |
|---------|---------|
| `【地点】仓库名 功能 频率` | `【家中】a_stock_trade git推送 每日` |
| `【地点】仓库名 功能 频率` | `【家中电脑】tq_real_trade 每日 git pull+push 同步` |

## Pitfalls

### Giant .git directory causes push failures

If the sync task fails with exit code 255 and `du -sh .git` shows hundreds of MB to >1GB, check for ghost data files inside `.git/`:

```bash
ls .git/data/   # should NOT exist in a normal repo
```

`.git/data/` is NOT a standard git directory. Files placed there bloat `.git/` and can cause push rejections from GitHub. See `references/troubleshoot-bloated-git-dir.md` for full diagnosis and cleanup steps.



### Conflict detection
If both machines edit the same line, `git pull --rebase` will fail. The script exits with an error message. Manual resolution is required:

```bash
cd /path/to/repo
git diff            # see what conflicts
# edit conflicting files
git add -A
git rebase --continue
git push
```

### Never-leave-a-mess rule
Before leaving one machine, always push. On arrival at the other, the auto-sync will pull cleanly. If you leave uncommitted work behind, the next machine's auto-sync won't see it.

### Credential expiry
Git Credential Manager caches tokens, but occasional expiry may pop a browser window. On a headless/server machine, use a GitHub Personal Access Token instead:

```bash
git remote set-url origin https://<token>@github.com/user/repo.git
```

### Hermes cron limitations
- Cron jobs run on the Hermes host; if Hermes isn't running, the job won't fire
- The cron scheduler evaluates cron syntax correctly but the job will only execute while the Hermes daemon is alive
- For OS-native scheduling on Windows, use Task Scheduler instead as a fallback

## Migrating to Windows Task Scheduler

When the user prefers OS-native scheduling, migrate Hermes cron jobs to Windows Task Scheduler.

### Step 1: Create a .bat script

Place a batch file alongside the repo. Use `findstr` + `errorlevel` to check for changes — `set /p`
with file redirection is fragile on Chinese-locale Windows where `%date%` and `%time%` contain
Unicode characters that break string comparison.

**IMPORTANT:** Write the `.bat` file via Python `open().write()` inside `execute_code`, not via
`terminal` + `echo >>` in bash — MSYS escaping of redirect operators (`>`, `&`) and batch
syntax (`%%`) produces corrupted files. Python's file I/O is the only reliable path.

For push-only (backup):

```batch
@echo off
REM chcp 65001 needed on Chinese-locale Windows to handle %date%/%time% Unicode
chcp 65001 >nul 2>&1
cd /d "C:\Users\<user>\Desktop\<repo>"

REM Check for changes — exit silently if none (findstr is more reliable than set /p)
git status --porcelain > "%TEMP%\gs.tmp"
findstr . "%TEMP%\gs.tmp" >nul
if %errorlevel% neq 0 (
    del "%TEMP%\gs.tmp" 2>nul
    exit /b 0
)
del "%TEMP%\gs.tmp" 2>nul

git add -A
git commit -m "auto backup %date%"
git push origin main
```

For bidirectional sync (pull+rebase+push):

```batch
@echo off
chcp 65001 >nul 2>&1
cd /d "C:\Users\<user>\Desktop\<repo>"

REM 1. Commit local changes
git status --porcelain > "%TEMP%\gs.tmp"
findstr . "%TEMP%\gs.tmp" >nul
if %errorlevel% equ 0 (
    git add -A
    git commit -m "auto-sync %date%"
)
del "%TEMP%\gs.tmp" 2>nul

REM 2. Pull remote changes (try main, fallback master)
git pull --rebase origin main 2>nul
if %errorlevel% neq 0 git pull --rebase origin master 2>nul
if %errorlevel% neq 0 (
    echo PULL FAILED - manual conflict resolution needed
    exit /b 1
)

REM 3. Push back
git push
if %errorlevel% neq 0 (
    echo PUSH FAILED
    exit /b 1
)
```

### Pre-bake step (copy before git)

When the sync source isn't a working directory but config/skills/dotfiles that live
elsewhere on the filesystem, add a copy step before the git operations:

```batch
@echo off
chcp 65001 >nul 2>&1
set SRC=C:\Path\To\Configs
set REPO=C:\Users\<user>\Desktop\<repo>

REM 1. Snapshot the source files
xcopy /e /i /q "%SRC%" "%REPO%\" >nul 2>&1

REM 2. Git operations (same pattern as above)
cd /d "%REPO%"
git status --porcelain > "%TEMP%\gs.tmp"
findstr . "%TEMP%\gs.tmp" >nul
if %errorlevel% neq 0 (
    del "%TEMP%\gs.tmp" 2>nul
    exit /b 0
)
del "%TEMP%\gs.tmp" 2>nul
git add -A
git commit -m "auto snapshot %date%"
git push origin main
```

### Step 2: Register via schtasks

**⚠️ CRITICAL: Use Python subprocess, not MSYS bash.**

In MSYS git-bash, `schtasks /create /tn "【中文】任务名" ...` fails because the shell mangles Chinese characters and path separators. The shell converts `C:\Users` to `/c/Users` which schtasks rejects.

**Fix**: Run the command through Python subprocess with native Windows paths:

```python
import subprocess

cmd = [
    "schtasks", "/create",
    "/tn", "【地点】仓库名 功能 频率",    # e.g. 【家中】a_stock_trade git推送 每日
    "/tr", "cmd /c C:\\Users\\<user>\\Desktop\\<repo>\\script.bat",
    "/sc", "daily",
    "/st", "21:00",                      # HH:MM 24h format
    "/f"                                  # force overwrite
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
print(r.stdout)  # "SUCCESS: The scheduled task ... has been created."
```

Do NOT use MSYS bash to invoke schtasks with Chinese characters in the task name — it will silently parse the path incorrectly.

### Step 3: Clean up Hermes cron

```bash
cronjob action=remove job_id=<id>
```

Also remove the Hermes script file from `~/AppData/Local/hermes/scripts/` since it's no longer needed.

### Step 4: Verify

```bash
schtasks /query /tn "任务名" /fo LIST /v
```

Check for: `Status: Ready`, `Next Run Time`, `Task To Run` (should point to your .bat).

### Naming Convention (keep consistent with Hermes)

Use the same pattern as Hermes cron naming for consistency:

| Pattern | Example |
|---------|---------|
| `【地点】仓库名 功能 频率` | `【家中】a_stock_trade git推送 每日` |

Tasks appear in Task Scheduler Library under the root folder `\`.

## Verification

```bash
# Check last sync status
cronjob action=list

# Check repo status
cd /path/to/repo
git log --oneline -5
git status --short
```

## Reference

See `scripts/sync-template.sh` for the exact script template used in this skill.

See `references/hermes-skills-backup-to-github.md` for a complete worked example:
backing up Hermes skills/config/profiles to GitHub with daily Windows Task Scheduler.
