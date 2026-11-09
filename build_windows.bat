@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .build-venv
if errorlevel 1 goto fail
".build-venv\Scripts\python.exe" -m pip install -r requirements.txt "pyinstaller>=6.11,<7" pillow
if errorlevel 1 goto fail
".build-venv\Scripts\python.exe" scripts\build_windows.py
if errorlevel 1 goto fail
echo.
echo Build complete. Open the installer-output folder.
pause
exit /b 0
:fail
echo.
echo Build failed. Read the error above. Python 3.12 x64 and Inno Setup 6 are required.
pause
exit /b 1
