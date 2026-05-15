@echo off
chcp 65001 >nul 2>&1
set HERMES=C:\Users\Mayn\AppData\Local\hermes
set REPO=C:\Users\Mayn\Desktop\Hermes\hermes-skills
set LOG=%TEMP%\hermes-skills-sync.log

echo [%date% %time%] Starting... > %LOG%

if exist "%REPO%\skills" rmdir /s /q "%REPO%\skills"
xcopy /e /i /q "%HERMES%\skills" "%REPO%\skills" >> %LOG% 2>&1

copy /y "%HERMES%\config.yaml" "%REPO%\config.yaml" >> %LOG% 2>&1

if exist "%REPO%\profiles" rmdir /s /q "%REPO%\profiles"
if exist "%HERMES%\profiles" xcopy /e /i /q "%HERMES%\profiles" "%REPO%\profiles" >> %LOG% 2>&1

cd /d "%REPO%"

git status --porcelain > %TEMP%\hs_stat.tmp
findstr . %TEMP%\hs_stat.tmp >nul
if %errorlevel% neq 0 (
    echo No changes. >> %LOG%
    type %LOG%
    exit /b 0
)

git add -A
git commit -m "hermes auto sync" >> %LOG% 2>&1
git push origin main >> %LOG% 2>&1
echo Sync complete. >> %LOG%
type %LOG%
