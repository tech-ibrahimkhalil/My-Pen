# Pen / cursor switching patch

Based on v0.8.2 plus the graphics-pad feedback fix.

On Windows, mode switching now changes only the native click-through and
no-activate style bits. It preserves Qt's layered transparency and avoids
reapplying Qt window flags during normal switching. Other platforms apply
their two input flags in one update. The pen feedback-ring fix is included.

## Windows update

Exit the old app through the tray menu. Extract the complete ZIP into a fresh
folder and run setup_windows.bat. Subsequently use run_windows.bat.
This is source code with launch scripts, not an updated compiled installer;
launching an old installed EXE will still run the old code.

## Desktop validation still needed

Switch Pen / Cursor repeatedly over a browser or moving video. Verify no
black flashes, background clicks in Cursor mode, immediate drawing in Pen
mode, retained annotations and clickable toolbar. Test transparent, white,
black and glass backgrounds. In blackboard mode an intentionally black
background remains black; cursor switching does not change board selection.

Native Windows compositor / graphics-pad testing is not available in this
Linux workspace. This patch addresses the suspected transition mechanism;
it is not a claim that hardware flicker has been verified as eliminated.

Validation: 85 automated tests passed on Linux/Qt offscreen, including
mocked Windows style preservation, repeated switching and failure fallback.
