# Build My Pen V10.0 EXE and installer on Windows

This kit contains the latest V10.0 glass Developer card and earlier fixes.
It contains build scripts, NOT an already compiled Windows installer.

## 1. Install the two build tools

- Python 3.12 **Windows installer (64-bit)**: https://www.python.org/downloads/windows/
  Include the Python launcher (`py`). Select Add Python to PATH.
- Inno Setup **6**: https://jrsoftware.org/isdl.php
  Install to the default location. No script wizard is needed.

Close My Pen before building. Internet is needed for the first dependency install.

## 2. Extract this ZIP

Right-click the ZIP and choose Extract All. Open the extracted My_Pen folder.
For example: C:\MyPenBuild\My_Pen. Do not run the script inside the ZIP viewer.

## 3. Build both outputs

Double-click **build_windows.bat** and leave the command window open.
The script creates a separate .build-venv, installs dependencies, creates an ICO,
bundles Python/Qt/images/docs, runs a short windowed startup check and compiles
the installer. It pauses with an error if any build stage fails.

Output paths inside the My_Pen folder:

- `dist\My Pen\My Pen.exe` — application executable.
- `installer-output\MyPen-Setup-10.0-x64.exe` — installer to distribute.

The application executable depends on the other files in its dist folder.
Do not copy My Pen.exe alone. Share the installer, or ZIP the entire dist\My Pen
folder for a portable copy. Installed users do not need Python or Inno Setup.

## 4. Test the installer

Run MyPen-Setup-10.0-x64.exe. Follow Next / Install, optionally select the desktop
shortcut, and launch My Pen. It installs for the current user under
%LOCALAPPDATA%\Programs\My Pen and adds an uninstall entry.

Test drawing, all shape tools, Ghost Mode, toolbar crossings, screen capture,
Developer links, tray restore and Exit. If you opt into startup in the app,
sign out/in and check it. Uninstall via Windows Settings > Apps when required.
The installer does not silently enable startup.

## Troubleshooting

- `py` not recognized: rerun Python installation and include its launcher.
- Python 3.12 missing: install that version (64-bit), then retry.
- Inno Setup not found: install Inno Setup 6; for a custom location open CMD in
  the project folder, run `set "ISCC_EXE=D:\YourPath\ISCC.exe"`, then
  `build_windows.bat` in that same CMD window.
- Build failure: read the first error above the final message; save the output
  or send a screenshot. A stale installer is not evidence the new build passed.
- Windows may identify this self-built installer as an unknown publisher. The
  build kit does not sign executables. Public distribution requires a separate
  signing process if you want a verified publisher identity.

## Validation limits

The build configuration was prepared on Linux. Python syntax and source checks
can run here; Windows compilation, Inno Setup compilation and installation have
not run here. The script's smoke check confirms only startup, not full desktop
or graphics-pad compatibility.

References:
https://pyinstaller.org/en/stable/
https://jrsoftware.org/is6help/
