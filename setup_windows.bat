@echo off
setlocal
title My Pen - Setup
cd /d "%~dp0"
echo My Pen - Windows setup
py -3 --version
if errorlevel 1 (
  echo Python was not found. Install Python 3.12 from python.org, then try again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 (
    echo The virtual environment could not be created.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependencies could not be installed. Check the error above and your internet connection.
  pause
  exit /b 1
)
echo Starting My Pen. Use the cursor icon to switch between drawing and Ghost Mode.
start "My Pen" ".venv\Scripts\pythonw.exe" main.py
exit /b 0
