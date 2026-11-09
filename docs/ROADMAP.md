# Implementation stages and complete scope

Status key: DONE = source implemented; PARTIAL = foundation only; TODO = future stage.
DONE is not a claim of native testing on all operating systems.

## Stage 1 — Shared drawing foundation (this deliverable)

| Feature | Status | Scope |
| --- | --- | --- |
| Windows / Linux / macOS shared application | PARTIAL | Shared Qt source; headless Linux tested; real-OS acceptance remains |
| Pen | DONE | Freehand mouse and Qt tablet-event input |
| Highlighter | DONE | Translucent ink; single stroke does not darken on self-overlap |
| Stroke eraser | DONE | Erase whole objects with swept hit testing |
| Clear all | DONE | Confirmed clear with undo |
| Ghost Mode | PARTIAL | Qt native click-through flag plus independent return toolbar; OS validation remains |
| 16 basic colors | DONE | Standard palette |
| 24 quick colors | DONE | Expanded palette; no payment gate |
| RGB / HEX custom colors | DONE | Attached RGB/HEX editor |
| Lines, rectangles, ellipses/circles, arrows | DONE | Shift constraints |
| Text | PARTIAL | New single-line text, size/color; later editable/movable/formatted |
| Whiteboard and blackboard | DONE | Background switching without clearing |
| Undo / redo | DONE | Last 100 checkpoints; eraser gesture grouped |
| Adjustable width | DONE | Pen, shapes and eraser radius; highlighter multiplier |
| Adjustable opacity | TODO | Stage 2; highlighter uses fixed 30% in Stage 1 |
| Draggable toolbar | DONE | Native title bar and drag label |
| Compact toolbar | DONE | v0.2.0 vertical white strip with icon menus |
| Saved preferences | DONE | Supported tool, panel, color, screenshot and hotkey preferences |
| Hotkeys | PARTIAL | Editable app-local bindings; global OS integrations remain planned |
| Stylus / pressure | PARTIAL | Qt tablet pressure used; physical hardware testing remains |
| Touchscreen | PARTIAL | Single-finger drawing; no multitouch gestures or palm rejection |
| PNG export / screenshot crop | DONE | Canvas export plus initial native desktop crop |

## Stage 2 — Editing and classroom tools

- Selection box and lasso; single and multiple object selection.
- Move, resize, duplicate, delete, and group objects.
- Edit text; choose font, alignment and size; validate Bengali shaping/fonts.
- Adjustable opacity and optional ink smoothing.
- Favorite tools/colors/widths and expanded saved preferences.
- Compact vertical toolbar completed in v0.2.0.
- Multi-page boards: create, rename, reorder, duplicate and navigate pages.
- Grid, ruled and dotted backgrounds.
- Teaching stamps: motor, relay contacts, coils, sensors, PLC I/O.
- Import personal stamps/images; manage a custom stamp library.
- Configurable fading ink includes presets and custom 1–3600 seconds (v0.7.0).
- Laser pointer trail and cursor-following spotlight remain planned.
- Highlighted presentation cursor completed in v0.3.0.
- Mouse-click indicators remain planned.

## Stage 3 — Save, capture, recover

- Versioned editable session file format; validate data when loading.
- Reopen sessions with objects/pages/backgrounds intact.
- Atomic saves, autosave and crash recovery.
- Single/all-page PDF export and per-page PNG export.
- Screenshot region selection completed in v0.4.0 (Windows/macOS/X11 capture path).
- Screenshot Save/Copy/Cancel completed in v0.4.0.
- Freeze & Annotate: capture a stable background and annotate it.
- Initial Qt desktop capture, error recovery, and HiDPI crop mapping completed; native OS testing remains.
- Wayland screenshot portal integration remains planned; macOS requires screen recording permission where applicable.

## Stage 4 — Native integrations and distribution

- Customizable global shortcuts, shortcut-conflict feedback and per-OS backends.
- Hold-to-erase / hold-to-interact temporary tool switching.
- Multi-monitor canvas selection and toolbar placement.
- Mixed-DPI monitors, unplug/replug, resolution/orientation changes.
- Native Wayland strategy for GNOME/KDE/other supported compositor targets.
- Tablet acceptance matrix (Wacom / XP-Pen models, drivers and OS versions).
- Pen eraser-end support, input preferences, touch navigation and palm rejection
  where the OS/hardware exposes the necessary information.
- Verify visibility in screen sharing and compatibility with full-screen apps.
- Per-OS packaging, clean-machine installation, signing/notarization strategy.

## Completion gate

Do not advertise full cross-platform compatibility until Windows, macOS, Linux
X11, and explicitly listed Wayland desktops pass the manual acceptance checks.
Do not advertise universal tablet support based solely on Qt pressure handling.
Do not label annotation-only PNG export as Screenshot Crop.

The next build should start with Stage 2 object selection/editing and Stage 3
session saving, so lesson content remains editable before adding more effects.

## v0.2.0 design update

Renamed the application My Pen. Added the reference-inspired vertical toolbar,
original outline icons, cyan active-tool states, black nib move handle, tool
dropdowns, hide/show annotations, four bottom quick colors, full-palette popup,
and annotation-canvas clipboard copy. Camera remains PNG export, not screen capture.

## v0.3.0 requested update

- Supplied green nib JPG is the main app/window/toolbar icon.
- Horizontal icon flyouts for cursor modes, fade lifetimes, ink tools, shapes, sizes, boards.
- Working fading ink, normal/highlighted cursor, and five quick sizes.
- Clipboard menu contains About, Help, Settings, Copy canvas, Colors and Close.
- Centralized modal handling hides the overlay, applies modality before topmost
  flags, and restores the canvas after accept/cancel. All app-owned dialogs use it.

## v0.4.0 requested changes

- Reduce toolbar to match the supplied Epic Pen proportions: 34 px strip, 28 px cells.
- Apply selected ink width consistently; remove the highlighter's old 4x multiplier.
- Update the current size-dot icon to follow the selected width.
- Close toolbar collapses to the supplied nib and closed-eye reopen control.
- Keep Quit My Pen separately in the logo context menu, with the dialog fix.
- Camera now provides desktop region capture with folder/save, clipboard/copy and X/cancel.
- Preserve annotation-only PNG export separately in the clipboard menu.

## v0.5.0 requested UI update

- Official Lucide SVG controls, bundled with ISC license and package/source metadata.
- Current color opens a narrow three-column vertical color bar beside the toolbar.
- Settings opens a scrollable side panel instead of a modal dialog.
- Supported sections: General, Ink tools, Quick Colors, Screenshot, Hotkeys.
- Implement per-tool size memory, mouse-wheel size changes, quick-color editing,
  screenshot folder/whole-screen choices, editable app-local hotkeys, duplicate
  rejection, disable/reset controls and immediate preference saving.
- Safe sidebar ownership, drawing-mode restoration, panel switching, and modal
  suspension/restoration for color/folder dialogs.

## v0.6.0 requested fixes

- Transparent green-ring logo PNG from the supplied icon.
- Immediate clear without a confirmation prompt; undo preserved.
- Existing-native-window input-mode updates, smaller dropdown hit area and reliable
  repeated tool clicks / Shift constraints.
- Cached permanent ink and incremental pending pen raster; bounded cursor/fade updates.
- Embedded option/color/settings/info panels in one native window, no floating panels.
- Panel height capped to the white toolbar strip; scroll long content internally.
- Exact collapsed logo + closed-eye-only state; no reserved full-height native hit area.

## v0.7.0

Custom backgrounds, inline single-line text, attached RGB editor, configurable fading
time, eye-collapse, main menu Exit, tool cursors and canvas control exclusion implemented.
Existing text movement, rich formatting and native OS acceptance remain pending.

## v0.7.1

Pure black board, transparent toolbar gutters and lightweight edge shadow completed.

## v0.8.0

Tray hide/restore, immediate Exit, opt-in sign-in registration and glass transparency
are implemented. Native OS acceptance and frosted background blur remain pending.
