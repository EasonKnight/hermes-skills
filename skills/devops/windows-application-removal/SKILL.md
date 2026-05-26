---
name: windows-application-removal
description: Completely remove a Windows application — search all drives, AppData, registry, ProgramData, shortcuts — and handle locked files via deferred deletion when the lock-holding process can't be terminated.
tags:
  - windows
  - cleanup
  - uninstall
  - locked-files
  - registry
  - system-maintenance
trigger: User asks to "remove", "clean", "delete", "uninstall", or "wipe" an application / program / game / software from Windows.
version: 1.1
---

# Windows Application Removal

Complete removal of a Windows application and all its traces, including handling the edge case where a file is locked by an unrelated process.

## Step 1 — Discovery (find every trace)

Search in order. Use `-iname` to case-insensitively match the app name.

### File-system search
```bash
# Dirs on C: (most common)
find /c/Program\ Files -maxdepth 3 -iname "*<appname>*" -type d 2>/dev/null
find "/c/Program Files (x86)" -maxdepth 3 -iname "*<appname>*" -type d 2>/dev/null

# AppData (user-scoped data + cache)
find /c/Users/$USER/AppData -maxdepth 5 -iname "*<appname>*" -type d 2>/dev/null
find /c/Users/$USER/AppData -maxdepth 5 -iname "*<appname>*" -type f 2>/dev/null | head -20

# ProgramData (system-scoped data)
find /c/ProgramData -maxdepth 5 -iname "*<appname>*" 2>/dev/null

# Other drives
for d in /d /e /f; do
  find "$d" -maxdepth 3 -iname "*<appname>*" -type d 2>/dev/null
done

# Shortcuts
find "/c/ProgramData/Microsoft/Windows/Start Menu" -iname "*<appname>*" 2>/dev/null
find "/c/Users/$USER/Desktop" -iname "*<appname>*" 2>/dev/null
find "/c/Users/$USER/Downloads" -iname "*<appname>*" 2>/dev/null
```

### Registry search
```bash
reg query "HKCU\Software" /s /f "<appname>" 2>/dev/null
reg query "HKLM\SOFTWARE" /s /f "<appname>" 2>/dev/null
reg query "HKLM\SOFTWARE\WOW6432Node" /s /f "<appname>" 2>/dev/null
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "<appname>" 2>/dev/null
reg query "HKLM\SOFTWARE\Classes" /s /f "<appname>" 2>/dev/null | head -30
```

### Start menu & desktop folders
```bash
# ProgramData start menu — often leaves empty folders after uninstall
find "/c/ProgramData/Microsoft/Windows/Start Menu/Programs/" -maxdepth 2 -iname "*<appname>*" -type d 2>/dev/null
find "/c/ProgramData/Microsoft/Windows/Start Menu/Programs/" -maxdepth 2 -iname "*腾讯*" -type d 2>/dev/null  # Chinese apps

# Public desktop shortcuts
find "/c/Users/Public/Desktop" -iname "*<appname>*" 2>/dev/null
```

### Startup entries
```bash
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /s 2>/dev/null | grep -i "<appname>" || echo "No startup entry"
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /s 2>/dev/null | grep -i "<appname>" || echo "No HKLM startup entry"
```

### 1d — IME / Input Method apps (TSF TIP)

Windows Input Method Editors (IME) do NOT register through normal Uninstall entries. Instead they register as TSF Text Input Processors. Use this PowerShell detection script (save as `.ps1`):

```powershell
# List all installed IME CLSIDs with descriptions
Get-ChildItem "HKLM:\SOFTWARE\Microsoft\CTF\TIP" -ErrorAction SilentlyContinue | ForEach-Object {
    $clsid = $_.PSChildName
    $desc = ""
    try { $desc = (Get-ItemProperty "$($_.PSPath)\Category\Category{34745C63-B2F0-4784-8B67-5E12C8701A31}" -ErrorAction SilentlyContinue).'0409' } catch {}
    if (-not $desc) {
        try { $desc = (Get-ItemProperty "$($_.PSPath)\Category\Category{34745C63-B2F0-4784-8B67-5E12C8701A31}" -ErrorAction SilentlyContinue).'0804' } catch {}
    }
    Write-Host "CLSID: $clsid  Desc: $desc"
}

# Also check user language list for registered IME tips
Get-WinUserLanguageList | ForEach-Object {
    Write-Host "Language: $($_.LanguageTag) | IMEs: $($_.InputMethodTips -join ', ')"
}
```

If a target CLSID is found, check its registry subtree and Appx package:
```powershell
# Full registry dump for a TIP CLSID
reg query "HKLM\SOFTWARE\Microsoft\CTF\TIP\{CLSID}" /s

# Check if it's a Store app
Get-AppxPackage | Where-Object { $_.InstallLocation -like "*<appname>*" }
```

Common IME CLSIDs (for reference, do NOT delete built-in ones):
- `{81D4E9C9-1D3B-41BC-9E6C-4B40BF79E35E}` — Microsoft Pinyin (built-in, do NOT remove)
- `{FA550B04-5AD7-411F-A5AC-CA038EC515D7}` — Microsoft Wubi (built-in, do NOT remove)

### 1e — Disable startup entries (for ongoing autostart)

If the goal is to **clean up after uninstall** rather than remove the app, disable its Run entries:

```powershell
# List current user startup entries
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

# Disable a specific entry
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "<EntryName>"

# HKLM startup (may need admin)
Remove-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "<EntryName>"
```

Common Chinese app startup entries: `AweSun` (向日葵), `HuyaExternal` (虎牙), `WeGameMiniLoader`.

## Step 2 — Delete

### 2a — File & Directory deletion

Use `rm -rf` for directories, `rm -f` for individual files:
```bash
rm -rf "/path/to/dir" 2>/dev/null && echo "✅ Deleted" || echo "❌ Delete failed"
rm -f "/path/to/file" 2>/dev/null && echo "✅ Deleted" || echo "❌ Delete failed"
```

### 2b — General registry key deletion

```bash
# HKCU entries (your user scope — safe to delete)
reg delete "HKCU\Software\Vendor\AppName" /f 2>/dev/null

# HKLM entries (may need admin — try first, warn if fails)
reg delete "HKLM\SOFTWARE\Vendor\AppName" /f 2>/dev/null || echo "⚠️ Needs admin rights to delete this registry key"
```

### 2c — Remove stale Uninstall entries (Programs and Features / 控制面板)

When an app was manually deleted without being uninstalled properly, its entry lingers in **Programs and Features (卸载程序)**. The entries live in the Windows Registry under:

| Scope | Registry Path |
|-------|--------------|
| 64-bit / All programs | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` |
| 32-bit (WOW6432Node) | `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall` |
| Per-user installs | `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` |

**⚠️ Important: `reg query` / `reg delete` from git-bash** is unreliable for Chinese-named entries (encoding issues with UTF-8 vs GBK/CP936). Use PowerShell scripts instead.

**Preferred approach — PowerShell script (save to .ps1 file to avoid git-bash `$_` expansion):**

```powershell
$paths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
)

$found = @()
foreach ($regPath in $paths) {
    Get-ChildItem $regPath -ErrorAction SilentlyContinue | ForEach-Object {
        $name = $_.GetValue("DisplayName")
        if ($name -match "<app-regex>") {  # e.g. "PoE|Path of Exile|流放|WeGame"
            $found += @{Name=$name; Guid=$_.PSChildName; RegPath=$_.PSPath}
        }
    }
}

foreach ($item in $found) {
    Remove-Item -Path $item.RegPath -Recurse -Force
    Write-Host "DELETED: $($item.Name) ($($item.Guid))"
}
```

Run it:
```bash
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\$USER\Desktop\clean_uninstall.ps1"
```

**Ad-hoc inline approach** (only for ASCII names — Chinese/korean names will encoding-error in git-bash pipeline):
```bash
# Search via PowerShell
powershell.exe -Command "Get-ChildItem 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall' | ForEach-Object { if ($_.GetValue('DisplayName') -match 'WeGame|PoE') { Write-Host $_.PSChildName; Remove-Item $_.PSPath -Recurse -Force } }"
```

> 💡 **Always save complex PowerShell as a `.ps1` file** and run via `powershell.exe -File`. Inline PowerShell from git-bash suffers from: `$_` being expanded by bash, Unicode/encoding corruption, and `2>$null` parsing errors. The `.ps1` file approach is the only reliable method.

### 2e — Clean up empty parent directories left behind

After removing the main app folders, check for empty parents that the uninstaller forgot to delete:

```bash
# Check common paths
ls "/c/Program Files (x86)/流放之路(511)" 2>/dev/null || rm -rf "/c/Program Files (x86)/流放之路(511)" 2>/dev/null

# Remove empty start menu folders
rmdir "/c/ProgramData/Microsoft/Windows/Start Menu/Programs/腾讯游戏" 2>/dev/null
rmdir "/c/ProgramData/Microsoft/Windows/Start Menu/Programs/腾讯软件" 2>/dev/null

# Remove WeGameApps/WUDownloadCache that were left on D/E drives
rmdir /d "E:/WeGameApps" 2>/dev/null
rmdir /d "E:/WUDownloadCache" 2>/dev/null
```

Use `rmdir` (not `rm -rf`) for empty dirs — it safely skips non-empty ones without accidental data loss.

## Step 3 — Handle Locked Files

If `rm -f` fails with "Device or resource busy", a process holds a lock on the file.

### 3a — Identify the lock-holding process
```bash
# Check if lsof is available (git-bash sometimes bundles it)
lsof "/path/to/locked/file" 2>/dev/null

# Use PowerShell to find process with file handle
powershell.exe -Command '
$path = "C:\\path\\to\\locked\\file"
Get-Process | ForEach-Object {
    try {
        $_.Modules | Where-Object { $_.FileName -eq $path } | ForEach-Object {
            Write-Host ($_.ProcessName + " PID:" + $_.Id)
        }
    } catch {}
}
' 2>/dev/null

# Download and use Sysinternals handle64 (best option for finding lock-holders)
# IMPORTANT: Download to a Windows path (Desktop, Downloads), NOT to /tmp/ —
#   bash tries to execute PE files downloaded to /tmp/ as ELF, giving "Exec format error"
curl -sL -o "%USERPROFILE%\Desktop\handle64.exe" "https://live.sysinternals.com/handle64.exe" --connect-timeout 10 --max-time 20

# Run from cmd.exe — handle64 output is often swallowed by git-bash pipe,
# so redirect to a file and read it afterward
cmd.exe /c "%USERPROFILE%\Desktop\handle64.exe -accepteula -nobanner C:\path\to\locked\file > %USERPROFILE%\Desktop\handle_result.txt 2>&1"
```

**⚠️ Important caveat:** `handle64` run without admin elevation **cannot enumerate handles held by the System process (PID 4)**. If handle64 says "No matching handles found" but the OS still reports the file as locked, the lock is almost certainly held by PID 4 (kernel-inherited handle from a crash or handle inheritance). In this case, skip directly to **Step 3c — Deferred deletion**; no process-killing approach will work.

### 3b — Attempt termination (safe)
```bash
# Only kill if the process belongs SOLELY to the app being removed
# NEVER kill a process that belongs to unrelated software (e.g. WeChat, antivirus)
taskkill /f /pid <PID> 2>/dev/null
```

### 3c — If process can't be killed → Deferred deletion

**Approach A — RunOnce + batch file (preferred, no admin needed):**
1. Write a cleaner batch file:
```bat
@echo off
del /f /q "C:\path\to\locked\file"
rmdir "C:\path\to\locked\dir"
del /f /q "%~f0"
```
2. Register it to run on next login:
   - **If calling directly from bash:** `reg add` often fails with "Invalid syntax" due to git-bash quoting issues.
   - **Fix:** Write a small setup `.bat` file containing the `reg add` command, then run that `.bat`.
   ```bat
   @echo off
   reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v CleanTask /t REG_SZ /d "C:\path\to\cleaner.bat" /f
   ```
   Then from bash:
   ```bash
   "C:/path/to/setup.bat"
   ```
   Or use PowerShell directly:
   ```powershell
   Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce" -Name "CleanTask" -Value "C:\path\to\cleaner.bat" -Type String
   ```

**Approach B — Scheduled task (no admin for current user):**
```bash
schtasks /create /tn "CleanTask" /tr "cmd.exe /c del /f /q \\\"C:\\path\\to\\file\\\" ^& rmdir \\\"C:\\path\\to\\dir\\\"" /sc onlogon /ru "$USER" /f 2>/dev/null
```

> ⚠️ `&` gets interpreted as bash backgrounding in git-bash. Use `^&` or `&&` to escape, or put the commands in a batch file and point `/tr` at the batch file.

**Approach C — MoveFileEx (requires admin):**
```powershell
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class RebootDelete {
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern bool MoveFileEx(string lpExistingFileName, string lpNewFileName, uint dwFlags);
    public static bool ScheduleDelete(string path) {
        return MoveFileEx(path, null, 4); // MOVEFILE_DELAY_UNTIL_REBOOT
    }
}
"@
[RebootDelete]::ScheduleDelete("C:\path\to\file")
```

## Pitfalls

- **Don't kill processes belonging to unrelated software.** WeChat's `crashpad_handler` often holds handles on other apps' log files. Killing it would disrupt the user's WeChat.
- **`cmd.exe /c del /f /q` may return exit code 0 without actually deleting the file** if it's locked. Always verify with `ls`/`Test-Path` afterward.
- **`handle64` run via `cmd.exe /c` in git-bash** often shows no output because git-bash swallows it. Always redirect to a file: `> result.txt 2>&1`
- **`handle64` without admin rights can't see System process (PID 4) handles.** If it says "No matching handles found" but the OS says "in use", the lock is from PID 4 (kernel-inherited handle) — skip straight to deferred deletion.
- **`reg add` from git-bash** can fail with "Invalid syntax" due to quoting issues. Prefer running a `.bat` file that contains the `reg add` command, or use PowerShell `Set-ItemProperty`.
- **`&` in `schtasks /tr`** is interpreted as background operator by git-bash. Use `^&` or `&&` to escape, or put commands in a batch file.
- **`MoveFileEx MOVEFILE_DELAY_UNTIL_REBOOT`** (Approach C) fails with ERROR_ACCESS_DENIED (5) unless running as admin.
- **`find` on git-bash** may silently succeed if you search a non-existent path. Always check `|| echo "Not found"` after each find call.
- **Registry entries in HKLM** (Software\Microsoft\Windows\CurrentVersion\Uninstall) usually require admin to delete. HKCU entries do not.
- **IME apps (input methods) do NOT appear in Uninstall registry.** They register through `HKLM\SOFTWARE\Microsoft\CTF\TIP\{CLSID}` and in `Get-WinUserLanguageList`. To detect them, use the IME detection script in Step 1d. To remove them: for Store-based IMEs, use `Remove-AppxPackage`; for traditional IMEs, remove their TIP CLSID registration and unregister from the language list via `Set-WinUserLanguageList`.
- **Chinese app names may differ from their internal codename.** Example: 微信输入法 is internally `WeType`. Always search multiple name variations. See `references/tencent-app-names.md` for common Tencent product naming quirks.

## Linked Files

- **`references/tencent-app-names.md`** — Tencent product naming conventions: internal codename vs display name mappings for WeChat, WeType/微信输入法, WeGame, QQ/QQNT. Consult when the user asks to remove a Tencent product.
- **`references/wegame-cleanup-example.md`** — Concrete walkthrough of a complete WeGame removal, including locked-file resolution via RunOnce deferral. Read this for a worked example before starting a new cleanup.
- **`templates/runonce-cleanup.bat`** — Reusable batch file template for deferred deletion of locked files on next login. Copy, edit the paths, register via `reg add` under RunOnce.
- **`templates/runonce-setup-helper.bat`** — Helper .bat to register a cleanup script in RunOnce. Use this instead of calling `reg add` directly from git-bash, which is prone to quoting errors.
