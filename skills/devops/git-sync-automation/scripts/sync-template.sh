#!/usr/bin/bash
# ============================================================
# Git Multi-Machine Sync Template
# Place in ~/.hermes/scripts/ and create a cron job
# ============================================================

# === CONFIG: change this to your repo path ===
REPO="/c/Users/YourName/Desktop/your-repo"

cd "$REPO" || {
  echo "ERROR: Repo directory not found: $REPO"
  exit 1
}

# --- Step 1: Commit local uncommitted changes ---
if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -m "auto-sync $(date '+%Y-%m-%d %H:%M')"
    echo "Committed local changes"
fi

# --- Step 2: Pull remote changes ---
# Tries 'main' first, falls back to 'master'
git pull --rebase origin main 2>/dev/null || git pull --rebase origin master 2>/dev/null

if [ $? -ne 0 ]; then
    echo "=== PULL FAILED ==="
    echo "There are merge conflicts that need manual resolution."
    echo "Fix them with:"
    echo "  cd $REPO"
    echo "  # edit conflicting files"
    echo "  git add -A && git rebase --continue"
    echo "  git push"
    exit 1
fi
echo "Pull successful"

# --- Step 3: Push back ---
git push
if [ $? -ne 0 ]; then
    echo "=== PUSH FAILED ==="
    echo "Check your network or GitHub credentials."
    exit 1
fi

echo "=== Sync complete: $(date) ==="
