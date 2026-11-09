@echo off
title My Pen
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run setup_windows.bat to install My Pen dependencies.
  pause
  exit /b 1
)
start "My Pen" ".venv\Scripts\pythonw.exe" main.py %*
exit /b 0
