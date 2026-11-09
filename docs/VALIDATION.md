# Validation of My Pen v0.8.2

Test environment: Linux container, Python 3.12, PySide6 / Qt 6.12.0,
`QT_QPA_PLATFORM=offscreen`. No native desktop compositor or physical input tablet
is available in this environment.

## Automated checks

Run `python -m unittest discover -s tests -v` from the project directory.

The suite covers:

1. Mouse press/drag/release creating a committed stroke.
2. Undo/redo and discarding a redo branch after a new edit.
3. Swept eraser hit detection across a thin line.
4. An empty eraser gesture preserving redo history.
5. An entire eraser gesture being undone in one step.
6. Clear-all recovery using undo.
7. Ghost mode blocking new drawing without deleting previous work.
8. Shift-constrained square geometry.
9. Exported PNG pixels, transparency, blackboard background and successful file write.
10. Highlighter self-overlap retaining consistent transparency.
11. Pressure values changing rendered pen thickness.
12. Rendering all shape types and text.
13. Returning from Ghost Mode via tool selection in the separate toolbar.
14. Normal-window application startup and automatic shutdown, with a timeout.
15. Overlay-code-path startup and automatic shutdown, with a timeout.

16. Eye visibility hiding ink without deletion; selecting a tool reveals it again.
17. Cursor toggle and all drawing-tool dropdown actions.
18. Palette expansion and quick-color selection.
19. Copying rendered canvas pixels to the clipboard.
20. Board switching preserving existing annotations.

21. Horizontal flyout buttons selecting tools and visual size presets.
22. Fade opacity timing, expiry and removal from undo/redo snapshots.
23. Fade settings leaving existing permanent ink unchanged.
24. Highlighted cursor preserving Ghost Mode and allowing drawing-mode return.
25. Exit with drawings quits without showing confirmation.
26. Modal Yes result and Ghost state restoration.
27. A canvas that was hidden before a modal remains hidden afterward.
28. Inline text acceptance, shortcut suspension and canvas visibility.
29. Bundled supplied main icon loading successfully.

30. Compact 48 px window / 34 px strip dimensions and collapse/reopen preservation.
31. Main menu Exit My Pen action calls the quit path.
32. Pen, highlighter and lines use the selected width, with updated size tooltip.
33. Screenshot capture setup hides/restores app windows and preserves annotations (synthetic screen).
34. HiDPI region cropping returns correct physical-pixel dimensions.
35. Empty/out-of-bounds crop handling.
36. Drag selection and clipboard copy produce the selected image.
37. Save selected region writes a valid PNG.
38. Esc cancellation emits one completion signal.

39. Vertical color sidebar selection and drawing/hotkey state restoration.
40. Settings panel controls update active behavior and saved preferences.
41. Separate tool widths survive switching between tools.
42. Wheel sizing obeys its setting and Ghost Mode.
43. Editable hotkeys reject duplicates, can be disabled, and reset to defaults.
44. Edited quick colors are used by the toolbar.
45. Switching/collapsing closes the active sidebar cleanly.
46. Modal dialog temporarily suspends and restores an open settings sidebar.
47. All bundled Lucide control mappings render non-transparent pixels.
48. Screenshot entire-selection/direct-folder saving writes a valid image.

49. Reset preferences retains drawings and rebuilds the settings panel.
50. Saved color/input/capture/hotkey preferences load in a fresh toolbar.

51. Repeated near-right-edge normal clicks select tools instead of opening menus.
52. Corner clicks open embedded options and selection switches tools.
53. Settings shares the toolbar native window, touches its edge and stays bounded.
54. All option menus fit inside the expanded rail height.
55. Collapsed state exposes only logo/reopen, with a matching short input mask.
56. Clear runs without a dialog and is undoable.
57. Logo PNG has transparent corners.
58. Fifty repeated cache lookups do not rerender completed strokes.
59. Idle timer stops; a stationary cursor highlight does not trigger repaints.
60. Expiry does not rebuild undo history before an actual expiry.
61. Shift press/release updates a pending line constraint.
62. Twenty Ghost/draw cycles preserve the native window ID and input flags.

**Result: all 79 automated tests passed.**

The reference-inspired toolbar and popup menus were also rendered offscreen and visually checked
for clipping, readable controls, palette layout and shape rendering.

## What these checks do not prove

- Native click-through delivery to another application on Windows, X11 or macOS.
- Native always-on-top behaviour or macOS Spaces / exclusive full-screen apps.
- Real tablet drivers, Wacom / XP-Pen model compatibility, touch or palm rejection.
- Mixed-DPI multi-monitor behaviour (multi-monitor support is not implemented yet).
- Native Wayland overlay support (experimental only; defaults to windowed mode).
- Native desktop sampling/permissions/compositor timing: screenshot tests use synthetic images.
- Global hotkeys, editable sessions or the remaining roadmap features.

Qt offscreen warnings about `raise()` and `propagateSizeHints()` are expected:
the test backend does not provide a real desktop window manager.

Run the manual OS checks in README.md before treating a target platform as accepted.

## Dialog fix evidence

The regression test opens the real QMessageBox in a nested Qt event loop, sends a
mouse click to its No button, and verifies that the close request was cancelled,
the canvas was hidden while the prompt was open, and the canvas/annotations were
restored. It also verifies ApplicationModal and WindowStaysOnTopHint at runtime.
Qt's QMessageBox.setWindowModality resets its flags, so topmost is set afterward.
Native Windows stacking still needs the manual test in README.md.

## Visual checks

Rendered and checked the expanded 48 × 446 toolbar, collapsed 48 × 78 state,
and synthetic screenshot selection including folder/copy/cancel controls.
Real Windows screenshot capture and macOS permissions must still be tested on those OSes.

## v0.6.0 visual and dependency checks

Checked the vertical color bar, complete settings panel, bottom Hotkeys section,
and Lucide tool controls via offscreen Qt renders. Lucide Static 1.62.0 was fetched
from its npm distribution and verified against its published SHA-512 integrity
value before selected SVGs and its license were bundled. The application does not
need npm or a live CDN to render icons. Native OS integration still requires the
manual checks in README.md.

## v0.6.0 local performance evidence

Linux offscreen Qt 6.12, 1920 × 1080 canvas; 150 pen strokes / 22,500 samples:
initial cache construction 187.57 ms; 200 subsequent cache lookups 0.048 ms.
A separate 1,000-point incremental pending-pen update loop took 25.26 ms.
These are local algorithm/cache timings, NOT native rendering FPS or a Windows
latency measurement. The first full rebuild can still take time on a large drawing.

Visually checked the transparent circular logo, attached settings/color/ink menus,
and collapsed logo/closed-eye state. Verified Settings is a child widget, not a
native window, with 398 px height inside the 446 px expanded toolbar.
The offscreen backend does not implement native window masks/stacking; perform the
manual Windows checks for actual input pass-through and compositor responsiveness.


## v0.7.0 regression checks

Additional tests cover eye-collapse/reopen, attached RGB/HEX apply, exact custom
background export pixels, custom fading time and persistence, native mask geometry
plus protected input/gesture termination over toolbar and attached settings,
distinct tool cursor pixmaps/shape crosshairs, and inline text Esc cancellation.
The offscreen plugin stores but does not implement native window masks, so these
assertions validate mask construction and guards, not real OS pointer delivery.
Manual Windows check: draw across the bar, release, then repeatedly select pen,
eraser and settings. Ensure ink never obscures controls and each fresh click works.


## v0.7.1 appearance verification

All 69 tests pass with the blackboard export expecting #000000. Offscreen UI
renders checked against pure black and custom cyan backgrounds. Toolbar alpha
was 0 at the outer/top gutter and logo corner; a canvas pixel beneath the side
gutter retained custom #7dc8e8 and remained in the canvas native mask. Visually
confirmed only the narrow tool strip and soft edge shadow are visible, without
a rectangular backing. The offscreen backend cannot prove native Windows alpha
compositing or mask/input delivery.


## v0.7.2 checks

71 tests pass, including actual mouse clicks inside settings retaining the panel,
clicks on the canvas dismissing it, and app deactivation dismissing it. Existing
text typing/Enter/Esc and toolbar protection tests still pass. Logo edge improvement
removes the coarse native ellipse exclusion; native Windows edge appearance and
focus/deactivation delivery cannot be verified on the offscreen backend.


## v0.8.0 checks

79 tests pass, including glass controls/alpha export, hiding/restoring with a fake
tray while retaining marks, repeated hide, tray-unavailable fallback, decline without
registration, enable only after explicit consent, removable Linux/macOS startup files
in temporary directories, and mocked Windows current-user registry enable/disable.
No real host startup entry was installed. No native tray/compositor is available;
actual notification-area clicks, sign-in launch, Windows alpha/canvas stacking and
macOS launch-agent approval require OS acceptance. Glass is transparency, not blur.
The previous Exit-No regression was replaced because Exit now has no prompt.


## v0.8.1 developer card

79 existing tests pass. Additional scripted UI inspection verifies Developer directly
follows About My Pen, card shares the toolbar window, height is bounded, portrait and
icons load, and each of the ten real button clicks dispatches the exact supplied URL
through a mocked QDesktopServices.openUrl. No actual browser/email app was launched;
link destination availability and native default-app handling were not tested.
Rendered and visually checked the 430×398 card with no clipped labels or buttons.


## v0.8.2 organization and About checks

All 79 regression tests pass after relocation. A separate run from /tmp verified
logo/portrait/social assets resolve independently of working directory, all ten
Developer link buttons still dispatch their exact supplied URLs, every image/SVG
is beneath images/, no loose PNG remains at the root, and About contains the
developer credit and feature details inside a bounded attached panel. Visually
checked images/previews/about_preview.png. Native OS acceptance remains unchanged.


## Current platform test rerun

See CROSS_PLATFORM_TEST_REPORT.md and ../test-results/ for the current Ubuntu
offscreen run: 79 tests pass, plus background startup exits successfully. Native
Windows, macOS and Linux compositor/desktop acceptance remain untested. Portable
test assertions and isolated smoke preferences are included in this package.
