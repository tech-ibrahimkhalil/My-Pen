# Graphics-pad starting-point ring fix

This patch is based on the supplied My Pen v0.8.2 Final Pack.

The Windows drawing canvas now responds to WM_TABLET_QUERYSYSTEMGESTURESTATUS
by disabling press-and-hold, pen tap/barrel feedback and flick gestures.
This targets the Windows ring and hold delay at the start of a stroke.
It does not change system-wide pen settings, pressure handling, or Linux/macOS input.

## Run the update

1. Exit the previous My Pen from its tray menu.
2. Extract this complete ZIP into a fresh folder.
3. Run setup_windows.bat, then use run_windows.bat for subsequent launches.
4. Test a short stroke and hold the pen tip briefly on the drawing canvas.
   Check that the ring no longer appears and strokes begin immediately.
5. Also test pressure, erasing, Ghost Mode and toolbar clicks.

This is a source package, not a rebuilt EXE. An existing installed EXE will not
be updated by extracting this ZIP; launch the supplied scripts instead.

Native Windows graphics-pad verification is still required. A tablet driver's
own indicator may require a separate driver setting if it remains visible.

Reference: https://learn.microsoft.com/windows/win32/tablet/wm-tablet-querysystemgesturestatus-message

Validation: 82 automated tests passed on Linux with Qt offscreen, including
three new native-message regression tests. This does not verify actual
Windows pen visuals or hardware.
