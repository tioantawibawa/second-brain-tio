param([switch]$Push)
$ErrorActionPreference = 'Stop'
if ($Push) { & "$PSScriptRoot\brain.ps1" sync --push }
else { & "$PSScriptRoot\brain.ps1" sync }
exit $LASTEXITCODE
