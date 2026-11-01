#!/usr/bin/env bash
# Run manually on the VPS after reviewing/pushing the rewrite.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo 'Usage: bash deploy/update_vps.sh /absolute/path/to/second-brain [secondbrain-telegram]'; exit 2
fi
repo=$(cd "$1" && pwd -P)
service=${2:-secondbrain-telegram}
[[ "$repo" =~ ^/[a-zA-Z0-9._/-]+$ && "$service" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid repo path/service name'; exit 2; }
cd "$repo"
[[ "$(git rev-parse --show-toplevel)" == "$repo" ]] || { echo 'Must use the repository root'; exit 1; }
remote=$(git remote get-url origin)
[[ "$remote" == 'https://github.com/tioantawibawa/second-brain-tio' || "$remote" == 'https://github.com/tioantawibawa/second-brain-tio.git' || "$remote" == 'git@github.com:tioantawibawa/second-brain-tio.git' ]] || { echo 'Unexpected Git origin'; exit 1; }
[[ "$(git branch --show-current)" == main ]] || { echo 'Switch to main after reviewing local changes'; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo 'Tracked local changes exist. Review/commit/back up them before deployment; no reset is performed.'; exit 1; }
[[ -f .env ]] || { echo 'Missing .env; configure it on the VPS first'; exit 1; }
for other in secondbrain-telegram second-brain-bot; do
  if [[ "$other" != "$service" ]] && systemctl is-active --quiet "$other"; then
    echo "Another runner ($other) is active. Inspect its WorkingDirectory; stop/disable the duplicate before deploying."; exit 1
  fi
done
git fetch origin main
old=$(git rev-parse HEAD)
git merge-base --is-ancestor HEAD origin/main || { echo 'VPS and GitHub diverged; resolve explicitly before deploying'; exit 1; }
backup="$(dirname "$repo")/second-brain-backups/$(date +%Y%m%d-%H%M%S)-${old:0:8}"
mkdir -p "$backup"
chmod 700 "$backup"
printf '%s\n' "$repo" > "$backup/repo-path"
printf '%s\n' "$service" > "$backup/service-name"
printf '%s\n' "$old" > "$backup/previous-sha"
was_active=0
systemctl is-active --quiet "$service" && was_active=1
printf '%s\n' "$was_active" > "$backup/was-active"
trap 'echo "Deployment failed. Backup: $backup. Service may be stopped; follow docs/DEPLOYMENT.md rollback instructions. No vault reset was performed."' ERR
if systemctl cat "$service" >/dev/null 2>&1; then sudo systemctl stop "$service"; fi
# Snapshot code and all vault/state data after the writer stops.
tar -czf "$backup/code-before.tgz" --exclude='./.git' --exclude='./.env' --exclude='./.venv' --exclude='./node_modules' --exclude='./tmp' --exclude='./raw' --exclude='./inbox_raw' --exclude='./wiki' --exclude='./journal' --exclude='./crm' --exclude='./in_motion' --exclude='./lattices' --exclude='./system_triggers' --exclude='./data' --exclude='./.obsidian' --exclude='./index.md' --exclude='./INDEX.md' --exclude='./log.md' --exclude='./HOME.md' --exclude='./Untitled*' -C "$repo" .
folders=()
for folder in raw inbox_raw wiki journal crm in_motion lattices system_triggers data .obsidian; do
  [[ ! -d "$folder" ]] || folders+=("$folder")
done
for file in index.md INDEX.md log.md HOME.md Untitled*.base Untitled*.canvas; do
  [[ ! -f "$file" ]] || folders+=("$file")
done
if [[ ${#folders[@]} -gt 0 ]]; then tar -czf "$backup/vault-before.tgz" "${folders[@]}"; fi
cp -p .env "$backup/env-before"
fragment=$(systemctl show -p FragmentPath --value "$service" 2>/dev/null || true)
if [[ -n "$fragment" && -f "$fragment" ]]; then sudo cp "$fragment" "$backup/service-before.service"; fi
git merge --ff-only origin/main
python3 -m venv .venv
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m second_brain bot --check
.venv/bin/python -m second_brain health
sed -e "s|@RUN_USER@|$(id -un)|g" -e "s|@REPO_DIR@|$repo|g" deploy/secondbrain-telegram.service.in > "$backup/service-v2.service"
sudo install -m 644 "$backup/service-v2.service" "/etc/systemd/system/$service.service"
sudo systemctl daemon-reload
sudo systemctl enable "$service"
sudo systemctl restart "$service"
sleep 3
sudo systemctl is-active --quiet "$service"
echo "Local service active. Verify /status, text capture, search and plan from Telegram. This is not yet proof of successful message delivery."
echo "Backup: $backup"
git rev-parse HEAD
