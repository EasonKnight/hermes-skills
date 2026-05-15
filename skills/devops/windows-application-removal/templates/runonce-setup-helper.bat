@echo off
REM === RunOnce Setup Helper ===
REM Run this .bat to register a cleanup script for next login.
REM This is needed because `reg add` called directly from git-bash
REM often fails with "Invalid syntax" due to quoting issues.
REM
REM Usage: Edit the paths below, then run this file (double-click or from bash).

REM === CONFIG: Edit these paths ===
set CLEANUP_SCRIPT=C:\PATH\TO\YOUR\CLEANUP.BAT
set RUNONCE_KEY=CleanTask

REM === Register ===
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v %RUNONCE_KEY% /t REG_SZ /d "%CLEANUP_SCRIPT%" /f

if %errorlevel% equ 0 (
    echo.
    echo [+] RunOnce entry created successfully.
    echo     Name : %RUNONCE_KEY%
    echo     Path : %CLEANUP_SCRIPT%
    echo.
    echo     The script will run at next login.
) else (
    echo.
    echo [X] Failed to create RunOnce entry (errorlevel=%errorlevel%).
    echo     Try running this batch file as administrator.
    echo.
)

echo.
pause
