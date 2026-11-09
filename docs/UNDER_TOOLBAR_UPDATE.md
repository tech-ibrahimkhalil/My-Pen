# Menu icons and drawing beneath the toolbar

- Added icons to My Pen version (app logo), Hide to tray (down arrow into tray)
  and Exit My Pen (power).
- Transparent desktop mode now uses a monitor containing a slide/window icon.
  The three new outline icons are original assets in images/icons/custom.
- Line, arrow, rectangle and ellipse use the normal system arrow pointer.
- A stroke begun on the canvas continues behind the toolbar instead of ending
  when it reaches the toolbar. Hidden points remain in the drawing and appear
  when the toolbar moves. A new press on the toolbar still operates its buttons.
  The toolbar remains in front, so ink does not paint on top of its controls.

Includes the earlier pen-feedback, cursor-switch, menu and size-preview fixes.

Exit the old app from its tray menu. Extract the full ZIP into a fresh folder
and run setup_windows.bat. Later launches: run_windows.bat. This is a source
package, not a rebuilt executable. Linux/macOS setup remains in README.md.

Windows test: draw a continuous stroke across the toolbar, release, then drag
its logo aside. The covered portion should appear; confirm toolbar clicks still
work. Test with both mouse and graphics pad. Native Windows pen capture and
compositor behavior remain unverified in this Linux/headless environment.

Validation: 88 headless automated tests passed, including updated shape
pointer checks, continuous stroke storage under controls, protected initial
clicks and application startup in overlay/windowed modes.
