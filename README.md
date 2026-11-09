> **GitHub repository update:** See [GITHUB_UPDATE_GUIDE.md](GITHUB_UPDATE_GUIDE.md) to push the V10.0 source update and run GitHub Actions.

> **Windows installer build:** See [WINDOWS_BUILD_GUIDE.md](WINDOWS_BUILD_GUIDE.md). Install Python 3.12 x64 and Inno Setup 6, then run build_windows.bat. No compiled installer is included.

> **V10.0 appearance update:** Developer card now uses translucent ice-blue glass styling, rounded white edging and translucent link buttons. This is a glass-style tint, not native desktop background blur.

# My Pen V10.0

Current release: **V10.0**. Removed the version row from the main menu; version information remains in About My Pen. Includes all preceding toolbar and drawing fixes. Older release notes below are historical.

> **Toolbar update:** Menu icons, desktop-slide icon, normal shape pointer and continuous strokes beneath the toolbar. See [update notes](docs/UNDER_TOOLBAR_UPDATE.md).

> **Menu/size update:** Aligned menu text, scrollbar-free shape flyout and true-size stroke dots. See [update notes](docs/MENU_SIZE_FIX.md).

> **Menu/shape update:** Full-width menu clicks, clean flyout backgrounds and stronger Windows pen-feedback suppression. See [update notes](docs/MENU_SHAPE_FIX.md).

> **Cursor-switch patch:** Updated Windows Pen/Cursor switching to preserve the transparent drawing layer. See [update and test instructions](docs/CURSOR_BLINK_FIX.md).

> **Graphics-pad feedback patch:** Windows pen press-and-hold feedback is disabled on the drawing canvas. See [update instructions](docs/PEN_FEEDBACK_FIX.md). Native graphics-pad verification remains pending.

# My Pen — v10.0 

A native desktop annotation prototype using Python and PySide6 (Qt 6).
The v0.8.2 design uses a slim white floating toolbar, your supplied green pen-nib logo,
outlined icons, cyan active-tool highlights, and bottom quick-color blocks.
The software name is **My Pen**. Controls now use official Lucide SVG icons,
bundled locally and rendered with Qt SVG. No Node.js, icon fonts or network access
is needed to display them at runtime. Size dots remain functional width samples. The main icon
is a transparent PNG cutout of your supplied logo, bundled under
`images/app/my_pen_icon.png`. The green ring is retained; the gray square
background is removed. The original JPG remains as a reference asset.
One source tree targets Windows, Ubuntu/Linux, and macOS. This is the first
development stage, not a completed replacement for Epic Pen.

## 1. Requirements

- Python 3.10 or newer (Python 3.12 recommended for this initial setup).
- Internet access for the initial dependency installation.
- A normal graphical desktop. Linux servers without a display need offscreen testing.
- On Linux, X11/Xorg is the initial desktop-overlay target. Wayland defaults to
  a normal drawing window; native Wayland overlay integration remains future work.

Extract the ZIP before running commands. Open a terminal in this folder (the
folder containing `main.py`). No administrator privileges are required for pip.

## 2. Windows setup

**Quick route:** install Python, then double-click `setup_windows.bat` inside
this extracted folder. It creates `.venv`, installs requirements, and starts
My Pen. For future launches, double-click `run_windows.bat`.

**Manual route:** use the commands below.

Install Python from https://www.python.org/downloads/ if necessary.
In PowerShell or Command Prompt, run:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

After installation, double-click `run_windows.bat` to launch again.
To use a normal window for an initial test:

```powershell
.venv\Scripts\python.exe main.py --windowed
```

## 3. Ubuntu/Linux setup

Install Python's virtual environment support if it is missing:

```bash
sudo apt update
sudo apt install python3-venv
```

Create the environment, install dependencies, and launch:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Later launches can use `sh run_unix.sh`.

If Qt reports a missing `xcb` dependency on Ubuntu, install the named library.
Common dependencies include:

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-xinerama0
```

Check your session with `echo "$XDG_SESSION_TYPE"`. On Wayland, the app
deliberately opens a normal whiteboard window by default. Where your system
offers it, an Xorg/X11 login session is the initial overlay route. You can
try `.venv/bin/python main.py --overlay` on Wayland, but positioning, stacking,
and click-through behaviour are experimental. It is not full Wayland support.
Do not assume forcing XWayland alone solves overlays above native Wayland apps.

## 4. macOS setup

Install Python 3.10+ from https://www.python.org/downloads/macos/ if necessary.
In Terminal, inside this project folder:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Later launches can use `sh run_unix.sh`. Use `--windowed` for a normal canvas.
This first version does not record your screen or install global input hooks.
Later screen-capture and global-input features may require macOS permissions.
Spaces, full-screen apps, and tablet drivers still require native Mac testing.

## 5. Use the compact toolbar

The toolbar starts on the left side. Hover over an icon to see its tooltip.
Drag the green nib at the top to move the toolbar. The name remains available in window titles and tooltips; the label is hidden to keep the toolbar compact.
Use the **clipboard menu**, or right-click the nib, for **About / Help / Settings / Exit My Pen**.
**The eye button** now collapses the tools to the nib and a small cyan closed-eye
button. No other tool controls or reserved full-height hit area remain visible. Click that button to reopen, preserving permanent drawings. The hidden
canvas does not intercept desktop clicks. Right-click the nib for **Quit My Pen**
when you want to terminate the application.
Click the center of a tool button to select it. Only the small bottom-right
corner triangle (or a right-click) opens its options. Options are child panels
inside the same toolbar window, opening on the side with available space.

| Icon / control | Action |
| --- | --- |
| Eye | Hide/show annotations without deleting them |
| Cursor | Toggle Ghost Mode; corner menu selects normal/highlighted cursor |
| Stopwatch | Toggle fading ink; corner menu selects permanent or 1/3/5/10 seconds |
| Pen | Draw with the last selected ink tool |
| Pen corner menu | Choose Pen, Highlighter, or Text |
| Line | Draw with the last selected shape tool |
| Line corner menu | Choose Line, Arrow, Rectangle, or Ellipse |
| Eraser | Erase entire strokes/objects |
| Dot | Choose a pen size visually: 2, 4, 8, 14 or 24 px; custom width/text size in Settings |
| Undo arrow | Undo; use its corner menu for Redo |
| Trash | Clear immediately without confirmation; Undo restores the drawings |
| Board | Choose Transparent overlay, Whiteboard, or Blackboard |
| Camera | Capture an area of the desktop; then choose Save, Copy, or Cancel |
| Clipboard menu | About, Help, Settings, Copy canvas, Export canvas PNG, Colors, Exit My Pen |
| Cyan / yellow / pink / black squares | Choose a quick color |
| Large current-color block | Open the vertical side color bar; RGB opens the custom picker |

- Overlay mode starts in **Ghost Mode** so the desktop remains clickable.
  Click the cursor icon or choose a drawing tool to start drawing.
- The independent toolbar stays interactive when the canvas is click-through.
- In `--windowed` mode, Ghost is a non-drawing preview, not native click-through.
- Pen pressure is used when the graphics-tablet driver supplies Qt tablet events.
- Pen, highlighter, lines and shape outlines use the selected stroke width.
  The size dot updates when you choose a size. Tablet pressure can reduce the pen
  width below the selected maximum. Sizes use Qt logical pixels and follow OS scaling.
- Hold Shift for squares/circles or horizontal/vertical lines/arrows.
- Text is a single-line note with its baseline at the clicked position.
- Selecting a drawing tool reveals hidden ink again.
- Export/copy includes the annotations even when the eye has temporarily hidden
  them. Transparent mode exports transparent PNG pixels; white/black modes include
  the canvas background. The toolbar never appears in exported canvas images.
- Fading mode affects new annotations only. It fades each stroke near the end of
  its selected lifetime, then removes it. Existing permanent ink remains permanent.
- Highlighted cursor draws a yellow ring. It works in Ghost Mode without taking
  clicks; it is a presentation effect and is excluded from canvas export/copy.
- File dialogs use
  the existing modal fix. Help, About, settings, colors and option menus are now
  attached child panels in the toolbar window. Opening them does not recreate the
  drawing overlay or toggle Ghost Mode. Longer content scrolls within the bar height.
- The eye button collapses the app; permanent drawings stay in memory.
  Export before using Quit My Pen. Editable sessions and autosave are not implemented yet.

### Camera / screenshot workflow

1. Click the camera. The toolbar and live overlay are hidden briefly.
2. Drag a rectangle over the frozen desktop preview. The outside area is dimmed.
3. Use the **folder** icon to save the selected area as PNG (Desktop is the initial folder).
4. Use the **clipboard** icon to copy the selected image and return to drawing.
5. Use **X**, Esc, or right-click to cancel. My Pen returns afterward.

Visible annotations are composited into the screenshot; the toolbar, crop controls,
and cursor highlight are excluded. Crop coordinates account for display scaling.
Capture currently targets the canvas's monitor (the primary monitor in this release).
On macOS, allow screen recording if required and restart the app if prompted.
Native Wayland camera capture is not implemented yet; it reports this clearly and
restores the toolbar. X11/Xorg is the initial Linux capture route. Protected or
exclusive full-screen content may not be available to the desktop capture API.

Canvas-only export remains available from the clipboard menu and Ctrl/Cmd+S.

### Initial shortcuts

| Key | Action |
| --- | --- |
| P / H / E | Pen / Highlighter / Eraser |
| L / A / R / O / T | Line / Arrow / Rectangle / Ellipse / Text |
| G | Toggle Ghost Mode |
| Ctrl+Shift+F | Toggle fading ink (application-local) |
| Esc | Enter Ghost Mode |
| Ctrl+Z on Windows/Linux; Cmd+Z on Mac | Undo |
| Platform standard redo shortcut | Redo |
| Ctrl+S on Windows/Linux; Cmd+S on Mac | Export PNG |

Shortcuts are now customizable in Settings, and remain application-local rather than global. When another app
has focus, use the cursor icon in My Pen's toolbar to return to drawing.
The shortcut printed in the reference screenshot is not implemented as a global
shortcut in this version.

## 6. What is implemented

Pen, highlighter, individual-stroke eraser, clear, Ghost Mode toggle, two palettes,
custom colors, stroke width, single-line text and font size, four shape tools,
white/black backgrounds, undo/redo, a compact draggable toolbar with tool menus,
annotation visibility, fading ink, highlighted cursor, horizontal icon flyouts,
Settings/About menus, desktop region screenshot Save/Copy/Cancel, collapse/reopen,
canvas clipboard copy, customizable app-local shortcuts,
PNG annotation export, and saved color/width/font/toolbar-position preferences.

Mouse input, pressure data from Qt tablet events, and basic single-finger touch
handling are implemented. Real Wacom/XP-Pen hardware, pressure drivers, touch,
and palm rejection are not certified by the headless tests.

See `ROADMAP.md` for all requested and proposed features and their stages.

## 7. Validate your installation

```bash
python -m unittest discover -s tests -v
python main.py --windowed --smoke-test
```

Use the Python executable inside your `.venv` in place of `python` if the virtual
environment is not activated. Automated tests use Qt's offscreen backend.
For headless smoke testing on Linux:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python main.py --windowed --smoke-test
```

### Manual checks required on each real OS

1. Open a browser/editor and launch the overlay. Confirm the toolbar stays visible.
2. Click the cursor icon to leave Ghost Mode, then test drawing and tool menus.
3. Enable Ghost Mode. Click and type in the browser underneath; keep the marks visible.
4. Return to drawing using the toolbar. Confirm there is no input lockout.
5. Test undo/redo, eraser, white/black board, and PNG export.
6. Draw a line, click the eye button, then click the small closed-eye button.
   Confirm the compact toolbar and drawing return without a quit prompt.
7. Export your drawing, then choose Exit My Pen. It should quit immediately without a prompt.
8. Test the camera: select an area, save, paste a copied capture, and cancel.
   Test Clear, Text, Settings, About, export and custom color dialogs.
7. Choose fading ink 3 seconds, draw, and verify it disappears; old permanent ink stays.
8. Test cursor highlight and the horizontal icon menus.
9. Test a tablet/touchscreen if available; check pressure and duplicate input.
10. Test at 100%, 150%, and 200% display scaling as available.
11. Test macOS Spaces / full-screen apps and Linux desktop-specific stacking.

## 8. Project layout

| Location | Contents |
| --- | --- |
| main.py | Application entry point |
| setup_windows.bat | First-time Windows installation |
| run_windows.bat | Normal Windows launch |
| debug_windows.bat | Windows launch with error output |
| run_unix.sh | Linux/macOS launch |
| requirements.txt | Python dependencies |
| screenpen/ | Application source code |
| images/app/ | Main logo, original logo and developer portrait |
| images/icons/lucide/ | Toolbar icons and their license/source metadata |
| images/icons/brands/ | Developer social icons and their license/source metadata |
| images/previews/ | All UI preview images |
| docs/ | Changelog, roadmap, validation and asset/license notes |
| tests/ | Automated checks |

Keep these folders together. The app resolves image paths from its installation
folder, so launching from a different working directory still loads the artwork.


The current overlay covers the primary screen only. Drawings stay at fixed
screen coordinates as background apps move or scroll. Annotating a video-call
window does not automatically send drawings to other participants. Native
screen sharing must include the overlay and needs separate testing.

## 9. Packaging later

This deliverable is runnable source, not prebuilt EXE/AppImage/DMG installers.
Build and test distributions on each target OS using Qt's deployment tooling.
Windows, Linux, and macOS require separate packages, even with shared source.
Choose the final distribution/license policy and review Qt/PySide license
obligations before publishing installers.

Official references:

- https://doc.qt.io/qtforpython-6/
- https://doc.qt.io/qtforpython-6/deployment/index.html
- https://doc.qt.io/qt-6/qt.html
- https://doc.qt.io/qt-6/application-windows.html
- https://doc.qt.io/qtforpython-6/PySide6/QtGui/QTabletEvent.html

## Upgrade from earlier versions on Windows

Close the old app before launching this version. If a previous dialog is already
stuck behind the overlay, Alt+F4 may dismiss it. If it remains blocked, open Task
Manager, identify the Python process running the old My Pen instance and end only
that process; unsaved annotations in that instance will be lost.

Extract this ZIP into a new folder, then run `setup_windows.bat`. For an already
configured installation, replace `main.py` and the entire `screenpen` folder
(including `assets`) together; keep your existing `.venv`, then use
`run_windows.bat`. Do not replace only app.py: this version has new modules/assets.

This deliverable remains Python source, not a packaged Windows EXE. The custom
icon is used by My Pen's toolbar and Qt windows; Windows may still show the
Python interpreter identity in some shell/taskbar surfaces until native packaging.



## Cross-platform testing

See docs/CROSS_PLATFORM_TEST_REPORT.md for actual results and limits. Run
`test_windows.bat` on Windows, or `sh test_unix.sh` on Ubuntu/macOS after setup.
These launch the automated suite plus native startup smoke checks when a desktop
is available, and save logs/JSON under test-results/. Native interactive acceptance
is separate; the included report does not claim Windows/macOS were executed here.
