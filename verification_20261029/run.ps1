param(
  [string]$Python = 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
  foreach ($stage in 'environment','label_stats','audio_features','coach_features','proposal_analysis') {
    & $Python "$PSScriptRoot/reproduce.py" $stage
    if ($LASTEXITCODE -ne 0) { throw "Failed: $stage" }
  }
  foreach ($script in 'audit.py','compare.py','make_figure.py','build_reports.py') {
    & $Python "$PSScriptRoot/$script"
    if ($LASTEXITCODE -ne 0) { throw "Failed: $script" }
  }
  node "$PSScriptRoot/build_web.mjs"
  if ($LASTEXITCODE -ne 0) { throw 'Failed: website build' }
} finally { Pop-Location }
