# schtasks Data Update Debugging — 2026-05-19

## Background

The user has a daily scheduled task `【家】a_stock_trade 数据更新 每日20点` that runs
two Python scripts (`update_data.py` + `update_fundamentals.py`) via a batch file.
Data was not updating — the CSV showed May 18 even though the task ran at 20:00
with Last Result 0.

## Root Cause Chain

### Layer 1: Python path

The original batch used `C:\Users\Mayn\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`.
This Python has `akshare` installed. When the batch was changed to system Python311
(`C:\Users\Mayn\AppData\Local\Programs\Python\Python311\python.exe`) to test,
akshare was missing → `ModuleNotFoundError`.

**Fix:** Use the hermes venv Python (has all quant packages).

### Layer 2: Batch file encoding

The `write_file` tool wrote the batch as UTF-8. The batch contained Chinese characters
in `echo` statements like `echo 开始更新`. cmd.exe on Chinese Windows cannot parse
UTF-8 Chinese — it garbles them and fails silently.

Symptoms:
- `schtasks /query` showed Last Result 0 but log file was empty
- Manual test from cmd.exe showed garbled text errors
- The redirect `>` to log file didn't write anything

**Fix:** Rewrite batch files with ASCII-only English. Use `cat > file.bat << 'EOF'`
in git-bash rather than the `write_file` tool.

### Layer 3: Variable quoting

Using `set LOGFILE="C:\path.txt"` + `>> %LOGFILE%` caused double-quoting issues.
Fixed by using literal paths directly in each `echo` redirect.

## Final Working Batch File

```batch
@echo off
echo [%date% %time%] START > "C:\Users\Mayn\Desktop\a_stock_trade\data\_batch_run_log.txt"
echo [%date% %time%] update kline... >> "C:\Users\Mayn\Desktop\a_stock_trade\data\_batch_run_log.txt"
cd /d "C:\Users\Mayn\Desktop\a_stock_trade"
"C:\Users\Mayn\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" core\update_data.py >> "C:\Users\Mayn\Desktop\a_stock_trade\data\_batch_run_log.txt" 2>&1
echo [%date% %time%] kline done code=%ERRORLEVEL% >> "C:\Users\Mayn\Desktop\a_stock_trade\data\_batch_run_log.txt"
echo [%date% %time%] update fundamentals... >> "C:\Users\Mayn\Desktop\a_stock_trade\data\_batch_run_log.txt"
"C:\Users\Mayn\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" core\update_fundamentals.py >> "C:\Users\Mayn\Desktop\a_stock_trade\data\_batch_run_log.txt" 2>&1
echo [%date% %time%] fundamentals done code=%ERRORLEVEL% >> "C:\Users\Mayn\Desktop\a_stock_trade\data\_batch_run_log.txt"
echo [%date% %time%] ALL DONE >> "C:\Users\Mayn\Desktop\a_stock_trade\data\_batch_run_log.txt"
exit /b 0
```

## Verification

1. Manual test: `cmd.exe /c "C:\path\to\update_data.bat"` — kline ran in 439s, fundamentals in 3m, NPZ rebuilt
2. One-shot task at 23:04: returned Last Result 0, log showed full output
3. Deleted May 19 data → test task at 23:06 re-downloaded it successfully
4. Log confirmed: "kline done code=0", "fundamentals done code=0"
