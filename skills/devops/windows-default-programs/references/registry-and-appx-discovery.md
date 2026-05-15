# Registry Paths and AppX Discovery Reference

## Key Registry Locations

### UserChoice Override (per-user, read-protected)
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.ext\UserChoice
  ProgId = <REG_SZ>   # The override ProgId (e.g., "WPS.PIC.jpg")
  Hash   = <REG_SZ>   # Base64 hash that Windows validates
```

This key has special ACLs — even the user cannot write/delete it. Access is denied from both reg.exe and PowerShell on Windows 11.

### System-Level Association (assoc command target)
```
HKLM\SOFTWARE\Classes\.ext
  (default) = <ProgId>   # e.g., "jpegfile" for .jpg
```

This is what `cmd /c assoc .ext` reads. Overridden by UserChoice if present.

### OpenWith Options (registered handlers)
```
HKLM\SOFTWARE\Classes\.ext\OpenWithProgids
  <ProgId> = (default value, type REG_NONE)
```

Lists all ProgIds that offer to open this extension.

### UWP App ProgIds (AppX registration)
```
HKCU\Software\Classes\AppX4mntx4h978m1v9gtzv0ewksfd6pmwsre
  (default) = <description>
  \Application
  \shell\open\command
```

These are the modern AppX ProgIds. NOT in HKLM because they're per-user UWP app registrations. Get merged into the combined view at query time.

### Per-Extension MRU History
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.ext
  \OpenWithList    — MRU of executables used to open this type
  \OpenWithProgids — MRU of ProgIds used (reflects UserChoice)
  \UserChoice      — locked-down current default
```

## AppX Manifest Discovery Procedure

### 1. Find the installed app
```powershell
$app = Get-AppxPackage *Microsoft.Windows.Photos*
```

### 2. Read the manifest
```powershell
$manifest = "$($app.InstallLocation)\AppxManifest.xml"
[xml]$xml = Get-Content $manifest
```

### 3. Find FileTypeAssociation declarations
Search for these patterns in the XML:
- `<uap3:FileTypeAssociation>`
- `<uap:FileType>.jpg</uap:FileType>`
- `Old Progid -> AppX...`
- `New ProgId -> AppX...`

The AppX manifest typically has:
- A comment line: `New ProgId -> AppX<hash>` (this is the active one)
- A comment line: `Old Progid -> AppX<hash>` (backward compatibility)
- A wrapped `<migrationprogid:MigrateApplicationProgIds>` block

### 4. Verify the ProgId exists
```powershell
Test-Path "HKCU:\Software\Classes\AppX4mntx4h978m1v9gtzv0ewksfd6pmwsre"
```

## Commands That Don't Work (Modern Windows 11)

These approaches all fail on Windows 11 build 26200+:
- `New-Object -ComObject Windows.ApplicationAssociationRegistration` → COM class not registered
- `Set-ItemProperty` on UserChoice → "Requested registry access is not allowed"
- `reg delete` on UserChoice → "Access is denied"
- `Set-Acl` on UserChoice → "Requested registry access is not allowed"
- `dism` without admin → "Error 740: Elevated permissions required"

## Extension List for Bulk Configuration

Image extensions handled by Photos:
.jpg .jpeg .png .gif .bmp .tiff .tif .webp .ico .jfif .jpe .jxr .wdp .dib .heic .heif .hif .avif .jxl .thumb

Raw camera extensions:
.arw .cr2 .crw .erf .kdc .mrw .nef .nrw .orf .pef .raf .raw .rw2 .rwl .sr2 .srw .srf .dcs .dcr .drf .k25 .3fr .ari .bay .cap .iiq .eip .fff .mef .mdc .mos .r3d .rwz .ori .cr3 .avci .dng
