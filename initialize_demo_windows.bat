@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Python environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)
if not exist ".env" (
  echo ERROR: .env not found. Run setup_windows.bat and configure DATABASE_URL first.
  pause
  exit /b 1
)
echo This creates missing tables and seeds the 30 fictional demo students.
echo Run this only once on a fresh demo database.
choice /M "Continue"
if errorlevel 2 exit /b 0
.venv\Scripts\python.exe -m flask --app run.py init-db
if errorlevel 1 goto :error
.venv\Scripts\python.exe seed_demo.py
if errorlevel 1 goto :error
echo.
echo SUCCESS: Demo data has been inserted.
echo Student credentials: instance\demo_credentials.csv
echo College admin credentials: instance\demo_admin_credentials.csv
echo Start the site by double-clicking run_windows.bat.
pause
exit /b 0
:error
echo ERROR: Initialization or seeding failed. Read the error above; do not repeatedly rerun the seed script.
pause
exit /b 1
