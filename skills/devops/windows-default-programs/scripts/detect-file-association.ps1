<#
.SYNOPSIS
    Detect what program handles a file extension and probe Windows default app settings.

.DESCRIPTION
    For a given extension (e.g. .jpg), shows:
    - System-level ProgId (via assoc)
    - UserChoice override (with Hash)
    - OpenWithProgids list
    - OpenWith MRU history
    - Whether the UWP Photos app is registered
    - The AppX ProgId from Photos manifest

.PARAMETER Extension
    The file extension to check, e.g. ".jpg" or ".pdf". Default: .jpg
#>

param([string]$Extension = ".jpg")

Write-Host "=== File Association Diagnostic ===" -ForegroundColor Cyan
Write-Host "Extension: $Extension" -ForegroundColor Yellow

# 1. System-level assoc
Write-Host "`n1. System assoc:" -ForegroundColor Cyan
cmd /c "assoc $Extension 2>nul"

# 2. System-level OpenWithProgids
Write-Host "`n2. HKCR OpenWithProgids:"
$key = "HKLM:\SOFTWARE\Classes\$Extension\OpenWithProgids"
if (Test-Path $key) {
    $props = Get-ItemProperty $key -ErrorAction SilentlyContinue
    $props.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } | ForEach-Object {
        Write-Host "   $($_.Name)" -ForegroundColor Gray
    }
} else {
    Write-Host "   (not found)" -ForegroundColor Gray
}

# 3. HKCU FileExts branches
Write-Host "`n3. HKCU FileExts:" -ForegroundColor Cyan
$feKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts$Extension"
if (Test-Path $feKey) {
    # UserChoice
    $ucKey = "$feKey\UserChoice"
    if (Test-Path $ucKey) {
        $uc = Get-ItemProperty $ucKey -ErrorAction SilentlyContinue
        Write-Host "   UserChoice ProgId: $($uc.ProgId)" -ForegroundColor Yellow
        Write-Host "   UserChoice Hash:   $($uc.Hash)"
    } else {
        Write-Host "   UserChoice: (none)" -ForegroundColor Green
    }

    # OpenWithList
    $owlKey = "$feKey\OpenWithList"
    if (Test-Path $owlKey) {
        $owl = Get-ItemProperty $owlKey -ErrorAction SilentlyContinue
        Write-Host "   OpenWithList MRU entries:"
        $owl.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' -and $_.Name -ne 'MRUList' } | ForEach-Object {
            Write-Host "     $($_.Name) = $($_.Value)"
        }
    }

    # OpenWithProgids
    $owpKey = "$feKey\OpenWithProgids"
    if (Test-Path $owpKey) {
        $owp = Get-ItemProperty $owpKey -ErrorAction SilentlyContinue
        Write-Host "   OpenWithProgids:"
        $owp.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } | ForEach-Object {
            Write-Host "     $($_.Name)"
        }
    }
} else {
    Write-Host "   (no HKCU FileExts entry)" -ForegroundColor Gray
}

# 4. Check Photos app registration
Write-Host "`n4. Photos App:" -ForegroundColor Cyan
$app = Get-AppxPackage *Microsoft.Windows.Photos* -ErrorAction SilentlyContinue
if ($app) {
    Write-Host "   Installed: $($app.PackageFamilyName)" -ForegroundColor Green
    Write-Host "   Version:   $($app.Version)"

    $progIdKey = "HKCU:\Software\Classes\AppX4mntx4h978m1v9gtzv0ewksfd6pmwsre"
    if (Test-Path $progIdKey) {
        Write-Host "   Photos image ProgId registered: YES" -ForegroundColor Green
    } else {
        Write-Host "   Photos image ProgId: (not found)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   NOT installed" -ForegroundColor Red
}

# 5. Legacy Windows Photo Viewer
Write-Host "`n5. Classic Windows Photo Viewer:" -ForegroundColor Cyan
$wvKey = "HKLM:\SOFTWARE\Classes\jpegfile"
if (Test-Path $wvKey) {
    $desc = (Get-ItemProperty $wvKey -Name '(default)' -ErrorAction SilentlyContinue).'(default)'
    Write-Host "   jpegfile ProgId: $desc" -ForegroundColor Gray
    $cmdKey = "$wvKey\shell\open\command"
    if (Test-Path $cmdKey) {
        $cmd = (Get-ItemProperty $cmdKey -Name '(default)' -ErrorAction SilentlyContinue).'(default)'
        Write-Host "   Command: $cmd"
    } else {
        Write-Host "   No shell\open\command (routed through AppX)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   jpegfile ProgId: (not found)" -ForegroundColor Gray
}

# 6. Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
$currentProgId = (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts$Extension\UserChoice" -Name ProgId -ErrorAction SilentlyContinue).ProgId
if ($currentProgId) {
    Write-Host "Default for $Extension : $currentProgId" -ForegroundColor Yellow
    if ($currentProgId -like '*WPS*') {
        Write-Host ">> WPS Office has overridden this association" -ForegroundColor Red
    } elseif ($currentProgId -like 'AppX*') {
        Write-Host ">> AppX/UWP app is the default" -ForegroundColor Green
    }
}
