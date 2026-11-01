param([Parameter(ValueFromRemainingArguments = $true)][string[]]$BrainArgs)
$ErrorActionPreference = 'Stop'
$candidates = @()
if ($env:SECOND_BRAIN_PYTHON) { $candidates += $env:SECOND_BRAIN_PYTHON }
$candidates += (Join-Path $PSScriptRoot '.venv\Scripts\python.exe')
foreach ($name in @('python.exe', 'python3.exe')) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
}
$candidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    try {
        $version = & $candidate --version 2>$null
        if ($LASTEXITCODE -ne 0 -or "$version" -notmatch 'Python 3\.(\d+)\.') { continue }
        if ([int]$Matches[1] -lt 10) { continue }
    } catch { continue }
    & $candidate (Join-Path $PSScriptRoot 'tools\brain.py') @BrainArgs
    exit $LASTEXITCODE
}
Write-Host 'Python 3.10+ belum ditemukan. Instal Python atau atur SECOND_BRAIN_PYTHON ke path python.exe.'
exit 1
