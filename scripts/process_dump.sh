#!/usr/bin/env bash
# Ingest helper wrapper for Linux VPS / Neovim
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cd "$REPO_DIR"

if [ -f "$REPO_DIR/.env" ]; then
    export $(grep -v '^#' "$REPO_DIR/.env" | xargs -d '\n')
fi

echo "[*] Triggering Second Brain Ingest Pipeline..."

if [ "$#" -eq 0 ]; then
    python3 "$SCRIPT_DIR/ingest.py" --all
else
    python3 "$SCRIPT_DIR/ingest.py" "$@"
fi

echo "[*] Rebuilding Network Index (INDEX.md)..."
python3 "$SCRIPT_DIR/graph_index.py" build

echo "[+] Done. System is up to date."
