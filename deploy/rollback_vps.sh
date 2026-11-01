#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]] || { echo 'Usage: bash deploy/rollback_vps.sh /absolute/path/to/backup'; exit 2; }
backup=$(cd "$1" && pwd -P)
[[ -f "$backup/repo-path" && -f "$backup/code-before.tgz" ]] || { echo 'Invalid backup'; exit 1; }
repo=$(cat "$backup/repo-path")
service=$(cat "$backup/service-name")
[[ "$repo" =~ ^/[a-zA-Z0-9._/-]+$ && "$service" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid manifest'; exit 1; }
[[ -d "$repo/.git" && "$backup" == "$(dirname "$repo")/second-brain-backups/"* ]] || { echo 'Backup does not belong to this checkout'; exit 1; }
[[ -f "$backup/service-before.service" ]] || { echo 'No prior unit backed up; perform rollback manually from docs/DEPLOYMENT.md'; exit 1; }
sudo systemctl stop "$service"
# Restore code only. Current .env and vault/state are deliberately preserved.
tar -xzf "$backup/code-before.tgz" -C "$repo"
sudo install -m 644 "$backup/service-before.service" "/etc/systemd/system/$service.service"
sudo systemctl daemon-reload
if [[ "$(cat "$backup/was-active")" == 1 ]]; then sudo systemctl start "$service"; fi
echo 'Prior code/unit restored. Current vault and .env preserved. Git HEAD is unchanged; git diff shows rollback contents. Do not commit/push until reviewed.'
