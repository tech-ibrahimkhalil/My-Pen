# My Pen v0.8.2

- Group all images under images/app, images/icons and images/previews.
- Group supporting documents under docs; retain easy launchers at project root.
- Update runtime asset paths and documentation for the organized layout.
- Expand About My Pen with Engr Ibrahim Khalil credit, tagline, purpose and features.
- Keep About attached, bounded and scrollable.

# My Pen v0.8.1

- Add Developer directly under About My Pen, also available in the logo menu.
- Add an attached blue gradient card matching the supplied reference, with supplied photo.
- Add all ten supplied social/contact links; Gmail uses mailto.
- Bundle local social icons and preserve the supplied photo unchanged.
- 79 regression tests passed; separately checked layout and all ten exact link dispatches.

# My Pen v0.8.0

- Remove the exit confirmation, including when drawings are present.
- Add saved glass transparency controls for toolbar/panels and canvas backgrounds.
- Add system tray Show, Hide, Settings and Exit, without balloon notifications.
- Preserve drawings on hide; fall back to the collapsed bar when no tray is available.
- Ask once in an attached panel before enabling user sign-in startup.
- Add removable per-user Windows Run / Linux XDG / macOS LaunchAgent registration.
- Launch Windows normally through pythonw; retain debug_windows.bat for error output.
- 79 offscreen tests passed; native tray, sign-in and compositing remain unverified.

# My Pen v0.7.2

- Remove the binary canvas hole under the logo to improve antialiased edges on black.
- Simplify inline text placeholder to "Enter text".
- Dismiss attached panels on outside mouse/tablet/touch press and application deactivation.
- Preserve inside-panel editing and toolbar menu toggling.
- 71 offscreen tests pass; native Windows composition and focus need acceptance testing.

# My Pen v0.7.1

- Set the third background preset and blackboard icon fill to pure #000000.
- Preserve canvas background beneath transparent toolbar gutters/logo corners.
- Keep native input holes limited to solid controls, while blocking ink over the full toolbar.
- Explicitly keep toolbar/rail backgrounds transparent and add a subtle edge shadow.
- 69 automated tests passed; black/custom-board renders and gutter pixels checked offscreen.
- Native Windows rendering/input still requires testing.

# My Pen v0.7.0

- Add custom canvas background RGB/HEX through the board palette icon.
- Eye now collapses the full toolbar; closed eye restores it and the canvas.
- Embed RGB/HEX and quick-color editing beside the toolbar.
- Exclude toolbar/panels from the drawing overlay mask, painting and gesture input.
- Add persisted custom fading time from 1 to 3600 seconds in Settings.
- Replace Close toolbar in the main menu with Exit My Pen.
- Replace the text dialog with inline canvas entry; suspend tool shortcuts while typing.
- Match pen/highlighter/eraser cursors to selected tools; keep shape crosshairs.
- 69 offscreen tests pass; native Windows input/stacking remains to be tested.

# My Pen v0.6.0

- Remove the logo's gray background while retaining the green round ring.
- Remove Clear confirmation; keep Undo.
- Embed menus, colors, settings and information in the toolbar's native window.
- Cap panels to white-strip height, scroll long content, and remove gaps.
- Collapse to only logo and closed-eye reopen control; shrink the input mask too.
- Reduce dropdown hit targets to the corner; repeated tool switching is tested.
- Update native input-mode flags without recreating the full-screen widget.
- Cache completed ink and pending pen segments; stop idle timers and limit dirty regions.
- Cache mark geometry and prune expiry history only after actual expiry.
- 62 offscreen regression tests passed; native Windows responsiveness requires testing.

# My Pen v0.5.0

- Replace tool controls with official Lucide SVG icons; retain the supplied app logo.
- Bundle the selected SVG assets, original ISC license and package/source metadata.
- Add a narrow vertical color bar beside the toolbar.
- Replace modal Settings with an attached scrollable side panel and pink section headings.
- Add real per-tool sizing, wheel sizing, editable quick colors, screenshot destination
  settings, editable app-local hotkeys, duplicate detection, disable and reset controls.
- Persist supported preferences immediately; restore input mode after panels close.
- Keep dialogs above the canvas while temporarily suspending visible side panels.
- 50 automated checks passed; Windows/Linux/macOS native acceptance remains ongoing.

# My Pen v0.4.0

- Compact toolbar calibrated to the supplied Epic Pen screenshots.
- Exact selected width for pen, highlighter and shape ink; dynamic size indicator.
- Close toolbar collapses; closed-eye button restores tools and permanent drawings.
- Separate Quit My Pen action in the logo context menu.
- Camera captures a desktop region with Save / Copy / Cancel controls.
- HiDPI region cropping and capture cancellation/state restoration.
- Keep annotation-only PNG export in the clipboard menu.
- 38 offscreen tests, including synthetic screenshot crop/save/copy checks.

# My Pen v0.3.0

- Use the user-supplied green nib image as the main toolbar/app/window icon.
- Add horizontal icon flyouts matching the supplied examples.
- Add permanent and 1/3/5/10-second fading ink, with expiry and undo-history cleanup.
- Add normal/highlighted cursor selection; cursor highlight works in Ghost Mode.
- Add visual pen-size presets (2/4/8/14/24 px) and a Settings dialog.
- Add About / Help / Settings / Copy canvas / Colors / Close to the clipboard menu.
- Fix modal prompts appearing behind the drawing layer: suspend the overlay,
  set ApplicationModal before applying topmost, and restore after accept/cancel.
- Apply the dialog fix to exit, clear, text, color, PNG export, Help and Settings.
- Pass 29 offscreen automated checks, including real dialog button clicks.

# My Pen v0.2.0

- Renamed the application, canvas, export files, help, and settings to My Pen.
- Replaced the wide dark panel with a slim white reference-inspired toolbar.
- Added original scalable outline icons, cyan selected states, subtle shadow,
  a black nib drag handle, and the MY PEN label.
- Grouped ink, shapes, redo, board modes, widths and full palettes into menus.
- Added hide/show annotations, four instant colors, and a current-color block.
- Added annotation/board image copy to clipboard (not desktop screenshot capture).
- Added setup_windows.bat for first-time Windows installation.
- Retained the shared Python/Qt source and previous drawing features.
- Passed 20 offscreen automated tests. Native OS and tablet acceptance remains.

This is a UI update to Stage 1. Screenshot Crop, global configurable shortcuts,
editable sessions and remaining classroom tools continue on the roadmap.
