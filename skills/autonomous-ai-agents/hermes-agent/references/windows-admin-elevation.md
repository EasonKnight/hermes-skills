# Windows Admin Elevation from Hermes Terminal Tool

When running Hermes on Windows, `terminal` tool commands execute under the **current user's token** via bash (git-bash / MSYS). Unless the Hermes process itself was launched as Administrator, these commands have no elevation — they cannot:

- Modify `HKLM\Software\...` registry keys
- Stop/configure Windows services (most of them)
- Run `powercfg /h off`
- Kill processes owned by SYSTEM or other users
- Write to `System32`, `Program Files`, etc.

This file documents how to work around UAC elevation constraints from within Hermes.

## The Core Problem

Hermes's `terminal` tool runs `subprocess.Popen([bash, "-c", command])`. Even if you wrap the command with `runas` or `Start-Process -Verb RunAs`, the UAC prompt appears on a **hidden desktop** — the agent can't see or click it, and `-Wait` will hang until the invisible prompt times out or the user happens to notice the taskbar flash.

## Working Approaches

### 1. PowerShell Start-Process -Verb RunAs (Simple Commands)

Best for **one-shot admin commands** that don't need multiple steps:

```
cmd //c "powershell.exe -NoProfile -Command Start-Process powershell.exe -ArgumentList '-NoProfile -Command powercfg /h off' -Verb RunAs -Wait"
```

The user sees a UAC dialog pop up on their desktop. The `-Wait` flag makes Hermes pause until the dialog is approved or rejected.

**Limitations:**
- UAC prompt is invisible to the agent; the command hangs if user walks away
- Quoting gets tricky with nested argument lists (PowerShell inside cmd.exe inside bash)
- Only works if the user is a local admin (standard users get "access denied")

### 2. Self-Elevating Batch File (Multi-Step Admin Tasks)

For anything more complex than one flag command, write a `.bat` file with a self-elevation guard at the top:

```
@echo off
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    powershell Start-Process cmd.exe -ArgumentList '/c ""%~f0""' -Verb RunAs
    exit /b
)

:: --- admin commands below here ---
net stop BcastDVRUserService_8da59
sc config BcastDVRUserService_8da59 start=disabled
```

**How it works:** Non-elevated `cacls.exe config` returns error → batch launches itself via `Start-Process -Verb RunAs` with the same path → elevated copy runs from line 1 → `cacls` succeeds → falls through to admin commands.

**Pitfalls:**
- Same UAC prompt issue (user must click Yes)
- If the user is on a **non-admin account**, `cacls` will still fail in the elevated context and the batch exits silently
- The elevated cmd.exe has its own working directory (usually `C:\Windows\System32`) — use absolute paths

### 3. RunOnce + Reboot (Last Resort)

When elevation is blocked (non-admin user, remote session, locked workstation), defer the command to next boot via `RunOnce`:

```
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" ^
  /v "HermesDeferredTask" /t REG_SZ ^
  /d "C:\Users\Mayn\Desktop\Hermes\fix_script.bat" /f
```

**Pitfalls:**
- `RunOnce` under HKCU runs as the **logged-in user**, not as admin — same elevation problem
- For true admin-level deferred tasks, use `HKLM\...\RunOnce` (needs elevation to write) or a scheduled task with `schtasks /create /ru SYSTEM`
- The user must reboot for the task to run

### 4. Scheduled Task as SYSTEM (No UAC)

Create a one-shot scheduled task that runs immediately as SYSTEM (highest privileges):

```
schtasks /create /tn "HermesElevatedTask" /tr "powershell.exe -NoProfile -Command \"powercfg /h off\"" ^
  /sc once /st 00:00 /ru SYSTEM /rl HIGHEST /f
schtasks /run /tn "HermesElevatedTask"
timeout /t 5
schtasks /delete /tn "HermesElevatedTask" /f
```

**Requires:** The `schtasks /create` call itself needs admin rights, so this is only useful as a **second-hop** from approach (1) or (2).

## Detection Patterns

Before attempting elevation, check what you're up against:

```bash
# Check if already admin
cmd //c "net session >nul 2>&1 && echo ADMIN || echo USER"

# Check if process can be killed
cmd //c "taskkill /f /im AweSun.exe 2>&1 | findstr ACCESS"

# Check if service config is locked
cmd //c "sc config BcastDVRUserService_8da59 start=disabled 2>&1"
```

If `net session` returns `USER`, all admin commands will need one of the approaches above.

## Common Admin Tasks from Hermes on Windows

| Task | Command | Approach |
|------|---------|----------|
| Disable hibernation | `powercfg /h off` | (1) Start-Process -Verb RunAs |
| Delete HKLM startup entry | `reg delete "HKLM\..." /v "Name" /f` | (1) or (2) |
| Kill system-owned process | `taskkill /f /im ...` | (1) or (2) |
| Disable a service | `sc config SERVICE start=disabled` | (1) or (2) |
| Set static IP / DNS | `netsh interface ip set ...` | (1) or (2) |
| Install Windows feature | `dism /online /enable-feature ...` | (2) batch file |
| Delete protected file | `takeown /f ... && icacls ... /grant ...:F && del ...` | (2) batch file |

## Pitfalls

- **PowerShell quoting with nested `Start-Process`:** The outer `-Command` string in single/double quotes doesn't compose well across MSYS. Prefer approach (2) (batch file) for complex admin work.
- **UAC timeout:** If the user doesn't click the UAC prompt within ~2 minutes, Windows auto-dismisses it (denies elevation). The `-Wait` will return, and the command silently fails.
- **Non-admin users:** None of the approaches above work for standard users. You must either ask the user to "Run as administrator" from the shell manually, or provide an admin password via `runas /user:Administrator` (which sends the password in cleartext on the command line — not recommended).
- **`sc config` syntax is picky:** The space after `start=` is **required**: `sc config SERVICE start= disabled` (not `start=disabled`).
- **`Get-Service -Name "Name*"` wildcards work** in PowerShell but the exact service name suffix (`_8da59` etc.) varies per machine. Use `sc query type= service state= all | findstr PATTERN` to discover the exact name.
