$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Ada perubahan staged sebelumnya. Review/commit atau unstage secara manual sebelum menjalankan helper.' }
    $files = Get-Content -LiteralPath (Join-Path $repo 'deploy\code-files.txt')
    foreach ($file in $files) {
        if (-not $file -or $file.StartsWith('#')) { continue }
        if ([IO.Path]::IsPathRooted($file) -or $file.Contains('..')) { throw 'Path allowlist tidak valid.' }
        if (-not (Test-Path -LiteralPath (Join-Path $repo $file) -PathType Leaf)) { throw "File kode tidak ditemukan: $file" }
    }
    git add --pathspec-from-file=deploy/code-files.txt
    if ($LASTEXITCODE -ne 0) { throw 'Git add gagal; periksa staging sebelum melanjutkan.' }
    git diff --cached --stat
    Write-Host 'Kode sudah staged. Review git diff --cached, lalu lakukan commit/push sendiri.'
} finally { Pop-Location }
