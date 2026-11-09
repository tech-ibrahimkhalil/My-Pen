"""My Pen: narrow, reference-inspired floating desktop toolbar."""
from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSettings, QSignalBlocker, QSize, QStandardPaths, QTemporaryDir, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence, QPainter, QPolygonF, QRegion, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QPushButton, QSpinBox, QSystemTrayIcon, QToolButton, QVBoxLayout, QWidget, QWidgetAction,
)
from . import __version__
from .developer import DeveloperPanel
from .startup import StartupManager
from .canvas import Canvas
from .icons import make_icon
from .dialogs import run_dialog
from .capture import CaptureSelector
from .drawing import paint_document
from .panels import AttachedMenu, ColorPanel, InfoPanel, SettingsPanel, RGBPanel, StartupPanel

PALETTE = [
    "#000000", "#ffffff", "#ff0088", "#ff3636", "#ff8a00", "#fff000",
    "#9be22d", "#00c85a", "#00c8ed", "#2484ff", "#6747e8", "#cc46ee",
    "#8d5140", "#737373", "#b8bdc6", "#006a75", "#ffcaa4", "#fff59a",
    "#b6efca", "#b4f1ff", "#bdd5ff", "#e0ccff", "#ffcae4", "#2a3444",
]
TOOLS = [("pen", "Pen", "P"), ("highlighter", "Highlighter", "H"),
         ("eraser", "Eraser", "E"), ("line", "Line", "L"),
         ("arrow", "Arrow", "A"), ("rectangle", "Rectangle", "R"),
         ("ellipse", "Ellipse / circle", "O"), ("text", "Text", "T")]

STYLE = """
QWidget { color: #25282b; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
QWidget#toolbarSurface, QWidget#toolbarRail { background: transparent; }
QFrame#strip { background: white; border: 1px solid #e5e7e9; }
QToolButton { background: white; border: 0; border-radius: 0; padding: 0; }
QToolButton:hover { background: #e9f8fc; }
QToolButton:checked { background: #28c7e5; }
QToolButton:pressed { background: #a1e9f6; }
QToolButton::menu-button { border: 0; width: 10px; }
QToolButton::menu-arrow { image: none; }
QToolButton#logo { background: transparent; }
QLabel#brand { color: #151719; font-size: 8px; font-weight: bold; letter-spacing: 1px; }
QMenu { background: white; border: 1px solid #d4d9de; padding: 5px; }
QMenu::item { padding: 8px 24px 8px 10px; }
QMenu::item:selected { background: #d9f5fb; color: #20252a; }
QMenu::separator { height: 1px; background: #e8edf0; margin: 4px 3px; }
QWidget#popup { background: white; }
QLabel#heading { font-size: 13px; font-weight: bold; padding: 3px 0 6px; }
QPushButton#swatch { border: 1px solid #bfc6cb; border-radius: 0; padding: 0; }
QPushButton#swatch:hover { border: 2px solid #252a30; }
QPushButton#custom { background: #f1f6f8; padding: 7px; border: 1px solid #d4dce2; }
QSpinBox, QComboBox { background: white; padding: 4px; border: 1px solid #cbd4da; }
QToolTip { background: #fcfcfc; color: #111; border: 1px solid #8a9095; padding: 6px; }
"""


class ToolButton(QToolButton):
    """Corner/right click opens a horizontal flyout beside the toolbar."""
    flyout_menu = None

    def mousePressEvent(self, event):
        self._menu_press = False
        if self.flyout_menu and (event.button() == Qt.MouseButton.RightButton or
                                (event.position().x() >= self.width() - 9 and
                                 event.position().y() >= self.height() - 10)):
            self._menu_press = True
            self.window().open_menu(self.flyout_menu, self)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, "_menu_press", False):
            self._menu_press = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.flyout_menu:
            p = QPainter(self)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#41494d"))
            w, h = self.width(), self.height()
            p.drawPolygon(QPolygonF([QPointF(w-10,h-3), QPointF(w-3,h-3), QPointF(w-3,h-10)]))
            p.end()


class LogoHandle(QToolButton):
    """Native move with a fallback for window managers without system move."""
    def __init__(self, parent):
        super().__init__(parent)
        self.drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.window().pos()
            handle = self.window().windowHandle()
            if handle and handle.startSystemMove():
                self.drag_offset = None
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_offset = None
        super().mouseReleaseEvent(event)


class Toolbar(QWidget):
    def __init__(self, canvas: Canvas, settings: QSettings):
        super().__init__()
        self.canvas, self.settings = canvas, settings
        self.tray = None
        self.startup_manager = StartupManager()
        self.toolbar_glass = settings.value("toolbar_glass", False, type=bool)
        self.toolbar_opacity = max(40, min(95, settings.value("toolbar_opacity", 80, type=int)))
        self.canvas.background_glass = settings.value("background_glass", False, type=bool)
        self.canvas.background_opacity = max(10, min(95, settings.value("background_opacity", 45, type=int)))
        self.collapsed = False
        self.side_panel = None
        self._panel_ghost_before = False
        self.shortcut_defaults = []
        self.shortcut_labels = []
        self.hotkeys_disabled = settings.value("hotkeys_disabled", False, type=bool)
        self.per_tool_size = settings.value("per_tool_size", False, type=bool)
        self.canvas.wheel_adjusts_size = settings.value("wheel_size", True, type=bool)
        self.canvas.background_color = str(settings.value("background_color", "#ffffff"))
        self.canvas.highlight_cursor = settings.value("highlight_cursor", False, type=bool)
        self.screenshot_ask = settings.value("screenshot_ask", True, type=bool)
        self.screenshot_entire = settings.value("screenshot_entire", False, type=bool)
        self.screenshot_folder = str(settings.value("screenshot_folder", QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DesktopLocation)))
        self.quick_color_values = []
        for i, default in enumerate(["#00c8ed", "#fff000", "#ff0088", "#000000"]):
            saved = str(settings.value(f"quick_colors/{i}", default))
            self.quick_color_values.append(saved if QColor(saved).isValid() else default)
        self._quitting = False
        self._capture_active = False
        self.capture_selector = None
        self.canvas.dialog_parent = self
        self.canvas.toolbar = self
        self.canvas.setWindowIcon(make_icon("logo"))
        self.shortcuts: list[QShortcut] = []
        self.setWindowTitle("My Pen")
        self.setWindowIcon(make_icon("logo"))
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(48)
        self.setObjectName("toolbarSurface")
        self.setAutoFillBackground(False)
        self.setStyleSheet(STYLE)
        self.rail = QWidget(self)
        self.rail.setObjectName("toolbarRail")
        self.rail.setAutoFillBackground(False)
        self.rail.setFixedWidth(48)
        root = QVBoxLayout(self.rail)
        root.setContentsMargins(7, 4, 7, 8)
        root.setSpacing(0)
        self.logo = LogoHandle(self.rail)
        self.logo.setObjectName("logo")
        self.logo.setFixedSize(34, 34)
        self.logo.setIcon(make_icon("logo", 32))
        self.logo.setIconSize(QSize(32, 32))
        self.logo.setToolTip("My Pen — drag to move\nRight-click for Restore / Quit My Pen")
        self.logo.setAccessibleName("My Pen — drag to move toolbar")
        root.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.brand = QLabel("MY PEN")
        self.brand.setObjectName("brand")
        self.brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand.setFixedHeight(16)
        root.addWidget(self.brand)
        self.brand.hide()
        root.addSpacing(2)
        self.strip = QFrame()
        self.strip.setObjectName("strip")
        root.addWidget(self.strip)
        self.reopen_button = QToolButton()
        self.reopen_button.setIcon(make_icon("eye_closed"))
        self.reopen_button.setIconSize(QSize(24, 24))
        self.reopen_button.setFixedSize(34, 30)
        self.reopen_button.setStyleSheet("background: #28c7e5; border: 2px solid white;")
        self.reopen_button.setToolTip("Show My Pen toolbar")
        self.reopen_button.setAccessibleName("Show My Pen toolbar")
        self.reopen_button.clicked.connect(self.expand_toolbar)
        root.addWidget(self.reopen_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.reopen_button.hide()
        self.tools_layout = QVBoxLayout(self.strip)
        self.tools_layout.setContentsMargins(2, 2, 2, 2)
        self.tools_layout.setSpacing(0)
        self.eye_button = self.button("eye", "Hide annotations", True)
        self.eye_button.setChecked(True)
        self.eye_button.toggled.connect(self.visibility_changed)
        self.ghost_button = self.button("cursor", "Cursor / Ghost Mode [G]\nInteract with background apps", True)
        self.ghost_button.toggled.connect(self.ghost_changed)
        self.ghost_button.setIcon(make_icon("highlight_cursor" if self.canvas.highlight_cursor else "cursor"))
        self.cursor_menu = self.menu()
        self.icon_flyout(self.cursor_menu, [
            ("cursor", "Normal cursor / Ghost Mode", lambda: self.choose_cursor(False),
             lambda: not self.canvas.highlight_cursor),
            ("highlight_cursor", "Highlighted cursor / Ghost Mode", lambda: self.choose_cursor(True),
             lambda: self.canvas.highlight_cursor),
        ])
        self.attach_menu(self.ghost_button, self.cursor_menu)
        self.last_fade = self.read_int("custom_fade_seconds", 3, 1, 3600)
        self.fade_button = self.button("fade_off", "Fading ink [Ctrl+Shift+F] — choose a lifetime", True)
        self.fade_menu = self.menu()
        self.icon_flyout(self.fade_menu, [
            ("fade_off" if seconds == 0 else f"fade_{seconds}",
             "Permanent ink" if seconds == 0 else f"Fade and disappear after {seconds} seconds",
             lambda value=seconds: self.choose_fade(value),
             lambda value=seconds: self.canvas.fade_seconds == value)
            for seconds in (0, 1, 3, 5, 10)
        ])
        self.custom_fade_action = self.fade_menu.addAction("Custom fading time…", self.open_settings)
        self.attach_menu(self.fade_button, self.fade_menu)
        self.fade_button.clicked.connect(lambda: self.choose_fade(0 if self.canvas.fade_seconds else self.last_fade))
        self.tool_buttons, self.tool_actions = {}, {}
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        self.last_ink, self.last_shape = "pen", "line"
        self.ink_button = self.button("pen", "Pen [P] — dropdown: Highlighter and Text", True)
        self.ink_button.clicked.connect(lambda: self.select_tool(self.last_ink))
        self.ink_menu = self.menu()
        for tool in ("pen", "highlighter", "text"):
            self.add_tool_action(self.ink_menu, tool, self.ink_button)
        self.tool_flyout(self.ink_menu, ("pen", "highlighter", "text"))
        self.attach_menu(self.ink_button, self.ink_menu)
        self.shape_button = self.button("line", "Line [L] — dropdown: Arrow, Rectangle, Circle", True)
        self.shape_button.clicked.connect(lambda: self.select_tool(self.last_shape))
        self.shape_menu = self.menu()
        for tool in ("line", "arrow", "rectangle", "ellipse"):
            self.add_tool_action(self.shape_menu, tool, self.shape_button)
        self.tool_flyout(self.shape_menu, ("line", "ellipse", "rectangle", "arrow"))
        self.attach_menu(self.shape_button, self.shape_menu)
        self.eraser_button = self.button("eraser", "Stroke eraser [E]", True)
        self.eraser_button.clicked.connect(lambda: self.select_tool("eraser"))
        self.tool_buttons["eraser"] = self.eraser_button
        self.width_button = self.button("width", "Stroke width and text size")
        self.build_width_menu()
        self.width_button.clicked.connect(lambda: self.open_menu(self.width_menu, self.width_button))
        self.undo_button = self.button("undo", "Undo [Ctrl/Cmd+Z] — dropdown: Redo")
        self.undo_button.clicked.connect(lambda: self.history(False))
        self.undo_menu = self.menu()
        self.undo_menu.addAction(make_icon("undo"), "Undo", lambda: self.history(False))
        self.undo_menu.addAction(make_icon("redo"), "Redo", lambda: self.history(True))
        self.attach_menu(self.undo_button, self.undo_menu)
        self.clear_button = self.button("trash", "Clear all annotations")
        self.clear_button.clicked.connect(self.clear)
        self.board_button = self.button("board", "Whiteboard / Blackboard / Transparent overlay")
        self.build_board_menu()
        self.board_button.clicked.connect(lambda: self.open_menu(self.board_menu, self.board_button))
        self.export_button = self.button("camera", "Screenshot — drag an area, then Save / Copy / Cancel")
        self.export_button.clicked.connect(self.screenshot)
        self.copy_button = self.button("clipboard", "My Pen menu — About / Help / Settings / Exit")
        self.build_palette()
        self.more_button = self.copy_button
        self.more_menu = self.menu()
        self.more_menu.addAction(make_icon("logo"), "About My Pen", self.about)
        self.more_menu.addAction(make_icon("keyboard"), "Developer", self.open_developer)
        self.more_menu.addAction(make_icon("help"), "Help / shortcuts", self.help)
        self.more_menu.addAction(make_icon("settings"), "Settings…", self.open_settings)
        self.more_menu.addAction(make_icon("clipboard"), "Copy canvas to clipboard", self.copy_canvas)
        self.more_menu.addAction(make_icon("camera"), "Export canvas PNG…", self.export)
        self.more_menu.addAction(make_icon("palette"), "Colors…", self.open_palette)
        self.more_menu.addSeparator()
        self.more_menu.addAction(make_icon("tray_down"), "Hide to tray", self.hide_to_tray)
        self.more_menu.addAction(make_icon("power"), "Exit My Pen", self.request_quit)
        self.more_button.clicked.connect(lambda: self.open_menu(self.more_menu, self.more_button))
        self.logo.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.app_menu = self.menu()
        self.app_menu.addAction("Show toolbar", self.expand_toolbar)
        self.app_menu.addAction("About My Pen", self.about)
        self.app_menu.addAction(make_icon("keyboard"), "Developer", self.open_developer)
        self.app_menu.addSeparator()
        self.app_menu.addAction("Quit My Pen", self.request_quit)
        self.logo.customContextMenuRequested.connect(lambda pos: self.open_menu(self.app_menu, self.logo))
        self.status = QLabel(self)
        self.status.hide()
        self.canvas.stroke_width = self.width_input.value()
        self.width_changed(self.width_input.value())
        self.canvas.font_size = self.font_input.value()
        saved = str(settings.value("color", "#ff0088"))
        self.choose_color(saved if QColor(saved).isValid() else "#ff0088", activate=False)
        self.sync_tool_state()
        self.refresh_status()
        saved_fade = self.read_int("fade_seconds", 0, 0, 3600)
        self.choose_fade(saved_fade)
        canvas.changed.connect(self.refresh_status)
        for tool, label, key in TOOLS:
            self.bind(key, lambda name=tool: self.select_tool(name), label)
        self.bind("Escape", lambda: self.ghost_button.setChecked(True))
        self.bind("G", self.ghost_button.toggle)
        self.bind("Ctrl+Shift+F", lambda: self.choose_fade(0 if self.canvas.fade_seconds else self.last_fade))
        self.bind(QKeySequence.StandardKey.Undo, lambda: self.history(False))
        self.bind(QKeySequence.StandardKey.Redo, lambda: self.history(True))
        self.bind(QKeySequence.StandardKey.Save, self.export)
        self.canvas.width_requested.connect(self.width_input.setValue)
        self.canvas.interaction_started.connect(self.close_sidebar)
        self.canvas.interaction_started.connect(self.raise_)
        self.canvas.text_editing_changed.connect(self.update_hotkey_state)
        self.resize_to_contents()
        self.apply_glass()
        QApplication.instance().installEventFilter(self)
        QApplication.instance().applicationStateChanged.connect(self.application_state_changed)

    def apply_glass(self):
        self.setWindowOpacity(self.toolbar_opacity / 100 if self.toolbar_glass else 1.0)
        self.canvas.update_toolbar_exclusion()
        self.canvas.update()

    def set_glass(self, target, enabled=None, opacity=None):
        obj = self if target == "toolbar" else self.canvas
        if enabled is not None:
            setattr(obj, target + "_glass", enabled)
            self.settings.setValue(target + "_glass", enabled)
        if opacity is not None:
            setattr(obj, target + "_opacity", opacity)
            self.settings.setValue(target + "_opacity", opacity)
        self.apply_glass()

    def enable_startup(self, enabled):
        self.startup_manager.set_enabled(enabled)
        self.settings.setValue("startup_prompted", True)

    def offer_startup(self):
        if not self.settings.value("startup_prompted", False, type=bool):
            self.open_sidebar(StartupPanel(self), self.strip)

    def init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        self.tray = QSystemTrayIcon(make_icon("logo"), self)
        self.tray.setToolTip("My Pen")
        self.tray_menu = QMenu()
        self.tray_menu.addAction("Show My Pen", self.restore_from_tray)
        self.tray_menu.addAction("Hide My Pen", self.hide_to_tray)
        self.tray_menu.addAction("Settings", self.tray_settings)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction("Exit My Pen", self.request_quit)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        return True

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.restore_from_tray()

    def hide_to_tray(self):
        if self.tray is None or not self.tray.isVisible():
            self.collapse_toolbar()
            return
        self.close_sidebar()
        if not self.collapsed and self.isVisible():
            self._expanded_canvas_visible = self.canvas.isVisible()
        self.canvas.cancel_input()
        self.canvas.hide()
        self.hide()

    def restore_from_tray(self):
        if self.collapsed:
            self.expand_toolbar()
        else:
            if getattr(self, "_expanded_canvas_visible", True):
                self.canvas.show()
            self.show()
            self.raise_()
        self.canvas.update_toolbar_exclusion()

    def tray_settings(self):
        self.restore_from_tray()
        self.open_settings()

    def application_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationInactive:
            self.close_sidebar()

    def eventFilter(self, watched, event):
        panel = self.side_panel
        if panel is not None and event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.TabletPress, QEvent.Type.TouchBegin):
            if hasattr(event, "globalPosition"):
                point = event.globalPosition().toPoint()
            else:
                points = event.points()
                point = points[0].globalPosition().toPoint() if points else None
            if point is not None:
                inside_panel = panel.rect().contains(panel.mapFromGlobal(point))
                inside_rail = self.rail.rect().contains(self.rail.mapFromGlobal(point))
                modal = QApplication.activeModalWidget()
                if not inside_panel and not inside_rail and modal is None:
                    self.close_sidebar()
        return super().eventFilter(watched, event)

    def button(self, icon, tooltip, checkable=False):
        button = ToolButton()
        button.setFixedSize(28, 28)
        button.setIcon(make_icon(icon))
        button.setIconSize(QSize(22, 22))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip.split("\n")[0])
        button.setCheckable(checkable)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tools_layout.addWidget(button)
        return button

    def menu(self):
        return AttachedMenu(self)

    def attach_menu(self, button, menu):
        button.flyout_menu = menu
        button.update()

    def open_menu(self, menu, button):
        if self.side_panel is menu and menu.isVisible():
            self.close_sidebar()
            return
        menu.aboutToShow.emit()
        self.open_sidebar(menu, button)

    def add_tool_action(self, menu, tool, button):
        _, label, key = next(t for t in TOOLS if t[0] == tool)
        action = QAction(make_icon(tool), f"{label}    [{key}]", self)
        action.setCheckable(True)
        action.triggered.connect(lambda checked=False, name=tool: self.select_tool(name))
        self.tool_group.addAction(action)
        self.tool_actions[tool], self.tool_buttons[tool] = action, button

    def icon_flyout(self, menu, items):
        widget = QWidget()
        widget.setStyleSheet("QWidget { background: #ffffff; } QToolButton { border: 0; "
                            "background: #ffffff; } QToolButton:hover { background: #e8f7fb; } "
                            "QToolButton:checked { background: #28c7e5; }")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        checks = []
        for icon, label, callback, selected in items:
            button = QToolButton()
            button.setFixedSize(32, 30)
            button.setIcon(make_icon(icon, 24))
            button.setIconSize(QSize(24, 24))
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, fn=callback: (self.close_sidebar(), fn()))
            layout.addWidget(button)
            checks.append((button, selected))
        action = QWidgetAction(menu)
        action.setDefaultWidget(widget)
        menu.addAction(action)
        # AttachedMenu is a QFrame; retain SidePanel's opaque background/border.
        menu.aboutToShow.connect(lambda: [button.setChecked(check()) for button, check in checks])
        menu.icon_buttons = [button for button, _ in checks]

    def tool_flyout(self, menu, names):
        self.icon_flyout(menu, [(name, self.tool_actions[name].text(),
                                self.tool_actions[name].trigger,
                                lambda name=name: self.canvas.tool == name)
                               for name in names])

    def choose_cursor(self, highlighted):
        self.canvas.highlight_cursor = highlighted
        self.ghost_button.setIcon(make_icon("highlight_cursor" if highlighted else "cursor"))
        self.ghost_button.setChecked(True)
        self.canvas.update()

    def set_custom_fade(self, seconds):
        self.settings.setValue("custom_fade_seconds", seconds)
        self.last_fade = seconds
        self.choose_fade(seconds)

    def choose_fade(self, seconds):
        self.canvas.fade_seconds = seconds
        panel = self.side_panel
        if isinstance(panel, SettingsPanel):
            with QSignalBlocker(panel.fade):
                if panel.fade.findData(seconds) < 0:
                    panel.fade.addItem(f"{seconds} seconds", seconds)
                panel.fade.setCurrentIndex(panel.fade.findData(seconds))
        self.settings.setValue("fade_seconds", seconds)
        if seconds:
            self.last_fade = seconds
            self.settings.setValue("custom_fade_seconds", seconds)
        self.fade_button.setChecked(bool(seconds))
        self.fade_button.setIcon(make_icon(f"fade_{seconds}" if seconds else "fade_off"))
        self.fade_button.setToolTip(f"Fading ink: {seconds}s — corner menu for presets" if seconds else
                                   "Permanent ink — corner menu for fading presets")
        self.refresh_status()

    def popup_widget(self, menu, heading):
        widget = QWidget()
        widget.setObjectName("popup")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 12)
        label = QLabel(heading)
        label.setObjectName("heading")
        layout.addWidget(label)
        action = QWidgetAction(menu)
        action.setDefaultWidget(widget)
        menu.addAction(action)
        return layout

    def build_width_menu(self):
        self.width_menu = self.menu()
        self.width_input = QSpinBox(self)
        self.width_input.hide()
        self.width_input.setRange(1, 40)
        self.width_input.setSuffix(" px")
        self.width_input.setValue(self.read_int("tool_widths/pen" if self.per_tool_size else "width", 4, 1, 40))
        self.width_input.valueChanged.connect(self.width_changed)
        self.font_input = QSpinBox(self)
        self.font_input.hide()
        self.font_input.setRange(10, 120)
        self.font_input.setSuffix(" px")
        self.font_input.setValue(self.read_int("font_size", 28, 10, 120))
        self.font_input.valueChanged.connect(self.font_changed)
        self.icon_flyout(self.width_menu, [
            (f"size_{size}", f"Pen size: {size} px", lambda size=size: self.width_input.setValue(size),
             lambda size=size: self.canvas.stroke_width == size) for size in (2, 4, 8, 14, 24)
        ])

    def build_board_menu(self):
        self.board_menu = self.menu()
        group = QActionGroup(self.board_menu)
        self.board_actions = []
        for i, label in enumerate(["Transparent overlay", "Whiteboard", "Blackboard"]):
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(i == (1 if self.canvas.windowed else 0))
            action.triggered.connect(lambda checked=False, index=i: self.board_changed(index))
            group.addAction(action)
            self.board_actions.append(action)
        self.icon_flyout(self.board_menu, [
            (icon, label, self.board_actions[i].trigger, lambda index=i: self.board_actions[index].isChecked())
            for i, (icon, label) in enumerate([("transparent", "Transparent overlay"),
                                              ("board", "Whiteboard"), ("blackboard", "Blackboard")])
        ])
        self.board_menu.addAction(make_icon("palette"), "Background color…", self.custom_background)

    def custom_background(self):
        self.open_rgb(self.canvas.background_color, self.set_background_color, "Background color")

    def set_background_color(self, color):
        self.canvas.background_color = color
        self.canvas.board = "custom"
        self.settings.setValue("background_color", color)
        for action in self.board_actions:
            action.setChecked(False)
        self.canvas.update()
        self.focus_canvas()

    def build_palette(self):
        quick = QWidget()
        quick.setFixedSize(28, 28)
        grid = QGridLayout(quick)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        self.quick_colors = []
        for i, color in enumerate(self.quick_color_values):
            button = QPushButton()
            button.setFixedSize(14, 14)
            button.setObjectName("swatch")
            button.setStyleSheet(f"background: {color}; border: 0;")
            button.setToolTip(color.upper())
            button.setAccessibleName(f"Quick color {color}")
            button.clicked.connect(lambda checked=False, index=i: self.choose_color(self.quick_color_values[index]))
            grid.addWidget(button, i // 2, i % 2)
            self.quick_colors.append(button)
        self.tools_layout.addWidget(quick)
        self.color_button = QPushButton()
        self.color_button.setFixedSize(28, 28)
        self.color_button.setObjectName("swatch")
        self.color_button.setAccessibleName("Current color — open full palette")
        self.color_button.clicked.connect(self.open_palette)
        self.tools_layout.addWidget(self.color_button)
        self.palette_panel = ColorPanel(self)
        self.palette_menu = self.palette_panel  # compatibility alias for palette controls

    def position_sidebar(self, panel, anchor, bottom_align=False):
        # Rail and panel share ONE native window and touch at the white strip edge.
        rail_global = self.rail.mapToGlobal(QPoint(0, 0))
        height = self.strip.sizeHint().height()
        if isinstance(panel, AttachedMenu):
            panel.fit(height)
        elif isinstance(panel, (SettingsPanel, InfoPanel, RGBPanel, DeveloperPanel)):
            panel.setFixedHeight(height)
        else:
            panel.adjustSize()
            panel.setMaximumHeight(height)
        bounds = self.screen().availableGeometry()
        width = panel.width()
        left = rail_global.x() - width + 7 >= bounds.left()
        rail_x = width - 7 if left else 0
        panel_x = 0 if left else 41
        point = anchor.mapTo(self.rail, QPoint(0, 0))
        y = point.y() + anchor.height() - panel.height() if bottom_align else point.y()
        y = max(self.strip.y(), min(y, self.strip.y() + height - panel.height()))
        self.setFixedSize(width + 41, self.rail.height())
        self.rail.move(rail_x, 0)
        panel.setParent(self)
        panel.move(panel_x, y)
        self.move(rail_global.x() - rail_x, rail_global.y())
        self.update_window_mask()

    def opaque_region(self):
        """Exclude only solid controls from the canvas, keeping board beneath clear gutters."""
        region = QRegion()
        # The logo is alpha-blended over the board. A binary ellipse cutout exposed
        # desktop pixels at its antialiased edge, creating a jagged white halo.
        control = self.reopen_button if self.collapsed else self.strip
        if control.isVisible():
            region |= QRegion(QRect(control.mapTo(self, QPoint(0, 0)), control.size()))
        if self.side_panel is not None and self.side_panel.isVisible():
            region |= QRegion(self.side_panel.geometry())
        return region

    def paintEvent(self, event):
        # Small layered edge shadow: no QGraphicsEffect rerendering the controls on hover.
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(event.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        control = self.reopen_button if self.collapsed else self.strip
        if not control.isVisible():
            painter.end()
            return
        rect = QRectF(QRect(control.mapTo(self, QPoint(0, 0)), control.size()))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for spread, alpha in ((6, 2), (5, 3), (4, 4), (3, 6), (2, 9), (1, 13)):
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(rect.adjusted(-spread, -spread+1, spread, spread+1), 2, 2)
        painter.end()

    def update_window_mask(self):
        region = QRegion(self.rail.geometry())
        if self.side_panel is not None:
            region |= QRegion(self.side_panel.geometry())
        self.setMask(region)
        self.update()
        self.canvas.update_toolbar_exclusion()

    def open_sidebar(self, panel, anchor, bottom_align=False):
        self.close_sidebar()
        self.canvas.cancel_input()
        self.side_panel = panel
        panel.dismissed.connect(self.close_sidebar)
        self.position_sidebar(panel, anchor, bottom_align)
        self.update_hotkey_state()
        panel.show()
        panel.raise_()
        self.raise_()
        self.activateWindow()
        self.update_window_mask()

    def close_sidebar(self):
        panel = self.side_panel
        if panel is None:
            return
        rail_global = self.rail.mapToGlobal(QPoint(0, 0))
        self.side_panel = None
        panel.hide()
        try:
            panel.dismissed.disconnect(self.close_sidebar)
        except (RuntimeError, TypeError):
            pass
        self.rail.move(0, 0)
        self.setFixedSize(48, self.rail.height())
        self.move(rail_global)
        self.update_window_mask()
        self.update_hotkey_state()
        if isinstance(panel, (SettingsPanel, InfoPanel, RGBPanel, StartupPanel, DeveloperPanel)):
            panel.deleteLater()

    def update_hotkey_state(self):
        for shortcut in self.shortcuts:
            shortcut.setEnabled(self.canvas.text_editor is None and not self.hotkeys_disabled and not isinstance(self.side_panel, (SettingsPanel, RGBPanel)))

    def set_hotkeys_disabled(self, disabled):
        self.hotkeys_disabled = disabled
        self.settings.setValue("hotkeys_disabled", disabled)
        self.update_hotkey_state()

    def update_shortcut(self, index, sequence):
        if not sequence.isEmpty() and any(other.key() == sequence for i, other in enumerate(self.shortcuts) if i != index):
            return False
        self.shortcuts[index].setKey(sequence)
        self.settings.setValue("shortcuts/" + self.shortcut_defaults[index],
                               sequence.toString(QKeySequence.SequenceFormat.PortableText))
        return True

    def reset_hotkeys(self):
        self.settings.remove("shortcuts")
        for shortcut, default in zip(self.shortcuts, self.shortcut_defaults):
            shortcut.setKey(QKeySequence(default))

    def set_per_tool_size(self, enabled):
        self.per_tool_size = enabled
        self.settings.setValue("per_tool_size", enabled)

    def set_wheel_size(self, enabled):
        self.canvas.wheel_adjusts_size = enabled
        self.settings.setValue("wheel_size", enabled)

    def set_cursor_highlight(self, enabled):
        self.canvas.highlight_cursor = enabled
        self.ghost_button.setIcon(make_icon("highlight_cursor" if enabled else "cursor"))
        self.settings.setValue("highlight_cursor", enabled)
        self.canvas.update()

    def set_quick_color(self, index, color):
        if not QColor(color).isValid():
            return
        self.quick_color_values[index] = QColor(color).name()
        self.quick_colors[index].setStyleSheet(f"background: {color}; border: 0;")
        self.quick_colors[index].setToolTip(color.upper())
        self.settings.setValue(f"quick_colors/{index}", color)

    def set_screenshot_ask(self, enabled):
        self.screenshot_ask = enabled
        self.settings.setValue("screenshot_ask", enabled)

    def set_screenshot_folder(self, folder):
        self.screenshot_folder = folder
        self.settings.setValue("screenshot_folder", folder)

    def set_screenshot_entire(self, enabled):
        self.screenshot_entire = enabled
        self.settings.setValue("screenshot_entire", enabled)

    def reset_preferences(self):
        self.close_sidebar()
        self.set_per_tool_size(False)
        self.settings.remove("tool_widths")
        self.set_wheel_size(True)
        self.set_cursor_highlight(False)
        self.set_glass("toolbar", enabled=False, opacity=80)
        self.set_glass("background", enabled=False, opacity=45)
        self.palette_mode.setCurrentIndex(1)
        self.width_input.setValue(4)
        self.font_input.setValue(28)
        self.choose_fade(0)
        self.choose_color("#ff0088", activate=False)
        for index, color in enumerate(["#00c8ed", "#fff000", "#ff0088", "#000000"]):
            self.set_quick_color(index, color)
        self.settings.setValue("custom_fade_seconds", 3)
        self.last_fade = 3
        self.set_hotkeys_disabled(False)
        self.reset_hotkeys()
        self.set_screenshot_ask(True)
        self.set_screenshot_entire(False)
        self.set_screenshot_folder(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        self.open_settings()

    def open_palette(self):
        if self.side_panel is self.palette_panel and self.palette_panel.isVisible():
            self.close_sidebar()
            return
        self.open_sidebar(self.palette_panel, self.color_button, bottom_align=True)

    def palette_color(self, color):
        self.close_sidebar()
        self.choose_color(color)

    def visibility_changed(self, enabled):
        self.canvas.ink_visible = enabled
        self.eye_button.setIcon(make_icon("eye" if enabled else "eye_off"))
        self.eye_button.setToolTip("Hide annotations" if enabled else "Show annotations")
        self.canvas.update()
        if not enabled:
            self.collapse_toolbar()

    def read_int(self, key, default, low, high):
        try:
            return max(low, min(high, int(self.settings.value(key, default))))
        except (ValueError, TypeError):
            return default

    def bind(self, key, callback, label=None):
        default = QKeySequence(key).toString(QKeySequence.SequenceFormat.PortableText)
        shortcut = QShortcut(QKeySequence(str(self.settings.value("shortcuts/" + default, default))), self)
        self.shortcut_defaults.append(default)
        names = {"Esc": "Cursor mode", "G": "Toggle cursor", "Ctrl+Shift+F": "Fading ink"}
        if label is None:
            label = names.get(default, "Undo" if key == QKeySequence.StandardKey.Undo else
                              "Redo" if key == QKeySequence.StandardKey.Redo else
                              "Export canvas" if key == QKeySequence.StandardKey.Save else default)
        self.shortcut_labels.append(label)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(callback)
        shortcut.setEnabled(not self.hotkeys_disabled)
        self.shortcuts.append(shortcut)

    def focus_canvas(self):
        if self.isVisible() and not self.canvas.ghost:
            self.canvas.setFocus(Qt.FocusReason.OtherFocusReason)
            self.raise_()

    def sync_tool_state(self):
        active = self.canvas.tool
        for tool, action in self.tool_actions.items():
            action.setChecked(tool == active and not self.canvas.ghost)
        self.ink_button.setChecked(active in ("pen", "highlighter", "text") and not self.canvas.ghost)
        self.shape_button.setChecked(active in ("line", "arrow", "rectangle", "ellipse") and not self.canvas.ghost)
        self.eraser_button.setChecked(active == "eraser" and not self.canvas.ghost)

    def select_tool(self, tool):
        self.close_sidebar()
        if self.per_tool_size:
            self.settings.setValue("tool_widths/" + self.canvas.tool, self.canvas.stroke_width)
            new_size = self.read_int("tool_widths/" + tool, self.canvas.stroke_width, 1, 40)
        else:
            new_size = self.canvas.stroke_width
        self.canvas.cancel_input()
        self.canvas.tool = tool
        self.width_input.setValue(new_size)
        if tool in ("pen", "highlighter", "text"):
            self.last_ink = tool
            self.ink_button.setIcon(make_icon(tool))
            self.ink_button.setToolTip(f"{tool.title()} — dropdown for Pen / Highlighter / Text")
        if tool in ("line", "arrow", "rectangle", "ellipse"):
            self.last_shape = tool
            self.shape_button.setIcon(make_icon(tool))
            self.shape_button.setToolTip(f"{tool.title()} — dropdown for shapes")
        if self.ghost_button.isChecked():
            self.ghost_button.setChecked(False)
        self.eye_button.setChecked(True)
        self.canvas.update_cursor()
        self.sync_tool_state()
        self.refresh_status()
        self.focus_canvas()

    def ghost_changed(self, enabled):
        self.canvas.set_ghost(enabled)
        self.ghost_button.setToolTip("Cursor / Ghost Mode active [G]\nClick to return to drawing" if enabled else
                                     "Cursor / Ghost Mode [G]\nClick to interact with background apps")
        self.sync_tool_state()
        self.refresh_status()
        self.raise_()
        if not enabled:
            self.focus_canvas()

    def width_changed(self, value):
        self.canvas.stroke_width = value
        self.width_button.setIcon(make_icon(f"size_{value}", 22))
        self.width_button.setToolTip(f"Pen size: {value} px — click for sizes")
        self.settings.setValue("width", value)
        if self.per_tool_size:
            self.settings.setValue("tool_widths/" + self.canvas.tool, value)

    def font_changed(self, value):
        self.canvas.font_size = value
        self.settings.setValue("font_size", value)

    def choose_color(self, color, activate=True):
        self.canvas.color = color
        self.settings.setValue("color", color)
        self.color_button.setStyleSheet(f"background: {color}; border: 0;")
        self.color_button.setToolTip(f"Current color {color.upper()}\nClick for 16 / 24 colors and custom RGB / HEX")
        if activate:
            self.focus_canvas()

    def custom_color(self):
        self.open_rgb(self.canvas.color, self.choose_color)

    def open_rgb(self, color, callback, title="Ink color"):
        self.close_sidebar()
        self.open_sidebar(RGBPanel(self, color, callback, title), self.color_button)

    def palette_changed(self, index):
        for i, swatch in enumerate(self.swatches):
            swatch.setVisible(i < (16 if index == 0 else 24))
        self.settings.setValue("expanded_colors", bool(index))
        self.palette_panel.adjustSize()
        if self.side_panel is self.palette_panel and self.palette_panel.isVisible():
            self.position_sidebar(self.palette_panel, self.color_button, True)

    def board_changed(self, index):
        self.canvas.board = ["transparent", "white", "black"][index]
        self.board_actions[index].setChecked(True)
        self.canvas.update()
        self.focus_canvas()

    def history(self, redo=False):
        self.canvas.cancel_input()
        (self.canvas.document.redo if redo else self.canvas.document.undo)()
        self.canvas.update()
        self.refresh_status()

    def clear(self):
        self.canvas.cancel_input()
        self.canvas.document.clear()
        self.canvas.update()
        self.refresh_status()

    def export(self):
        self.canvas.end()
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        dialog = QFileDialog(self, "My Pen — export annotations (not a screenshot)", folder)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter("PNG image (*.png)")
        dialog.setDefaultSuffix("png")
        dialog.selectFile("My_Pen.png")
        if run_dialog(dialog, self.canvas) == QDialog.DialogCode.Accepted:
            path = dialog.selectedFiles()[0]
            if not self.canvas.export_image().save(path, "PNG"):
                self.message("My Pen — export failed", "The PNG could not be saved. "
                             "Choose a writable folder and try again.")
            else:
                self.status.setText("PNG saved. Canvas only, not background apps.")
                self.export_button.setToolTip("Screenshot — drag an area, then Save / Copy / Cancel")

    def screenshot(self):
        self.close_sidebar()
        if self._capture_active:
            return
        self._capture_active = True
        self.canvas.end()
        self._capture_canvas_visible = self.canvas.isVisible()
        self._capture_toolbar_visible = self.isVisible()
        popup = QApplication.activePopupWidget()
        if popup:
            popup.hide()
        self.canvas.hide()
        self.hide()
        # Allow the native compositor to remove both tool windows before sampling.
        QTimer.singleShot(180, self.take_screenshot)

    def take_screenshot(self):
        try:
            if "wayland" in QApplication.platformName().lower():
                raise RuntimeError("Native Wayland screenshot capture needs portal integration. "
                                   "Use an X11 session for this initial screenshot implementation.")
            screen = self.canvas.screen() or QApplication.primaryScreen()
            geometry = screen.geometry()
            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                raise RuntimeError("The desktop could not be captured. Check screen-recording "
                                   "permission on macOS and your desktop capture support.")
            image = pixmap.toImage()
            painter = QPainter(image)
            # Composite our own ink; toolbar/cursor/dim selection UI is never captured.
            if self._capture_canvas_visible:
                offset = self.canvas.mapToGlobal(QPoint(0, 0)) - geometry.topLeft()
                painter.translate(offset)
                painter.setClipRect(self.canvas.rect())
                if self.canvas.board != "transparent":
                    painter.fillRect(self.canvas.rect(),
                                     self.canvas.board_color())
                if self.canvas.ink_visible:
                    paint_document(painter, self.canvas.document)
            painter.end()
            self.capture_selector = CaptureSelector(image, geometry, self.canvas)
            self.capture_selector.finished.connect(self.finish_screenshot)
            self.capture_selector.show()
            self.capture_selector.raise_()
            self.capture_selector.activateWindow()
            self.capture_selector.setFocus()
            if self.screenshot_entire:
                self.capture_selector.select_entire()
        except Exception as error:
            self.finish_screenshot()
            self.message("My Pen — screenshot unavailable", str(error))

    def finish_screenshot(self):
        selector = self.capture_selector
        self.capture_selector = None
        if selector:
            selector.hide()
            selector.deleteLater()
        self._capture_active = False
        if getattr(self, "_capture_canvas_visible", False) and not self.collapsed:
            self.canvas.show()
        if getattr(self, "_capture_toolbar_visible", False):
            self.show()
            self.raise_()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "rail"):
            self.canvas.update_toolbar_exclusion()

    def showEvent(self, event):
        super().showEvent(event)
        self.canvas.update_toolbar_exclusion()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.canvas.update_toolbar_exclusion()

    def resize_to_contents(self):
        self.rail.layout().invalidate()
        self.rail.layout().activate()
        height = self.rail.sizeHint().height()
        self.rail.setFixedHeight(height)
        self.setFixedSize(48, height)
        self.rail.move(0, 0)
        self.update_window_mask()

    def collapse_toolbar(self):
        self.close_sidebar()
        if self.collapsed:
            return
        self._expanded_canvas_visible = self.canvas.isVisible()
        self.canvas.cancel_input()
        self.canvas.hide()
        self.collapsed = True
        self.strip.hide()
        self.reopen_button.show()
        self.resize_to_contents()
        self.settings.setValue("toolbar_position", self.pos())

    def expand_toolbar(self):
        if not self.collapsed:
            self.show()
            return
        self.collapsed = False
        self.eye_button.setChecked(True)
        self.reopen_button.hide()
        self.strip.show()
        self.resize_to_contents()
        if getattr(self, "_expanded_canvas_visible", False):
            self.canvas.show()
        self.show()
        # Expanding near the bottom must not leave the restored bar offscreen.
        bounds = self.screen().availableGeometry()
        self.move(self.x(), max(bounds.top(), min(self.y(), bounds.bottom() - self.height())))
        self.raise_()

    def copy_canvas(self):
        self.canvas.end()
        QApplication.clipboard().setImage(self.canvas.export_image())
        self.copy_button.setToolTip("Canvas copied.\nMy Pen menu — About / Help / Settings / Exit")

    def refresh_status(self):
        mode = "Ghost / cursor" if self.canvas.ghost else self.canvas.tool.title()
        self.status.setText(f"My Pen • {mode} • {len(self.canvas.document.marks)} annotations")
        self.brand.setToolTip(self.status.text())

    def message(self, title, text, question=False):
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        if question:
            dialog.setIcon(QMessageBox.Icon.Question)
            dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            dialog.setDefaultButton(QMessageBox.StandardButton.No)
        else:
            dialog.setIcon(QMessageBox.Icon.Information)
            dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        return run_dialog(dialog, self.canvas)

    def about(self):
        self.open_info(f"About My Pen · V{__version__}",
            "Draw. Explain. Inspire.\n\n"
            "Developed by Engr Ibrahim Khalil\n"
            "Think Beyond Limits\n\n"
            "My Pen is a desktop annotation and presentation companion for teachers, "
            "trainers, engineers and anyone who wants to explain ideas visually. "
            "Write, highlight and sketch over your screen while teaching, presenting "
            "or brainstorming.\n\n"
            "Make your ideas clear\n"
            "Use pens, highlighters, text, lines, arrows and shapes. Choose your ink "
            "color and size, erase strokes, and undo or redo changes.\n\n"
            "Present your way\n"
            "Switch between a transparent overlay, whiteboard, blackboard or custom "
            "background. Try fading ink, cursor highlighting and glass transparency. "
            "Ghost Mode lets you interact with applications beneath your annotations.\n\n"
            "Keep your workflow simple\n"
            "Capture a screen region, copy or export annotations, customize shortcuts, "
            "and keep My Pen ready in the system tray. Starting at sign-in is optional.\n\n"
            "One project for Windows, Ubuntu/Linux and macOS. Desktop integration "
            "depends on the operating system.\n\n"
            "Visit Developer in the menu to meet the creator and explore tutorials, "
            "projects and contact links.")

    def open_developer(self):
        if isinstance(self.side_panel, DeveloperPanel):
            self.close_sidebar()
            return
        self.close_sidebar()
        self.open_sidebar(DeveloperPanel(self), self.strip)

    def open_settings(self):
        if isinstance(self.side_panel, SettingsPanel) and self.side_panel.isVisible():
            self.close_sidebar()
            return
        self.close_sidebar()
        self.settings_panel = SettingsPanel(self)
        self.open_sidebar(self.settings_panel, self.strip)

    def help(self):
        self.open_info("Help",
            "Drag the green nib to move the toolbar. The eye collapses it without quitting.\n"
            "Click the small cyan closed-eye button to reopen. Right-click the logo for Quit My Pen.\n"
            "Eye: collapse the toolbar and hide annotations. Closed eye: restore. Cursor: Ghost Mode / return to drawing.\n"
            "Corner arrows open tool menus. Pen menu: Pen, Highlighter, Text. Click the canvas to type; Enter places text, Esc cancels.\n"
            "Flyouts show icons horizontally, beside the toolbar.\n"
            "Stopwatch: fading ink presets; Settings accepts 1–3600 seconds. Applies only to new annotations.\n"
            "Cursor menu: normal or highlighted cursor. Dot: five quick pen sizes.\n"
            "Line menu: Line, Arrow, Rectangle, Ellipse. Dot: width and text size.\n"
            "Undo menu includes Redo. Board icon switches backgrounds; palette icon chooses a custom background.\n"
            "Camera captures a selected desktop area. Drag a rectangle, then Save / Copy / Cancel.\n"
            "Canvas-only PNG export and Copy canvas are in the clipboard menu.\n"
            "Bottom color block opens 16/24 colors and the RGB/HEX picker.\n\n"
            "Settings opens a scrollable side panel. Changes save automatically.\n"
            "Quick colors, screenshot folder and app-local hotkeys can be customized there.\n"
            "Keys: P pen; H highlighter; E eraser; L line; A arrow; R rectangle; O ellipse; T text.\n"
            "G Ghost; Esc enters Ghost; Ctrl/Cmd+Z undo; Ctrl/Cmd+S export.\n"
            "Shortcuts work only while My Pen has focus. Use the cursor button to return from Ghost.\n"
            "Export before exiting: editable sessions / autosave are not implemented yet.\n"
            "Wayland overlays and physical tablets still require native testing.")

    def open_info(self, title, text):
        self.close_sidebar()
        self.open_sidebar(InfoPanel(self, title, text), self.strip)

    def request_quit(self):
        self.close_sidebar()
        self.settings.setValue("toolbar_position", self.pos())
        self.settings.sync()
        self.canvas.allow_close = True
        self._quitting = True
        if self.tray is not None:
            self.tray.hide()
        QApplication.instance().quit()
        return True

    def closeEvent(self, event):
        if self._quitting:
            event.accept()
            return
        self.hide_to_tray()
        event.ignore()


def main(argv=None):
    parser = argparse.ArgumentParser(description="My Pen desktop annotation prototype")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--windowed", action="store_true", help="Run a normal-window drawing canvas")
    mode.add_argument("--overlay", action="store_true", help="Try desktop overlay, including on Wayland")
    parser.add_argument("--background", action="store_true", help="Start hidden in the tray")
    parser.add_argument("--smoke-test", action="store_true", help="Open then close automatically")
    args = parser.parse_args(argv)
    app = QApplication([sys.argv[0]])
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName("MyPen")
    app.setApplicationName("My Pen")
    app.setApplicationVersion(__version__)
    app.setWindowIcon(make_icon("logo"))
    wayland = "wayland" in app.platformName().lower()
    windowed = args.windowed or (wayland and not args.overlay)
    canvas = Canvas(windowed)
    smoke_directory = QTemporaryDir() if args.smoke_test else None
    preferences = (QSettings(smoke_directory.path()+"/smoke.ini", QSettings.Format.IniFormat)
                   if smoke_directory else QSettings())
    toolbar = Toolbar(canvas, preferences)
    available = app.primaryScreen().availableGeometry()
    if windowed:
        canvas.resize(min(1000, available.width()), min(700, available.height()))
        canvas.move(available.topLeft() + QPoint(90, 20))
    else:
        canvas.setGeometry(app.primaryScreen().geometry())
    canvas.show()
    toolbar.adjustSize()
    position = toolbar.settings.value("toolbar_position")
    if not isinstance(position, QPoint) or not available.contains(position):
        position = available.topLeft() + QPoint(18, 35)
    toolbar.move(max(available.left(), min(position.x(), available.right() - toolbar.width())),
                 max(available.top(), min(position.y(), available.bottom() - toolbar.height())))
    toolbar.show()
    toolbar.init_tray()
    canvas.closed.connect(toolbar.close)
    if not windowed:
        toolbar.ghost_button.setChecked(True)
    if wayland and not args.smoke_test:
        QTimer.singleShot(0, lambda: toolbar.message("My Pen — Wayland compatibility",
            "Wayland detected. My Pen uses a normal drawing window by default.\n"
            "Desktop overlays require compositor-specific testing / integration.\n"
            "Use --overlay only for experimental testing.\n"
            "Where available, X11/Xorg is the initial Linux overlay target."))
    if args.background:
        toolbar.hide_to_tray()
    elif not args.smoke_test:
        QTimer.singleShot(350, toolbar.offer_startup)
    if args.smoke_test:
        QTimer.singleShot(250, lambda: app.exit(0))
    return app.exec()
