@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   AegisEdge ATC - Quick Start
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found on PATH.
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm not found on PATH.
  exit /b 1
)

if not exist "backend\requirements.txt" (
  echo [ERROR] Run this from the AegisEdgeProject root.
  exit /b 1
)

echo [1/3] Ensuring backend dependencies...
python -m pip install -r backend\requirements.txt -q
if errorlevel 1 (
  echo [ERROR] pip install failed.
  exit /b 1
)

echo [2/3] Ensuring frontend dependencies...
pushd frontend
if not exist "node_modules\" (
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    popd
    exit /b 1
  )
)
popd

echo [3/3] Starting API + UI...
echo   API  http://127.0.0.1:8000
echo   UI   http://127.0.0.1:5173
echo   Docs http://127.0.0.1:8000/docs
echo.
echo Close the two spawned windows ^(or Ctrl+C in each^) to stop.
echo.

start "AegisEdge API" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
start "AegisEdge UI" cmd /k "cd /d "%~dp0frontend" && npx vite --host 127.0.0.1 --port 5173"

echo Opened API and UI terminals.
endlocal
