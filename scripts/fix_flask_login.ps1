$ErrorActionPreference = 'Stop'

# Run this script from the project root in Windows PowerShell.
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Creating project virtual environment...'
    py -m venv .venv
}

$python = Resolve-Path '.venv\Scripts\python.exe'
Write-Host 'Installing project dependencies into the project virtual environment...'
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

Write-Host 'Checking Flask-Login import...'
& $python -c "import flask_login; print('SUCCESS: Flask-Login is installed in', __import__('sys').executable)"

Write-Host ''
Write-Host 'Next: in VS Code press Ctrl+Shift+P, select Python: Select Interpreter, and choose .venv\Scripts\python.exe.'
Write-Host 'Then run Developer: Reload Window.'
