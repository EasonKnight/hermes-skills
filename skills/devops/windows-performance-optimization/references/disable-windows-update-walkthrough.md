# Disabling Windows Update — Full Walkthrough

## Context

- Windows 11 Home Chinese edition (no Group Policy Editor `gpedit.msc`)
- User account: regular user (not elevated admin)
- Goal: completely disable Windows Update, including all four update-related services

## Service Target Map

| Service | Display Name | Win10 | Win11 | Protected? |
|---------|-------------|-------|-------|------------|
| `wuauserv` | Windows Update | ✓ | ✓ | No |
| `UsoSvc` | Update Orchestrator Service | ✓ | ✓ | No |
| `WaaSMedicSvc` | Windows Update Medic Service | ✓ | ✓ | **Yes** — resists `sc` even as admin |
| `DoSvc` | Delivery Optimization | ✓ | ✓ | Sometimes on Win11 Home |

## Registry Key Reference

```
HKLM\SYSTEM\CurrentControlSet\Services\<ServiceName>\Start
  Values: 2=Automatic, 3=Manual, 4=Disabled

HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate
  DisableWindowsUpdateAccess (DWORD) = 1
  SetDisableUXWUAccess (DWORD) = 1
  TargetReleaseVersion (DWORD) = 1
  TargetReleaseVersionInfo (SZ) = "22H2"

HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU
  NoAutoUpdate (DWORD) = 1
  AUOptions (DWORD) = 2

HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings
  BranchReadinessLevel (DWORD) = 0x20
  PauseFeatureUpdatesStartTime (SZ) = "2099-12-31"
  PauseUpdatesStartTime (SZ) = "2099-12-31"
```

## What Worked vs What Didn't

| Method | Result |
|--------|--------|
| `sc config wuauserv start= disabled` | ✓ Works (admin only) |
| `sc config UsoSvc start= disabled` | ✓ Works (admin only) |
| `sc config WaaSMedicSvc start= disabled` | ✗ Access Denied even as admin |
| `reg add … WaaSMedicSvc /v Start /d 4` | ✗ Access Denied (needs takeown first) |
| Scheduled Task as SYSTEM | ✗ Fails without prior elevation |
| VBScript `ShellExecute "runas"` | △ Opens UAC popup — user must click Yes |
| `.bat` right-click → Run as Administrator | ✓ Most reliable for protected services |

## Key Lesson: WaaSMedicSvc

The Windows Update Medic Service was introduced in Windows 10 specifically to prevent users and malware from disabling Windows Update. It has:

1. A special security descriptor on its registry key that denies `SetValue` to `BUILTIN\Administrators`
2. A Windows Service Protection (spsvc) mechanism that auto-restores the service config
3. Failure actions that restart the service if killed

On Windows 11 this protection is even stronger. The full bypass requires:
- Taking ownership of the registry key (`takeown`)
- Granting full control (`icacls`)
- Setting `Start=4`
- Nulling out `FailureActions`
- Repeating after major Windows updates that may reset the protection

## Encoding Issue with MSYS

When the `terminal` tool runs via MSYS/bash on Windows, batch files containing non-ASCII characters (Chinese, Japanese, etc.) have garbled output. The `reg.exe` and `sc.exe` commands execute correctly regardless — the encoding corruption only affects `echo` output. Workaround: put `chcp 65001 >nul` at the top of the batch file, or avoid non-ASCII in echo messages.
