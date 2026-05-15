# Start the Bookmarked Flask API from this repo (multilingual-2+).
# Usage from repo root: .\scripts\start-api.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$marker = Select-String -Path (Join-Path $root 'server.py') -Pattern 'API_VERSION = "multilingual-2"' -Quiet
if (-not $marker) {
    Write-Error "server.py in $root does not look like the current API. Wrong folder?"
    exit 1
}

$on3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($on3000) {
    $pid = $on3000.OwningProcess | Select-Object -First 1
    Write-Host "Stopping process on port 3000 (PID $pid)..." -ForegroundColor Yellow
    Stop-Process -Id $pid -Force
    Start-Sleep -Seconds 1
}

Write-Host "Starting Flask from: $root" -ForegroundColor Cyan
Write-Host "After start, open: http://localhost:3000/health" -ForegroundColor Green
python server.py
