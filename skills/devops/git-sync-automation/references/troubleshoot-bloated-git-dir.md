# Troubleshooting Bloated .git Directory (Push Failures)

## Scenario

`git push` fails — often with error code 255 in automated sync scripts — and the `.git/` directory is abnormally large (hundreds of MB to >1GB for a small code repo).

## Root Cause: `.git/data/` Ghost Directory

Files placed **inside** `.git/` (e.g. `.git/data/a_stock_kline_3y.csv` at 1GB) are **not** tracked by git, but they bloat the repository directory. This can cause:

- `git push` to fail (GitHub's 100MB limit metadata scanning may reject)
- Cloning/sync operations to be extremely slow
- Disk usage ballooning for no reason

This is **not** a standard git structure — it's typically caused by:
- A script accidentally writing data files to `.git/data/` instead of `data/`
- Manual file operations inside `.git/`
- A misconfigured scheduled task or batch file

## Diagnostic Steps

```bash
# 1. Check total .git size
du -sh .git

# 2. Identify what's eating space in .git
du -sh .git/* | sort -rn

# 3. If .git/data/ exists and is large, inspect contents
ls -la .git/data/

# 4. Check if any code references this path
grep -r "\.git.*data" --include="*.py" --include="*.bat" --include="*.sh" .

# 5. Check for orphaned large blobs in git packs
git verify-pack -v .git/objects/pack/*.idx | awk '{if($3 > 50000000) print $3, $4, $1}'
```

## Fix

### Step 1: Delete ghost data inside .git/

```bash
# ONLY if .git/data/ contains files you're sure should be in data/ instead
rm -rf .git/data/
```

**Verify:** `du -sh .git` should drop dramatically.

### Step 2: Clean orphaned blobs from git history

```bash
# Expire all reflog entries (makes orphaned objects eligible for pruning)
git reflog expire --all --expire=now

# Aggressive garbage collection
git gc --prune=now --aggressive
```

**Verify:** `git count-objects -vH` — `size-pack` should be in the KB range for a typical code repo.

### Step 3: Audit .gitignore

Ensure large generated files are excluded:

```gitignore
data/*.csv
data/*.npz
data/*.h5
data/*.parquet
results/
backtest_results/
*_progress.txt
```

**Verify:**
```bash
# Check specific files are ignored
git check-ignore data/large_file.csv

# Check nothing large is accidentally tracked
git ls-files | xargs -I{} sh -c 'find "{}" -size +10M' 2>/dev/null
```

### Step 4: Test push

```bash
git push --dry-run
```

Should return "Everything up-to-date" without warnings.

## Prevention

Add a `.gitkeep` or `.gitignore` in `.git/` directories that are used to host ghost data:

While you can't .gitignore files inside `.git/` itself (it's the git directory), you should **never** let scripts write to paths inside `.git/`. Audit all scheduled tasks and batch files:

```bash
# Check all batch files for paths that might resolve to .git/
grep -rn "\.git" --include="*.bat" --include="*.py" --include="*.sh" .
```

## Worked Example (from session 2026-05-17)

- `.git/` was 1.4GB for a ~50MB code repo
- `ls .git/data/` showed `a_stock_kline_3y.csv` (1011MB), `a_stock_kline_3y.npz` (63MB) — files not referenced by any code
- No scripts wrote to `.git/data/` — origin unknown
- After `rm -rf .git/data/` and `git gc --aggressive`: `.git/` → 491KB
- `git push --dry-run` passed
- Scheduled task `【家中】a_stock_trade git同步 每日` subsequently ran successfully
