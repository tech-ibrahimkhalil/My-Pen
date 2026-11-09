# My Pen cross-platform test report

Tested version: 0.8.2, with portable test-runner updates.
Date: 28 October 2026 (Asia/Dhaka).

## Results actually obtained

| Platform/check | Result | Evidence limit |
| --- | --- | --- |
| Ubuntu 24.04.3, x86_64, Python 3.12.14, Qt/PySide6 6.12.0 | 79 tests passed | Qt offscreen backend; no graphical desktop |
| Windowed and overlay startup | Passed in the suite | Offscreen startup, not native overlay acceptance |
| Background/tray-mode startup | Passed separately | No real system tray available; fallback exercised |
| Windows startup registration logic | Mocked registry test passed | No Windows machine, registry or sign-in tested |
| Linux startup entry | Temporary-file creation/removal and Exec parsing passed | Real sign-in was not performed |
| macOS startup entry | Temporary plist creation/removal passed | No macOS machine or launchd execution tested |
| Native Ubuntu X11/Wayland desktop | Not tested | No DISPLAY, WAYLAND_DISPLAY or compositor |
| Native Windows 10/11 | Not tested | No Windows runner available |
| Native macOS | Not tested | No macOS runner available |

The local environment cannot certify support on all three operating systems.
Mocked startup logic is not equivalent to running the app on Windows or macOS.

## Changes made during testing

- Replaced two Linux-path assumptions in tests with platform-independent path handling.
- Smoke-test launches now use temporary INI preferences instead of normal user settings.
- Added scripts/test_platform.py and Windows/Unix test launchers.
- The test runner records machine/OS/Python/Qt versions, pass/fail results, timeouts,
  detailed logs and explicit skipped native tests. It does not install startup entries.

## Run on each actual platform

Install using README.md first. Export work and exit any running My Pen instance.

Windows: double-click test_windows.bat.

Ubuntu/Linux and macOS: run `sh test_unix.sh` from a graphical desktop terminal.

Manual alternative from the project directory:

```sh
python scripts/test_platform.py --gui-smoke
```

Use the project's .venv Python if `python` selects a different installation.
Without --gui-smoke the runner performs only headless checks. Native smoke checks
briefly open/close windowed, overlay and background modes; they still do not test
user interactions, desktop capture permissions or actual sign-in startup.

Results are saved in test-results/<system>_<architecture>.json and .log.
Included linux_x86_64 files are evidence from this run, not Windows/macOS results.

## Manual desktop acceptance required

| Check | Windows 10/11 | Ubuntu X11 | Ubuntu Wayland | macOS |
| --- | --- | --- | --- | --- |
| Pen/highlighter/erase, exact size, undo/redo and text | Pending | Pending | Pending | Pending |
| Tool switching, Shift shapes, toolbar always clickable | Pending | Pending | Pending | Pending |
| Glass toolbar/background and logo edge compositing | Pending | Pending | Pending | Pending |
| Ghost clicks reach another app | Pending | Pending | Experimental/unsupported integration | Pending |
| Screenshot crop/save/copy | Pending | Pending | Portal not implemented | Pending screen-recording permission |
| Tray hide/restore/exit retains work until exit | Pending | Pending; tray availability varies | Pending; tray availability varies | Pending |
| Enable startup, sign out/in, then disable and repeat | Pending | Pending | Pending | Pending OS approval |
| Physical Wacom/XP-Pen pressure and touch | Pending | Pending | Pending | Pending |

The current canvas targets the primary screen. Multi-monitor acceptance is not
claimed. Fading ink expires naturally while hidden. Editable session recovery is
not implemented, so a full exit discards drawings that were not exported.

## Local evidence

Offscreen suite: 79 tests, 13.257 seconds.

Background smoke: 0.488 seconds, exit code 0.
