# Running Windows Programs as Admin at Startup (via Scheduled Task)

## Problem

The Startup folder (`shell:startup`) runs programs with **user privileges**. If your goal is to run a tool (Hermes Agent, a monitoring script, etc.) as **Administrator** without a UAC prompt every boot, the Startup folder approach won't work.

## Solution: Scheduled Task with Highest Privileges

Schedule a task that triggers `AtLogOn` with `RunLevel: Highest`. This runs the program as admin **without a UAC prompt** — Windows trusts the Task Scheduler's stored credential.

### Step 1 — Remove old startup shortcut

```powershell
Remove-Item "$env:USERPROFILE\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\myapp.lnk" -Force
```

### Step 2 — Create scheduled task

**Via `schtasks.exe` (works in any shell):**

```cmd
schtasks /Create /TN "MyApp" /TR "cmd.exe /c \"C:\Path\To\myapp.bat\"" /SC ONLOGON /RL HIGHEST /F
```

Key flags:
| Flag | Meaning |
|------|---------|
| `/TN` | Task name (arbitrary) |
| `/TR` | Command to run (the `.bat` or `.exe` path) |
| `/SC ONLOGON` | Trigger on user logon |
| `/RL HIGHEST` | **Run with highest privileges (admin)** |
| `/RU %USERNAME%` | Run as current user (default) |
| `/F` | Force overwrite if task exists |

**Via PowerShell (needs admin):**

```powershell
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"C:\Path\To\myapp.bat`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest -LogonType Interactive

Register-ScheduledTask -TaskName "MyApp" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
```

> **Note:** `Register-ScheduledTask` itself needs admin rights. Use `Start-Process -Verb RunAs` or write to a `.bat` with self-elevation to run this script.

### Step 3 — Verify

```cmd
schtasks /Query /TN MyApp /FO LIST /V | findstr /i "TaskName TaskToRun RunAsUser RunLevel"
```

Expected: `RunLevel: 1` (not `0`), `TaskToRun: cmd.exe /c "..."`, `RunAsUser: <your username>`.

## Comparison: Startup Folder vs Scheduled Task

| Aspect | Startup Folder | Scheduled Task (`/RL HIGHEST`) |
|--------|---------------|-------------------------------|
| Privilege | User | Administrator |
| UAC prompt at boot | No | **No** (task scheduler bypasses UAC) |
| Visibility | Visible in Startup folder | Visible in Task Scheduler |
| Runs when? | At user logon | At user logon |
| Works if user is admin | Yes | Yes |
| Works if user is standard | Yes | **No** (needs stored admin cred) |

## When to Use This

- Launching a CLI agent (Hermes, Claude Code, Codex) that needs to modify system state
- Running a monitoring script that reads performance counters
- Auto-starting a batch file that disables services / modifies registry
- Any scenario where a UAC prompt at boot would be disruptive

## Pitfalls

- **`Register-ScheduledTask` needs admin.** Can't self-elevate the PowerShell cmdlet from a user session; use `schtasks /Create` in an admin shell or write a `.bat` with self-elevation.
- **`/TR` quoting is fragile.** `schtasks` parses the `/TR` argument verbatim. If the path has spaces, wrap the whole `/TR` value in double quotes:
  ```cmd
  schtasks /Create /TN "MyApp" /TR "'C:\Program Files\MyApp\run.bat'" /SC ONLOGON /RL HIGHEST /F
  ```
  Or better: avoid spaces in the bat file path.
- **Task credentials are stored.** If you change your password, the task may fail. Set `-LogonType Interactive` (PowerShell) or use `/IT` flag with `schtasks` to run in the interactive session.
- **Don't use `/RL HIGHEST` for non-admin tasks.** It adds unnecessary elevation overhead and may cause permission issues if the task writes files as admin to a user-owned directory.
