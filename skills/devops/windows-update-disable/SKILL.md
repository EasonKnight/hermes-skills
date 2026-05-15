---
name: windows-update-disable
description: 彻底禁用 Windows 10/11 系统更新（服务 + 注册表 + 策略）
---

# 彻底禁用 Windows 更新

## 适用场景
用户要求永久关闭 Windows 更新，阻止自动下载/安装

## 核心步骤

### 1. 通过注册表禁用受保护服务（WaaSMedicSvc, DoSvc）
Windows 11 的 WaaSMedicSvc 和 DoSvc 有 TrustedInstaller 保护，`sc config` 即使是管理员也会被拒。必须通过 `reg add` 绕过：

```batch
reg add "HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc" /v Start /t REG_DWORD /d 4 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\DoSvc" /v Start /t REG_DWORD /d 4 /f
```

### 2. 禁用常规更新服务
```batch
sc config wuauserv start= disabled
sc stop wuauserv
sc config UsoSvc start= disabled
sc stop UsoSvc
sc config WaaSMedicSvc start= disabled
sc stop WaaSMedicSvc
sc config DoSvc start= disabled
sc stop DoSvc
```

### 3. 注册表组策略
```batch
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "DisableWindowsUpdateAccess" /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "SetDisableUXWUAccess" /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU" /v "NoAutoUpdate" /t REG_DWORD /d 1 /f
```

### 4. 锁定版本 / 暂停到2099年
```batch
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "TargetReleaseVersion" /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v "TargetReleaseVersionInfo" /t REG_SZ /d "22H2" /f
reg add "HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" /v "PauseFeatureUpdatesStartTime" /t REG_SZ /d "2099-12-31" /f
reg add "HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" /v "PauseUpdatesStartTime" /t REG_SZ /d "2099-12-31" /f
```

## 权限问题
- 在 git-bash 终端中无法直接提权（UAC 弹窗不可见）
- 通过 `Start-Process cmd -Verb RunAs` 或 VBS `ShellExecute "runas"` 触发 UAC
- 必须用户手动点击 UAC 「是」按钮
- 即使在管理员账户下，WaaSMedicSvc/DoSvc 的 `sc config` 也会被拒，必须用 `reg add` 改注册表

## 验证
```powershell
Get-Service wuauserv,UsoSvc,WaaSMedicSvc,DoSvc | Format-Table Name,Status,StartType
# 期望: 全部 Stopped + Disabled
```

## 恢复方法
```batch
sc config wuauserv start= auto
sc config UsoSvc start= auto
sc config WaaSMedicSvc start= auto
sc config DoSvc start= auto
reg delete "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /f
```
