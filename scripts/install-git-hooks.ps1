Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  git config core.hooksPath .githooks
  Write-Host "Git hooks enabled: .githooks" -ForegroundColor Green
  Write-Host "pre-commit will run Prettier and lint before each commit."
} finally {
  Pop-Location
}
