# Menu and shape-tool patch

Based on v0.8.2 with the previous pen-feedback and cursor-switch patches included.

- Text menu buttons expand across the full row, including Settings.
- Shape flyouts retain the opaque SidePanel style instead of an ineffective
  QMenu style; their content background is explicitly white.
- The translucent toolbar clears its dirty background before painting to
  avoid stale pixels after panel resize/movement.
- On Windows, canvas creation/show applies both the tablet service property
  and SetWindowFeedbackSetting for pen barrel, tap, double-tap, press-and-hold
  and right-tap visuals. This applies to pen and all shape tools. The native
  gesture-message handler remains as a second path. Pressure input is unchanged.

Exit the old app from the tray, extract into a fresh folder, and launch
setup_windows.bat. Use run_windows.bat afterwards. This ZIP is source with
launch scripts, not a rebuilt EXE or installer.

Validation: existing 85 headless tests passed, plus 3 new checks for far-right
Settings clicks, opaque flyout borders and native pen-feedback configuration.
Windows hardware/compositor behavior is still unverified. Test all four shape
tools with the graphics pad, including holding the tip down before dragging;
open and close the shape menu against light and dark desktop backgrounds.

API references:
https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowfeedbacksetting
https://learn.microsoft.com/windows/win32/tablet/wm-tablet-querysystemgesturestatus-message
