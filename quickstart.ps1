# AegisEdge ATC — start backend + frontend
# Usage:  .\quickstart.ps1
# Stop:   .\quickstart.ps1 -Stop

param(
    [switch]$Stop,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Stop-AegisEdge {
    Write-Host "Stopping AegisEdge processes on ports 8000 / 5173..."
    foreach ($port in 8000, 5173) {
        Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
            ForEach-Object {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            }
    }
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'uvicorn' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'vite' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
    Write-Host "Done."
}

if ($Stop) {
    Stop-AegisEdge
    exit 0
}

Write-Host "========================================"
Write-Host "  AegisEdge ATC - Quick Start"
Write-Host "========================================"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python not found on PATH."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm not found on PATH."
}

Stop-AegisEdge

if (-not $SkipInstall) {
    Write-Host "[1/3] Backend dependencies..."
    python -m pip install -r (Join-Path $Root "backend\requirements.txt") -q

    Write-Host "[2/3] Frontend dependencies..."
    Push-Location (Join-Path $Root "frontend")
    try {
        if (-not (Test-Path "node_modules")) {
            npm install
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[1-2/3] Skipping installs (-SkipInstall)"
}

Write-Host "[3/3] Starting API + UI..."
Write-Host "  API  http://127.0.0.1:8000"
Write-Host "  UI   http://127.0.0.1:5173"
Write-Host "  Docs http://127.0.0.1:8000/docs"
Write-Host "  Stop with: .\quickstart.ps1 -Stop"
Write-Host ""

$apiCmd = "Set-Location '$Root\backend'; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
$uiCmd  = "Set-Location '$Root\frontend'; npx vite --host 127.0.0.1 --port 5173"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCmd -WindowStyle Normal
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", $uiCmd -WindowStyle Normal

Write-Host "Spawned API and UI windows."
