---
name: windows-keyboard-remapping
description: Remap keyboard keys and create custom shortcuts on Windows using AutoHotkey v2. Install, write scripts, set up auto-start, and manage AHK processes.
category: devops
trigger: user asks to remap keys, create keyboard shortcuts, assign hotkeys, or customize Fn keys on Windows.
---

# Windows Keyboard Remapping (AutoHotkey v2)

Install, configure, and manage AutoHotkey v2 scripts for keyboard remapping on Windows.

## Quick Start

### 1. Install AutoHotkey v2

```powershell
winget install --id AutoHotkey.AutoHotkey --silent --accept-package-agreements --accept-source-agreements
```

Installed to: `%LOCALAPPDATA%\Programs\AutoHotkey\v2\`
Executables: `AutoHotkey64.exe` (64-bit), `AutoHotkey32.exe` (32-bit)

### 2. Write a Script

Create `YourScript.ahk` (AHK v2 syntax):

```autohotkey
#Requires AutoHotkey v2.0
#SingleInstance Force

; Map F1-F4 to Win+1 through Win+4 (taskbar shortcuts)
F1::#1
F2::#2
F3::#3
F4::#4
```

**Key syntax reference:**
- `#` = Win key, `!` = Alt, `^` = Ctrl, `+` = Shift
- `F1::#1` = Press F1 to send Win+1
- `F1::Send "^c"` = Press F1 to send Ctrl+C
- Hotstrings: `::btw::by the way` = auto-expand text

### 3. Run the Script

```powershell
# Start
& "$env:LOCALAPPDATA\Programs\AutoHotkey\v2\AutoHotkey64.exe" "$env:USERPROFILE\YourScript.ahk"
```

From git-bash:
```bash
"/c/Users/Mayn/AppData/Local/Programs/AutoHotkey/v2/AutoHotkey64.exe" "C:\Users\Mayn\YourScript.ahk"
```

### 4. Set Up Auto-Start

Create a shortcut in the Windows Startup folder:

```powershell
$w = New-Object -ComObject WScript.Shell
$s = $w.CreateShortcut([Environment]::GetFolderPath('Startup') + '\YourScript.lnk')
$s.TargetPath = [Environment]::GetFolderPath('LocalApplicationData') + '\Programs\AutoHotkey\v2\AutoHotkey64.exe'
$s.Arguments = '"' + [Environment]::GetFolderPath('UserProfile') + '\YourScript.ahk"'
$s.Description = 'Custom keyboard shortcuts'
$s.Save()
```

### 5. Reload / Restart After Editing

Kill the existing process and restart:

```powershell
Stop-Process -Name AutoHotkey64 -Force
# Then restart the script (same command as step 3)
```

Or from AHK tray icon: right-click → "Reload This Script"

## Script Management

**Check if running:**
```powershell
Get-Process -Name AutoHotkey*
```

**Multiple scripts:** Each runs as a separate AutoHotkey64.exe process. Organize by keeping all custom scripts in one file, or use `#Include` to split across files.

**Exclude specific programs:**
```autohotkey
#HotIf WinActive("ahk_exe notepad.exe")
F1::Send "Hello"   ; F1 types "Hello" in Notepad
#HotIf               ; Reset scope
```

## Common Mappings

| Desired effect | AHK code |
|---|---|
| F1→Win+1 | `F1::#1` |
| F2→Win+2 | `F2::#2` |
| Ctrl+Shift+A→Win+D (show desktop) | `^+A::#d` |
| Disable Caps Lock | `CapsLock::Return` |
| Caps Lock→Ctrl | `CapsLock::Control` |
| Win+R→Run dialog (remap) | `#r::Send "^n"` |
| Media keys from Fn combos | `^F1::Send "{Volume_Down}"` |

## Pitfalls

- **Encoding**: Save .ahk files as UTF-8 (with BOM on older AHK versions, but AHK v2 handles UTF-8 without BOM fine).
- **#Requires v2.0**: Always include this line. Without it AHK defaults to v1 syntax which is different.
- **$ prefix**: In AHK v2, variables don't need `$` prefix (that's v1 syntax).
- **PowerShell from git-bash**: Write complex PowerShell logic to a `.ps1` file rather than inline with backticks and `$_`. See memory notes for git-bash PowerShell pitfalls.
- **F1 key override**: F1 is normally "Help" in most Windows apps. Remapping it globally affects all programs. Use `#HotIf WinActive(...)` to scope.
- **Win+10+**: Windows `Win+1` through `Win+0` covers only the first 10 taskbar items. For items beyond, use `Win+T` then arrow keys (see example below).
- **Script auth**: Windows may ask for admin on first run if the script path is protected.
