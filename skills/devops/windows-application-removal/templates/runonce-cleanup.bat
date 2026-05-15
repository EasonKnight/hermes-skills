@echo off
REM === RunOnce Cleanup Script ===
REM Auto-generated for deferred deletion on next login
REM This script deletes locked files, then removes itself.

REM === CONFIG: Edit these paths ===
set LOCKED_FILE=C:\PATH\TO\LOCKED\FILE.EXT
set LOCKED_DIR=C:\PATH\TO\PARENT\DIR

REM === Execution ===
if exist "%LOCKED_FILE%" (
    del /f /q "%LOCKED_FILE%" 2>nul
    echo Deleted: %LOCKED_FILE%
) else (
    echo File not found: %LOCKED_FILE%
)

if exist "%LOCKED_DIR%" (
    rmdir "%LOCKED_DIR%" 2>nul
    if %errorlevel% equ 0 (
        echo Deleted: %LOCKED_DIR%
    ) else (
        echo Directory not empty or still locked: %LOCKED_DIR%
    )
) else (
    echo Dir not found: %LOCKED_DIR%
)

REM === Self-destruct ===
del /f /q "%~f0" 2>nul
