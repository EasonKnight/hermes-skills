---
name: windows-color-management
category: devops
description: Manage Windows display color profiles — ICC/ICM profiles, HDR calibration, NVIDIA color settings, and Windows Color Management app interaction.
tags: [windows, display, color, icc, hdr, nvidia, monitor]
triggers:
  - user says '颜色配置' / 'color scheme' / '显示器配置' / 'display settings'
  - user asks to apply/switch ICC profile or HDR calibration
  - user asks about monitor/NVIDIA color settings
---

# Windows Color Management (显示器颜色配置)

Manage display color profiles, ICC/ICM profiles, HDR calibration, and NVIDIA color settings on Windows.

## System ICC Profiles Location

System color profiles are stored at:
`C:\Windows\System32\spool\drivers\color\`

Common file types: `.icc`, `.icm`, `.camp`, `.gmmp`, `.cdmp`

## Windows Color Management App

Open the Color Management dialog via:
```
colorcpl.exe
```

## HDR Calibration

Windows 10/11 HDR calibration produces an `.icc` profile in the system color folder.
Apply via **Settings → System → Display → HDR → Color profile** or **Color Management** app.

## Display Settings

Open Windows Display settings directly:
```
ms-settings:display
```

## NVIDIA Color Settings

On Windows, NVIDIA color settings are managed through:
- **NVIDIA Control Panel** → Display → Change Resolution / Adjust Desktop Color Settings
- Path: `C:\Program Files\NVIDIA Corporation\Control Panel Client\nvcplui.exe`
- Or right-click desktop → NVIDIA Control Panel
- Key settings: Digital Vibrance, Gamma, Contrast, Color channel adjustments

## GPU Info Query

```powershell
Get-WmiObject Win32_VideoController | Select-Object Name
```

## Hands-on Actions

### Apply an ICC Profile
1. `colorcpl.exe` → Advanced tab
2. Select display → Add profile → Set as Default
3. Or via Settings → Display → Advanced display → Color profile

### Open Windows HDR Settings
```
ms-settings:hdr
```

### Check Current Color Profiles
- Registry: `HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM`
- System folder: `C:\Windows\System32\spool\drivers\color\`

## Pitfalls

- **Do NOT** assume "颜色配置" means app code color scheme — it may mean display/monitor hardware color. Always clarify if ambiguous.
- ICC files are binary — do not try to read them as text.
- PowerShell inline scripts in git-bash need to be written as .ps1 files to avoid parser errors.
- WMI display info may be unavailable depending on driver model — fall back to registry (HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM).
- NVIDIA Control Panel Client (nvcplui.exe) may not be installed on all systems with NVIDIA drivers (DCH driver model omits it; install from Microsoft Store).
