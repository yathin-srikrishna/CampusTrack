@echo off
setlocal
cd /d "%~dp0"
echo === Student Academic and Placement Management System setup ===
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher 'py' was not found. Install Python 3.11 or newer and enable Add Python to PATH.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :error
)
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env from .env.example. Edit DATABASE_URL and SECRET_KEY before continuing.
)
echo.
echo Next: run sql\01_create_database.sql in MySQL Workbench, then edit .env.
echo Then run: .venv\Scripts\python.exe -m flask --app run.py init-db
echo Then run: .venv\Scripts\python.exe seed_demo.py
echo Then double-click run_windows.bat.
pause
exit /b 0
:error
echo ERROR: Setup failed. Check the message above, internet access, and Python installation.
pause
exit /b 1
