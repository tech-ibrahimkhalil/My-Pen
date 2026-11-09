# Menu alignment, shape scrollbar and stroke preview update

- All text menu rows use the same left-aligned text column, including the
  version heading, Hide to tray and Exit My Pen. Rows remain fully clickable.
- Attached menu sizing includes frame and layout margins. Short shape flyouts
  have no scrollbar and do not clip their buttons. Long menus/settings retain
  scrolling when needed to stay within toolbar height.
- Size dots are rendered at their actual logical pixel diameter, without
  toolbar-icon downscaling. Widths larger than the 22-pixel toolbar icon area
  show a number rather than an undersized dot. The size tooltip gives pixels.
  Stylus pressure can still make freehand ink thinner; shapes use selected width.

Includes the earlier Windows cursor-switch and pen-feedback fixes.

Update: exit My Pen from the tray, extract into a fresh folder, and run
setup_windows.bat. Later launches use run_windows.bat. This is a source package,
not a compiled installer. Linux/macOS setup instructions remain in README.md.

Validation: 88 automated tests passed on Linux/offscreen. Additional checks
verified no shape scrollbar or button clipping, and exact dot diameters for
2, 4, 8, 14 and 20 pixels. Menu and shape flyout renders were visually inspected.
Windows/macOS native desktop checks remain pending.
