---
name: windows-desktop-configuration
category: devops
description: Windows desktop configuration — display color profiles (ICC/HDR), file associations (UserChoice, ProgId), and keyboard remapping (AutoHotkey v2). Three related Windows customization domains in one skill.
trigger: user asks about Windows display/color settings, file associations, default programs, keyboard remapping, hotkeys, AutoHotkey, AHK, monitor calibration, HDR, ICC profiles, UserChoice
---

# Windows Desktop Configuration

Covers three Windows customization domains that are frequently needed during system setup or cleanup.

## 1. Display Color Management

### System ICC Profiles Location
```
C:\Windows\System32\spool\drivers\color\
```
Common file types: `.icc`, `.icm`, `.camp`, `.gmmp`, `.cdmp`

### Key Commands
- Open Color Management: `colorcpl.exe`
- Open HDR Settings: `ms-settings:hdr`
- Open Display Settings: `ms-settings:display`

### Apply an ICC Profile
1. `colorcpl.exe` → Advanced tab → Select display → Add profile → Set as Default
2. Or via Settings → Display → Advanced display → Color profile

### Check Current Color Profiles
- Registry: `HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM`
- System folder: `C:\Windows\System32\spool\drivers\color\`

### NVIDIA Color Settings
- NVIDIA Control Panel → Display → Change Resolution / Adjust Desktop Color Settings
- Path: `C:\Program Files\NVIDIA Corporation\Control Panel Client\nvcplui.exe`
- Key settings: Digital Vibrance, Gamma, Contrast, Color channel adjustments
- Note: DCH driver model may omit nvcplui.exe (install from Microsoft Store)

### GPU Info
```powershell
Get-WmiObject Win32_VideoController | Select-Object Name
```

**Pitfalls:**
- ICC files are binary — don't read as text
- "颜色配置" may mean display color, not app code color scheme — clarify if ambiguous
- WMI may be unavailable depending on driver model — fall back to registry

## 2. Default Programs (File Associations)

Windows 10/11 locks file associations with **UserChoice hash protection**. Setting defaults requires working within these constraints.

### Methods (Ranked by Priority)

**Method 1: Settings UI via ms-settings URI (No Admin)**
```powershell
Start-Process "ms-settings:defaultapps?filename=.jpg"
```

**Method 2: DISM Bulk Import (Admin Required)**
```cmd
dism /online /Export-DefaultAppAssociations:"C:\path\to\assoc.xml"
# Edit XML ProgramId attributes, then:
dism /online /Import-DefaultAppAssociations:"C:\path\to\assoc.xml"
```

**Method 3: Community Tool SetUserFTA**
Download from https://github.com/Dijji/SetUserFTA. No admin needed.
```cmd
SetUserFTA.exe .jpg AppX4mntx4h978m1v9gtzv0ewksfd6pmwsre
```

### Finding UWP App ProgIds
UWP (Store) apps don't use traditional ProgIds — their AppX ProgIds are in AppxManifest.xml:
```powershell
$app = Get-AppxPackage *Microsoft.Windows.Photos*
[xml]$xml = Get-Content "$($app.InstallLocation)\AppxManifest.xml"
# Look for FileTypeAssociation → migrationprogid lines
```

### Common Photos App ProgIds
- Images (jpg/png/gif/bmp): Old `AppX43hnxtbyyps62jhe9sqpdzxn1790zetc` → New `AppX4mntx4h978m1v9gtzv0ewksfd6pmwsre`
- Raw camera files: Old `AppX9rkaq77s0jzh1tyccadx9ghba15r6t3h` → New `AppXq8btj36kvahvgqpj75d9n4510vjppa26`
- Video files: Old `AppXk0g4vb8gvt7b93tg50ybcy892pge6jmt` → New `AppXcezf6bjsrpbyaqwyjdehhb46y5e5mm3a`

### Diagnosis Commands
```powershell
cmd /c "assoc .jpg"
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.jpg\UserChoice" -Name ProgId,Hash
```

**Pitfalls:**
- UserChoice key is read-protected — don't try to force-delete via ACL manipulation
- COM API `Windows.ApplicationAssociationRegistration` doesn't exist on Windows 11
- `assoc` alone doesn't work — UserChoice overrides it
- UWP ProgIds live under `HKCU\Software\Classes\AppX*`, not HKLM
- PowerShell from git-bash: write `.ps1` files, avoid inline backticks/`$_`

## 3. Keyboard Remapping (AutoHotkey v2)

### Install
```powershell
winget install --id AutoHotkey.AutoHotkey --silent --accept-package-agreements --accept-source-agreements
```
Installed to: `%LOCALAPPDATA%\Programs\AutoHotkey\v2\`

### Script Template
```autohotkey
#Requires AutoHotkey v2.0
#SingleInstance Force

; Map F1-F4 to Win+1 through Win+4 (taskbar shortcuts)
F1::#1
F2::#2
F3::#3
F4::#4
```

Key syntax: `#` = Win, `!` = Alt, `^` = Ctrl, `+` = Shift

### Auto-Start Setup (PowerShell)
```powershell
$w = New-Object -ComObject WScript.Shell
$s = $w.CreateShortcut([Environment]::GetFolderPath('Startup') + '\YourScript.lnk')
$s.TargetPath = [Environment]::GetFolderPath('LocalApplicationData') + '\Programs\AutoHotkey\v2\AutoHotkey64.exe'
$s.Arguments = '"' + [Environment]::GetFolderPath('UserProfile') + '\YourScript.ahk"'
$s.Save()
```

### Common Mappings
| Desired effect | AHK code |
|---|---|
| F1→Win+1 | `F1::#1` |
| Ctrl+Shift+A→Win+D (show desktop) | `^+A::#d` |
| Disable Caps Lock | `CapsLock::Return` |
| Caps Lock→Ctrl | `CapsLock::Control` |
| Media keys from Fn combos | `^F1::Send "{Volume_Down}"` |

### Reload After Editing
```powershell
Stop-Process -Name AutoHotkey64 -Force
# Then restart script
```

**Pitfalls:**
- Save .ahk as UTF-8; always include `#Requires AutoHotkey v2.0`
- AHK v2 doesn't use `$` prefix for variables (that's v1 syntax)
- F1 override affects all programs — use `#HotIf WinActive(...)` to scope
- Win+10+ covers only first 10 taskbar items
- Complex PowerShell: write to `.ps1` file, don't inline from git-bash

## Cross-Cutting Pitfalls

- **PowerShell in git-bash**: Always write complex PowerShell to `.ps1` files. Inline backticks, `$_`, and `&&` get mangled by MSYS.
- **CJK/emoji in PowerShell**: Can trigger parser errors if `.ps1` is UTF-8 without BOM. Use UTF-8 BOM or ASCII-only output.
- **Admin elevation**: UAC prompts are invisible from Hermes terminal tool. Prefer writing `.bat` on desktop for manual right-click "Run as Administrator".
