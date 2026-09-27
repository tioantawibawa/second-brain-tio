# Second Brain Automated Vault Sync Script (PowerShell)
# Commits latest changes and pushes to GitHub so Obsidian on PC receives updates.

$ErrorActionPreference = "Continue"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoDir

if (Test-Path "tools\indexer.py") {
    python tools\indexer.py | Out-Null
}

git add .
$status = git status --porcelain
if ($status) {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm"
    $msg = "chore(sync): automated vault update $now"
    git commit -m $msg
    Write-Host "[+] Committed changes: $msg"
    git push origin main
} else {
    Write-Host "[*] Vault is already clean. Nothing to sync."
}
