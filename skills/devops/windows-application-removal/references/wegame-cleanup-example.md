# WeGame Cleanup — Concrete Example

Referenced from: session "Complete WeGame removal" (May 14, 2026)

## What was found

| Location | Path |
|----------|------|
| D: drive (main install) | `D:\Program Files\WeGame\` |
| D: drive (installer) | `D:\Program Files\WeGameInstaller\WeGameSetup6.3.0.1042_launcher_0_0.exe` (413MB) |
| D: drive (game apps) | `D:\WeGameApps\` |
| AppData (config) | `C:\Users\$USER\AppData\Roaming\Tencent\WeGame\` |
| AppData (crash reports) | `C:\Users\$USER\AppData\Local\RailCrashReport\UnsentCrashReports\` — 7 crash-report folders |
| Temp | `C:\Users\$USER\AppData\Local\Temp\` — 4 log files |
| Downloads | `C:\Users\$USER\Downloads\WeGameMiniLoader.*.exe` |

## Registry state

No registry entries at all — the installation was portable/copy-based, not a standard MSI installer.

## Unexpected finding: Kernel/system-level lock

After closing WeChat (the lock-holding process), the file was STILL locked. `handle64.exe` (Sysinternals) reported "No matching handles found" — but the OS still rejected all deletion attempts with "The process cannot access the file because it is being used by another process."

**Root cause:** The handle had been inherited by the **System process (PID 4)** when `crashpad_handler.exe` exited. PID 4 handles are invisible to `handle64` when run without admin elevation. No process-killing approach can resolve this — only a reboot releases such handles.

**Takeaway for future cleanups:** If `handle64` says no handles but the OS says "in use", the lock is kernel-level. Skip all process-termination attempts; go directly to deferred deletion (RunOnce / reboot).

## Locked file resolution

**File:** `C:\Users\$USER\AppData\Roaming\Tencent\WeGame\install.log` (479KB)

**Locker:** `crashpad_handler.exe` PID 15260, owned by WeChat (Weixin 微信 4.1.9.30), not WeGame.

**Resolution:** Could not kill the lock-holder (belongs to unrelated software). Used RunOnce deferred deletion:

1. Created `CleanWeGame.bat` on Desktop:
   ```bat
   @echo off
   del /f /q "C:\Users\$USER\AppData\Roaming\Tencent\WeGame\install.log"
   rmdir "C:\Users\$USER\AppData\Roaming\Tencent\WeGame"
   del /f /q "%~f0"
   ```

2. Registered via RunOnce:
   ```
   reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v CleanWeGame /t REG_SZ /d "C:\Users\$USER\Desktop\Hermes\CleanWeGame.bat" /f
   ```

**Note:** `reg add` in git-bash kept returning "Invalid syntax". The solution was to write the command into a separate setup `.bat` file and run that `.bat` file instead.

## Failed approaches (documented dead ends)

| Approach | Result |
|----------|--------|
| `rm -f` | ❌ Device or resource busy |
| `cmd.exe /c del /f /q` | Returns 0 but file unchanged |
| `takeown` + `icacls` + `del` | ❌ Still locked |
| PowerShell `[System.IO.File]::Delete()` | ❌ Access denied (locked) |
| PowerShell `[System.IO.File]::Open()` with FileShare.ReadWrite | ❌ Cannot open locked file |
| Restart Manager `RmStartSession` | ❌ Failed to start session |
| `MoveFileEx` MOVEFILE_DELAY_UNTIL_REBOOT | ❌ ERROR_ACCESS_DENIED (needs admin) |
| Directory rename | ❌ Cannot rename locked file's parent |
| `schtasks /create /sc onlogon` | ❌ `&` in command string interpreted as bash backgrounding — used `^&` as workaround |
| `handle64` downloaded to `/tmp/` | ❌ `Exec format error` — bash tried to execute PE as ELF. Fix: download to `%USERPROFILE%\Desktop\` |
| `handle64` via `cmd.exe /c` pipe | ❌ Output swallowed — always redirect to file: `> result.txt 2>&1` |
| `reg add` from git-bash | ❌ "Invalid syntax" — workaround: write `reg add` into a .bat file and run that |
