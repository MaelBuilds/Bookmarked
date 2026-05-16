# Run deterministic checks before deploying Bookmarked.
# Usage from repo root: .\scripts\predeploy.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$previousProvider = $env:AI_PROVIDER
try {
    Write-Host 'Running backend tests with fake AI provider...' -ForegroundColor Cyan
    $env:AI_PROVIDER = 'fake'
    pytest
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Host 'Building frontend production bundle...' -ForegroundColor Cyan
    Set-Location (Join-Path $root 'frontend')
    npm run build
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Set-Location $root
    if ($null -eq $previousProvider) {
        Remove-Item Env:\AI_PROVIDER -ErrorAction SilentlyContinue
    }
    else {
        $env:AI_PROVIDER = $previousProvider
    }
}
