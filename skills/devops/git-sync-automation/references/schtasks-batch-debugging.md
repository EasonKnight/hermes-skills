# Windows Schtasks Batch File Debugging

## Symptom: exit code 255 but batch file looks correct

Task registered with schtasks, `Last Result: 255`, batch log is empty,
but running the batch from `cmd.exe` works fine.

**Root cause:** The batch file used `python` (bare name) instead of an absolute path.
schtasks runs in a stripped-down environment that does NOT load the user's
interactive `%PATH%`. The bare `python` resolves to nothing or a Windows Store
stub, and the task fails to launch.

**Fix:** Replace every bare executable name with its absolute path.

```batch
REM ❌ BAD — exit code 255 inside schtasks
python core\update_data.py

REM ✅ GOOD — works inside schtasks
set PY="C:\Users\Mayn\AppData\Local\Programs\Python\Python311\python.exe"
%PY% core\update_data.py
```

## Debugging checklist

| Check | Command | What to look for |
|-------|---------|------------------|
| Task metadata | `schtasks /query /tn "任务名" /fo LIST /v` | Verify `Task To Run` path, `Last Result`, `Last Run Time` |
| Exit code | `Last Result` field | 0=ok, 1=script error, 2=false positive (add `exit /b 0`), 255=not found |
| Batch run test | Open `cmd.exe` and run the batch file's exact command | Must work from fresh cmd, not bash |
| Log file | Check batch redirect target | If empty and exit=255, the script never launched |
| PATH inside task | Add `echo %PATH% > C:\temp\path.txt` to batch | Compare to interactive shell's PATH |

## Always end batch files with `exit /b 0`

Without this, Windows picks up whatever exit code the last internal command
(`echo`, `chcp`, `findstr`, etc.) happened to leave. This causes false exit
codes like 2 even when the actual work succeeded.

## Logging pattern for data update batch files

**⛔ Don't use variables for log paths.** `set LOGFILE="C:\path\to\file.txt"` embeds the quotes AS PART of the variable value. While `>> %LOGFILE%` happens to expand correctly in most cmd contexts, it's fragile — especially under schtasks where the expansion can break. The safest pattern is literal paths everywhere:

```batch
@echo off
echo [%date% %time%] ====== 开始更新 ====== >> "C:\path\to\data\_update_log.txt"

"C:\path\to\python.exe" script.py >> "C:\path\to\data\_update_log.txt" 2>&1
echo [%date% %time%] 完成（exit code: %ERRORLEVEL%） >> "C:\path\to\data\_update_log.txt"

exit /b 0
```

Key details:
- `>> "path" 2>&1` captures both stdout and stderr — use quoted literal paths, never variables
- Timestamp each section so you can diagnose hangs
- Record `%ERRORLEVEL%` explicitly — it's lost after the next command
- Always end with `exit /b 0`
- First line `>` (overwrite) rather than `>>` (append) to start a fresh log each run
