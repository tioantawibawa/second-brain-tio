# Ingest helper wrapper for Windows PowerShell
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Split-Path -Parent $scriptDir

Set-Location $repoDir

Write-Host "[*] Triggering Second Brain Ingest Pipeline..." -ForegroundColor Cyan

if ($args.Count -eq 0) {
    python "$scriptDir\ingest.py" --all
} else {
    python "$scriptDir\ingest.py" @args
}

Write-Host "[*] Rebuilding Network Index (INDEX.md)..." -ForegroundColor Cyan
python "$scriptDir\graph_index.py" build

Write-Host "[+] Done. System is up to date." -ForegroundColor Green
