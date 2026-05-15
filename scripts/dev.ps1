# Start Flask (API) and Vite (UI with hot reload) for local frontend development.
# Usage from repo root: .\scripts\dev.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not (Test-Path '.env')) {
    Write-Warning '.env not found. Copy .env.example to .env and add your GitHub token.'
}

Write-Host 'Starting Flask on http://localhost:3000 (new window)...' -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$root'; & '$root\scripts\start-api.ps1'"
)

Write-Host 'Starting Vite on http://localhost:5173 (this window)...' -ForegroundColor Cyan
Write-Host 'Edit React at :5173 — not :3000.' -ForegroundColor Yellow
Set-Location (Join-Path $root 'frontend')
npm run dev
