@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)
if not exist ".env" (
  echo ERROR: .env not found. Run setup_windows.bat and configure the database.
  pause
  exit /b 1
)
echo Starting Student Academic and Placement Management System...
echo Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop.
.venv\Scripts\python.exe -m flask --app run.py run --debug
pause
