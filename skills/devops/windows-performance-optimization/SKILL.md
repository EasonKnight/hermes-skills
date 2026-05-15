---
name: windows-performance-optimization
description: "Windows system performance optimization — service management, startup items, power plans, disk cleanup, and hibernation. For gaming PCs and general desktop use."
version: 1.0.0
author: Hermes Agent
platforms: [windows]
metadata:
  hermes:
    tags: [windows, performance, services, startup, optimization, gaming]
---

# Windows Performance Optimization

Systematic approach to optimizing Windows performance — trimming unnecessary services, cleaning startup items, and freeing disk space. Designed for gaming PCs where background services waste CPU/RAM/disk.

**Related skills:** `windows-application-removal` (per-app uninstall guidance).

## Disabling Windows Update Completely

Windows Update is a common target for gaming PCs. Below is the layered approach for Windows 10/11 Home (no Group Policy Editor).

### Step 1 — Disable core services

```cmd
sc config wuauserv start= disabled
sc stop wuauserv
sc config UsoSvc start= disabled
sc stop UsoSvc
```

Needs admin. The space after `start=` is mandatory.

### Step 2 — Registry policies (no GPEdit on Home edition)

```cmd
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "DisableWindowsUpdateAccess" /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "SetDisableUXWUAccess" /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v "NoAutoUpdate" /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v "AUOptions" /t REG_DWORD /d 2 /f
```

### Step 3 — Lock version (prevent feature upgrades)

```cmd
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "TargetReleaseVersion" /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "TargetReleaseVersionInfo" /t REG_SZ /d "22H2" /f
reg add "HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" /v "BranchReadinessLevel" /t REG_DWORD /d 0x20 /f
reg add "HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" /v "PauseFeatureUpdatesStartTime" /t REG_SZ /d "2099-12-31" /f
reg add "HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" /v "PauseUpdatesStartTime" /t REG_SZ /d "2099-12-31" /f
```

### Step 4 — Disable update-related scheduled tasks

```cmd
schtasks /Change /TN "Microsoft\Windows\WindowsUpdate\ScheduledStart" /DISABLE
schtasks /Change /TN "Microsoft\Windows\UpdateOrchestrator\Schedule Scan" /DISABLE
schtasks /Change /TN "Microsoft\Windows\UpdateOrchestrator\Backup Scan" /DISABLE
schtasks /Change /TN "Microsoft\Windows\UpdateOrchestrator\Schedule Work" /DISABLE
```

### Step 5 — Dealing with WaaSMedicSvc (protected service)

**WaaSMedicSvc** (Windows Update Medic Service) is a **protected service** on Windows 11. Even normal admin `sc config` calls return "Access Denied" (error 5). It sits at `Start=3` (Manual) and resists change.

On Windows 11 Home, the most reliable approach is:

1. Write a `.bat` or `.ps1` script with all the above commands
2. Place it on the desktop
3. Tell the user to **right-click → Run as Administrator**
4. Use `takeown` first if it still fails:
   ```cmd
   takeown /f "C:\Windows\System32\config\systemprofile\AppData\Local\Microsoft\Windows\WaaS" /r /d y
   reg add "HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc" /v "Start" /t REG_DWORD /d 4 /f
   ```

Alternative: null out the `FailureActions` binary value to prevent automatic recovery:
```cmd
reg add "HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc" /v "FailureActions" /t REG_BINARY /d "000000000000000000000000000000000000000000000000" /f
```

**DoSvc** (Delivery Optimization) may also resist `sc config` on Windows 11 Home. Same registry fix:
```cmd
reg add "HKLM\SYSTEM\CurrentControlSet\Services\DoSvc" /v "Start" /t REG_DWORD /d 4 /f
```

After Step 5, reboot. Settings → Windows Update should show "某些设置由你的组织管理" (Some settings are managed by your organization).

### Restore

Reverse all changes:
```cmd
sc config wuauserv start= auto
sc config UsoSvc start= auto
sc config WaaSMedicSvc start= auto
sc config DoSvc start= auto
reg delete "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /f
```

## Service Management

### 1. Inventory running services

Write to a `.ps1` file to avoid MSYS `$_` path mangling, then execute via `cmd //c`:

```powershell
# list_services.ps1
Get-Service | Where-Object { $_.Status -eq 'Running' } |
  Select-Object Name, DisplayName, StartType | Sort-Object Name | Format-Table -AutoSize
```

```bash
cmd //c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/path/to/list_services.ps1"
```

### 2. Identify safe-to-disable candidates

**Gaming PC — safe to disable:**

| Service | Why |
|---------|-----|
| `AMD Crash Defender Service` | Crash reporting, not needed |
| `GigabyteUpdateService` | Motherboard auto-update |
| `InventorySvc` | Compatibility assessment |
| `PCManager Service Store` | Microsoft PC Manager |
| `OneSyncSvc_*` | Mail/calendar sync |
| `DoSvc` | Delivery Optimization (P2P bandwidth) |
| `PcaSvc` | Program Compatibility Assistant |
| `WpnService` / `WpnUserService_*` | Windows Push Notifications |
| `lfsvc` | Geolocation |
| `TextInputManagementService` | Touch keyboard (no touch screen) |
| `webthreatdefusersvc_*` | Web threat defense (defender core stays on) |
| `cbdhsvc_*` | Clipboard history |
| `BcastDVRUserService_*` | Game Bar / Game DVR |
| `WifiAutoInstallSrv` | Only needed during WiFi adapter install |

**Already handled in prior sessions (check first):** SysMain, DiagTrack, WSearch, Xbox services, DiagTrack.

### 3. Disable services

**Method A — `sc.exe` (reliable, needs admin):**

```cmd
sc stop "Service Name"
sc config "Service Name" start=disabled
```

Note the **space** after `start=` — `start=disabled` (wrong) vs `start= disabled` (correct).

**Method B — PowerShell `Set-Service`:**

```powershell
Stop-Service "ServiceName" -Force
Set-Service "ServiceName" -StartupType Disabled
```

**Method C — Registry (for stubborn per-user services with `_*` suffix):**

Per-user services (e.g. `OneSyncSvc_8da59`, `cbdhsvc_8da59`, `WpnUserService_8da59`) often resist `sc config` and `Set-Service`. The registry approach is the most reliable:

```powershell
$path = "HKLM:\SYSTEM\CurrentControlSet\Services\ServiceName_8da59"
Set-ItemProperty -Path $path -Name "Start" -Value 4 -Type DWord
```

Start value meanings: 2=Automatic, 3=Manual, 4=Disabled

> **Verify registry writes with admin PowerShell.** Run `Get-ItemProperty -Path $path -Name Start` after setting. If it still shows 2, the write didn't execute with sufficient privileges or the service is protected.

### 4. Verify after reboot

Changes to `StartType` only take full effect after reboot. Before rebooting, verify:

```powershell
Get-Service -Name "ServiceName" | Select-Object Name, Status, StartType
```

A service showing `Automatic` + `Stopped` means it was **stopped but NOT disabled** — it will restart at next boot. Always check `StartType`, not just `Status`.

### 5. Admin elevation from MSYS

When running via Hermes `terminal` tool on Windows (MSYS/bash), UAC prompts are invisible and batch files with non-ASCII characters (e.g. Chinese labels) cause encoding corruption. Three approaches:

**Approach A — inline elevation via PowerShell Start-Process:**

```bash
cmd //c "powershell.exe -NoProfile -Command Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File C:/path/to/script.ps1' -Verb RunAs -Wait"
```

**Approach B — VBScript launcher (opens UAC popup, no output back to terminal):**

Create `elevate.vbs`:
```vbscript
CreateObject("Shell.Application").ShellExecute "cmd.exe", "/c C:\path\to\script.bat", "", "runas", 1
```

Run from terminal:
```bash
cd /c/Users/Mayn/Desktop/Hermes && cscript //nologo elevate.vbs
```

The UAC prompt appears on the desktop. Output goes to the separate admin window, not back to the terminal.

**Approach C — write a `.bat` on the desktop for manual right-click → "Run as administrator".**

This is the **most reliable** method for protected services like WaaSMedicSvc.

**Approach D — batch file with self-elevation check:**

```batch
@echo off
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    powershell Start-Process cmd.exe -ArgumentList '/c ""%~f0""' -Verb RunAs
    exit /b
)
REM ... admin commands here ...
```

> **Encoding pitfall:** Batch files with Chinese (or other non-ASCII) characters written from MSYS/bash will have garbled output when run via `cmd.exe //c`. If using `cmd //c "something.bat"`, the encoding corruption doesn't affect execution of `reg.exe` or `sc.exe` commands, but it may mangle `echo` messages. Workarounds: (1) avoid non-ASCII echo messages in batch files, or (2) add `chcp 65001 >nul` at the top of the batch file and run via PowerShell's Start-Process instead.

**Approach E — Scheduled Task as SYSTEM (when regular elevation fails):**

Some services (WaaSMedicSvc) have ACL protections that block even admin `sc config`. Running as the SYSTEM account via a scheduled task can sometimes bypass this. Create a temporary task:

```powershell
$action = New-ScheduledTaskAction -Execute "C:\path\to\script.bat"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(10)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "TempTask" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
Start-Sleep -Seconds 20
Unregister-ScheduledTask -TaskName "TempTask" -Confirm:$false
```

Note: creating SYSTEM tasks from a non-elevated prompt may still fail with "Access Denied". On Windows 11 Home, pre-elevate first.

### 5. Verify changes

```powershell
Get-Service -Name "ServiceName" | Select-Object Name, Status, StartType
```

## Startup Item Management

### HKCU (current user)

```powershell
# View
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

# Remove
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "ProgramName"
```

### HKLM (all users — needs admin)

```powershell
# View
Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"

# Remove
Remove-ItemProperty -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "ProgramName"
```

Or via `reg.exe`:
```cmd
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "ProgramName" /f
```

## Power Management

### Disable hibernation (frees hiberfil.sys, ~75% of RAM size)

```cmd
powercfg /h off
```

Needs admin. Effect: disables hibernation, deletes hiberfil.sys, prevents recreation. Sleep (S3) is NOT affected.

### Enable/change power plan

```cmd
powercfg /list           # List all plans with GUIDs
powercfg /setactive <GUID>  # Activate a plan
```

Common GUID: High Performance = `8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c` (varies by system).

### Hybrid Sleep / Fast Startup

```cmd
powercfg /a              # Show available sleep states
```

## Disk Cleanup Patterns

### Check disk space

```powershell
Get-PSDrive C,D,E -PSProvider FileSystem | Format-Table Name, @{N='FreeGB';E={'{0:N1}' -f ($_.Free/1GB)}}
```

### Find large folders

```powershell
Get-ChildItem "E:\" -Directory | ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue |
             Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
    [PSCustomObject]@{Name=$_.Name; SizeGB=[math]::Round($size/1GB, 2)}
} | Sort-Object SizeGB -Descending | Select-Object -First 20
```

### Delivery Optimization cache

```cmd
rm -rf /c/Windows/SoftwareDistribution/Download
```

Or via `Dism.exe`:
```cmd
Dism.exe /online /Cleanup-Image /StartComponentCleanup
```

## Making Admin Changes Stick

Some performance optimizations (disabling services, modifying registry) require admin privileges. When running CLI tools from the Startup folder, they don't have admin rights.

Using a **Scheduled Task with `/RL HIGHEST`** lets you run programs as admin at boot without UAC prompts.

See `references/admin-startup-via-scheduled-task.md` for the full walkthrough.

## Pitfalls

- **`$_` in PowerShell gets mangled by MSYS.** Always run PowerShell scripts via `.ps1` file, never inline `-Command` with `$_`.
- **`sc config` syntax is brittle.** The space after `start=` is mandatory: `start=disabled` fails silently; `start= disabled` works.
- **`_8da59` suffix services** are per-user instances of template services. They reappear after reboot unless the registry Start value is set to 4.
- **WaaSMedicSvc (Windows Update Medic Service) is a protected service** on Win 11. Even admin `sc config` returns "Access Denied" (error 5). Bypass via registry: write `Start=4 (DWORD)` directly under `HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc`. May require `takeown` + `icacls` on the registry key first.
- **DoSvc may also be protected** on Windows 11 Home. Same registry bypass: `HKLM\SYSTEM\CurrentControlSet\Services\DoSvc → Start=4`.
- **UAC is invisible from Hermes terminal tool.** The user won't see the elevation prompt. Prefer writing a `.bat` on the desktop for manual right-click execution, or verify elevation succeeded before proceeding.
- **Non-ASCII encoding in batch files.** Chinese/Japanese characters in `echo` statements become garbled when the batch file is run via `cmd.exe //c` from MSYS. The actual `reg.exe` / `sc.exe` commands execute correctly regardless — the corruption only affects echo output. Workaround: `chcp 65001 >nul` at the top of the batch file, or use ASCII-only echo messages.
- **Process vs Service distinction.** Some background programs show as processes (e.g., `MSPCManagerService.exe`) but their service name may differ (e.g., `PCManager Service Store`). Use `Get-Service` to cross-reference.
- **Services with `Automatic` start type and status `Stopped`** are triggered-on-demand — they weren't disabled by `sc config`. Always verify `StartType` property, not just `Status`.
