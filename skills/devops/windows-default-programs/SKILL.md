---
name: windows-default-programs
description: "Set Windows default file associations, protocol handlers, and per-user default apps. Covers Windows 10/11 UserChoice protection, UWP AppX ProgId discovery from AppxManifest.xml, and workarounds when standard methods are blocked."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [windows, file-associations, default-programs, devops]
    related_skills: [windows-application-removal, windows-performance-optimization]
---

# Windows Default Programs (File Associations)

## Overview

Windows 10/11 locks down file associations with **UserChoice hash protection** — the registry key under `HKCU\...\FileExts\.ext\UserChoice` has special ACLs that deny even the user write/delete access. The old COM API (`Windows.ApplicationAssociationRegistration`) was removed on Windows 11 builds. Setting defaults requires working within these constraints.

This skill covers every method that works, ranked by reliability and admin requirements.

## When to Use

- User asks to change what program opens .jpg, .pdf, .html, .mp4, or any file type
- User reports "WPS Office took over my image files" or similar hijacking
- User wants to set a UWP app (Photos, Edge, etc.) as the system default
- You need to find the AppX ProgId for a Windows Store app

## Methods (Ranked by Priority)

### 1. Settings UI via ms-settings URI (No Admin Required)

Opens Windows Settings to the exact page for a file type. Fastest reliable method.

```powershell
Start-Process "ms-settings:defaultapps?filename=.jpg"
```

Replace `.jpg` with any extension. The user then clicks the app in Settings.

For bulk operations (multiple extensions), open the general page:
```powershell
Start-Process "ms-settings:defaultapps"
```

### 2. DISM Bulk Import (Admin Required)

Best for batch-setting many extensions at once.

```cmd
rem Step 1: Export current associations
dism /online /Export-DefaultAppAssociations:"C:\path\to\assoc.xml"

rem Step 2: Edit the XML — change the <Association> elements' ProgramId
rem attributes to the target app's ProgId

rem Step 3: Import back
dism /online /Import-DefaultAppAssociations:"C:\path\to\assoc.xml"
```

Note: You need Administrator privileges for both export and import.

### 3. Community Tool: SetUserFTA

Handles the UserChoice hash generation. Download from https://github.com/Dijji/SetUserFTA. No admin needed. Usage:

```cmd
SetUserFTA.exe .jpg AppX4mntx4h978m1v9gtzv0ewksfd6pmwsre
```

## Finding the Correct ProgId for UWP Apps

Windows Store (UWP) apps don't use traditional ProgIds. Their AppX ProgIds are embedded in the app manifest.

### Step-by-step

```powershell
# 1. Find the app's install location
$app = Get-AppxPackage *Microsoft.Windows.Photos*
$manifest = "$($app.InstallLocation)\AppxManifest.xml"

# 2. Read the manifest and find FileTypeAssociation declarations
[xml]$xml = Get-Content $manifest
# Look for migrationprogid lines:
#   Old Progid -> AppX43hnxtbyyps62jhe9sqpdzxn1790zetc
#   New ProgId -> AppX4mntx4h978m1v9gtzv0ewksfd6pmwsre
```

The "New ProgId" values are the ones to use. These ProgIds are registered under `HKCU\Software\Classes\AppX*`.

### Common Photos App ProgIds

| Purpose | Old ProgId | New ProgId |
|---------|-----------|------------|
| Images (jpg, png, gif, bmp, tiff, webp, ico) | AppX43hnxtbyyps62jhe9sqpdzxn1790zetc | AppX4mntx4h978m1v9gtzv0ewksfd6pmwsre |
| Raw camera files | AppX9rkaq77s0jzh1tyccadx9ghba15r6t3h | AppXq8btj36kvahvgqpj75d9n4510vjppa26 |
| DNG | AppXvvwq6wxamf7qhxd0vn6wm1wwehyxrdd6 | AppXnjayypjpx6dtabtjqtt76hhmg5nsz5nm |
| Video files | AppXk0g4vb8gvt7b93tg50ybcy892pge6jmt | AppXcezf6bjsrpbyaqwyjdehhb46y5e5mm3a |

## Diagnosis: Checking Current Association

```powershell
# System-level ProgId (assoc)
cmd /c "assoc .jpg"

# UserChoice override (what actually opens the file)
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.jpg\UserChoice" -Name ProgId,Hash

# OpenWithProgids (registered options)
Get-ItemProperty "HKLM:\SOFTWARE\Classes\.jpg\OpenWithProgids" -ErrorAction SilentlyContinue
```

## Common Pitfalls

1. **UserChoice key is read-protected** — Even `reg delete` returns "Access is denied." This is by design. Do NOT try to force-delete via ACL manipulation; it fails on modern Windows 11.

2. **COM API doesn't exist** — `New-Object -ComObject Windows.ApplicationAssociationRegistration` fails with CLSID `{00000000...}` on Windows 11. Do not attempt.

3. **DISM needs admin** — Error 740 if run without elevation. Check with `whoami` first.

4. **PowerShell escaping in git-bash** — Backticks, `$_`, `&&`, and curly braces cause parsing failures. Write `.ps1` script files for multi-line logic.

5. **CJK/emoji in Write-Host** — Can trigger PowerShell parser errors if .ps1 file is UTF-8 without BOM. Prefer ASCII output for scripts, or ensure UTF-8 BOM encoding.

6. **assoc alone doesn't work** — Setting `assoc .jpg=jpegfile` is overridden by UserChoice. UserChoice must be removed or set to match.

7. **Registry key AppX* may not exist at HKLM** — UWP app ProgIds live under `HKCU\Software\Classes\AppX*`, not HKLM. They get merged at query time.

## Verification Checklist

- [ ] Run `reg query "HKCU\...\FileExts\.jpg\UserChoice" /v ProgId` to confirm the target ProgId
- [ ] Double-click a .jpg file in Explorer to verify it opens with the intended app
- [ ] Check all relevant extensions (.jpg, .jpeg, .png, .gif, .bmp, .tiff, .webp, .ico)
- [ ] If using Settings UI, confirm the app appears in the OpenWith list
