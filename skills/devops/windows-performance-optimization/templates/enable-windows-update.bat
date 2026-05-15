@echo off
title Restore Windows Update (Run as Admin)

sc config wuauserv start= auto
sc config UsoSvc start= auto
sc config WaaSMedicSvc start= auto
sc config DoSvc start= auto

reg delete "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /f >nul 2>&1
reg delete "HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" /v "BranchReadinessLevel" /f >nul 2>&1

schtasks /Change /TN "Microsoft\Windows\WindowsUpdate\ScheduledStart" /ENABLE >nul 2>&1
schtasks /Change /TN "Microsoft\Windows\UpdateOrchestrator\Schedule Scan" /ENABLE >nul 2>&1
schtasks /Change /TN "Microsoft\Windows\UpdateOrchestrator\Backup Scan" /ENABLE >nul 2>&1
schtasks /Change /TN "Microsoft\Windows\UpdateOrchestrator\Schedule Work" /ENABLE >nul 2>&1

echo Restored. Reboot to re-enable updates.
pause
