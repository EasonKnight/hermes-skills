# Session: tq_real_trade dual-machine sync (2026-05-14)

## User Context
- GitHub user: EasonKnight
- Repo: https://github.com/EasonKnight/tq_real_trade.git
- Purpose: Futures/CTA real trading system, edited from home and work PCs
- Work PC already had auto-push configured (daily auto commit + push)
- Home PC needed auto pull (fetch work's changes) + push (send home changes back)

## Script Used
`~/.hermes/scripts/tq_sync.sh` — standard commit → pull --rebase → push pattern

## Cron Job
- Name: `【家中电脑】tq_real_trade_11 每日 git pull+push 同步`
- Schedule: `0 12 * * *` (daily noon)
- Workdir: `C:\Users\Mayn\Desktop\tq_real_trade_11`

## Edge Case: Script path must be relative
Tried using absolute path `C:\Users\...\auto_sync.sh` for the script parameter in cronjob create — API rejected it. Must copy script to `~/.hermes/scripts/` and use just the filename.

## Edge Case: PowerShell `$_` expansion in git-bash
When running inline PowerShell one-liners from git-bash, `$_` gets expanded by bash to `C:\Users\Mayn.TaskName` etc. Workaround: write `.ps1` files first, then execute with `powershell.exe -ExecutionPolicy Bypass -File /tmp/script.ps1`. This avoids all shell interpolation issues.

## Bonus: Disabling Edge Update Services
User also wanted to stop Edge from auto-updating. Two services to disable (requires admin):
```
edgeupdate   → START_TYPE 2 (AUTO_START) → disabled
edgeupdatem  → START_TYPE 3 (DEMAND_START) → disabled
```
Command: `sc config <servicename> start= disabled`
Elevation needed: Use `Start-Process powershell -Verb RunAs` from non-elevated shell.
