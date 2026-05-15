@echo off
cd /d "%~dp0.."
echo Starting Bookmarked API from %CD%

findstr /C:"API_VERSION = \"multilingual-2\"" server.py >nul
if errorlevel 1 (
  echo ERROR: server.py in this folder is not the current API.
  pause
  exit /b 1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
  echo Stopping PID %%a on port 3000...
  taskkill /PID %%a /F >nul 2>&1
)

echo.
echo Open http://localhost:3000/health when you see "Running on" (should show "Version: multilingual-2")
echo.
python server.py
pause
