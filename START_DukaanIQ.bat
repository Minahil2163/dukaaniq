@echo off
setlocal
cd /d "%~dp0backend"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.10+ and try again.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creating DukaanIQ virtual environment...
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
pause
