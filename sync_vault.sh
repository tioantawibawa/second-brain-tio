#!/usr/bin/env bash
# Second Brain Automated Vault Sync Script
# Commits latest changes and pushes to GitHub so Obsidian on PC receives updates.

set -e
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# Ensure git author is configured if missing
git config user.name "Second Brain Bot" || true
git config user.email "bot@secondbrain.local" || true

# Rebuild search index if indexer exists
if [ -f "tools/indexer.py" ]; then
    python3 tools/indexer.py > /dev/null 2>&1 || true
fi

# Add changes
git add .

# Check if there is anything to commit
if ! git diff-index --quiet HEAD --; then
    COMMIT_MSG="chore(sync): automated vault update $(date '+%Y-%m-%d %H:%M')"
    git commit -m "$COMMIT_MSG"
    echo "[+] Committed local changes: $COMMIT_MSG"
    
    # Push to origin main
    if git push origin main; then
        echo "[+] Successfully pushed vault to GitHub origin/main"
    else
        echo "[!] Push failed. Check credentials or network connectivity."
    fi
else
    echo "[*] Vault is already clean. Nothing to sync."
fi
