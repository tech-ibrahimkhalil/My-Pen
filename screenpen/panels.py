"""Attached, non-modal side panels for colors and real application settings."""
from PySide6.QtCore import QPoint, QRect, QSignalBlocker, QSize, Qt, Signal, QStandardPaths
from PySide6.QtGui import QAction, QColor, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QKeySequenceEdit, QLabel, QPushButton, QRadioButton, QScrollArea,
    QSpinBox, QToolButton, QVBoxLayout, QWidget, QWidgetAction, QSlider, QLineEdit, QSizePolicy,
)

from .dialogs import run_dialog
from .icons import make_icon

PANEL_STYLE = """
QFrame#sidePanel { background: white; border: 1px solid #d5dce2; }
QWidget { color: #253039; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
QWidget#panelContent, QScrollArea, QScrollArea > QWidget > QWidget { background: white; border: 0; }
QLabel#panelTitle { font-size: 19px; font-weight: bold; }
QLabel#sectionTitle { color: #ed1682; font-size: 16px; padding-top: 12px; padding-bottom: 4px; }
QLabel#muted { color: #6a7785; font-size: 11px; }
QCheckBox, QRadioButton { spacing: 8px; padding: 5px 0; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
QPushButton { background: #f3f7f9; border: 1px solid #d5dce2; padding: 7px 10px; }
QPushButton:hover { background: #e4f7fb; }
QPushButton#primary { background: #08b7dc; border: 0; color: #102732; }
QToolButton { background: transparent; border: 0; padding: 2px; }
QToolButton:hover { background: #e5f7fb; }
QSpinBox, QComboBox, QKeySequenceEdit { background: #f5f7f9; border: 1px solid #dbe2e7;
    padding: 6px; selection-background-color: #28c7e5; }
QKeySequenceEdit { color: #00a8d4; }
QScrollBar:vertical { background: #f3f5f7; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #c8d1d8; min-height: 26px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

# Eight hue rows; three shades in each row, like the supplied color-bar reference.
SIDE_COLORS = [
    "#007e32", "#00bf42", "#38df65", "#1455c9", "#008cdd", "#00c8ed",
    "#bb102d", "#f32e3f", "#ff6262", "#8c125e", "#d91b88", "#ff61b2",
    "#d29e00", "#f6dc00", "#fff374", "#d34c12", "#ff8500", "#ffb04c",
    "#ffffff", "#26344e", "#201446", "#a5aab0", "#000000", "#411d18",
]


class SidePanel(QFrame):
    dismissed = Signal()

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setObjectName("sidePanel")
        self.setStyleSheet(PANEL_STYLE)
        self.setWindowIcon(make_icon("logo"))

    def closeEvent(self, event):
        if self.owner._quitting:
            event.accept()
            return
        self.hide()
        self.dismissed.emit()
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.owner.close_sidebar()
        else:
            super().keyPressEvent(event)


class MenuRow(QToolButton):
    """Full-width action row with one text column, including iconless actions."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e6f8fc" if self.underMouse() and self.isEnabled() else "white"))
        if not self.icon().isNull():
            self.icon().paint(painter, QRect(12, (self.height()-16)//2, 16, 16))
        painter.setPen(QColor("#253039"))
        painter.drawText(QRect(34, 0, self.width()-38, self.height()),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())
        painter.end()


class AttachedMenu(SidePanel):
    """QAction-compatible menu embedded in the toolbar window, never a popup window."""
    aboutToShow = Signal()

    def __init__(self, owner):
        super().__init__(owner)
        self._actions = []
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body.setObjectName("panelContent")
        self.items = QVBoxLayout(self.body)
        self.items.setContentsMargins(0, 0, 0, 0)
        self.items.setSpacing(0)
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll)
        self.hide()

    def addAction(self, *args):
        if len(args) == 1 and isinstance(args[0], QAction):
            action = args[0]
        else:
            icon = None
            if isinstance(args[0], str):
                text, callback = args[0], args[1] if len(args) > 1 else None
            else:
                icon, text = args[:2]
                callback = args[2] if len(args) > 2 else None
            action = QAction(text, self)
            if icon:
                action.setIcon(icon)
            if callback:
                action.triggered.connect(lambda checked=False, fn=callback: (self.owner.close_sidebar(), fn()))
        self._actions.append(action)
        if isinstance(action, QWidgetAction):
            widget = action.defaultWidget()
            self.items.addWidget(widget)
            widget.show()
        else:
            button = MenuRow()
            button.setDefaultAction(action)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setStyleSheet("QToolButton { text-align: left; padding: 7px 12px; background: white; } "
                                "QToolButton:hover { background: #e6f8fc; }")
            self.items.addWidget(button)
        return action

    def addSeparator(self):
        action = QAction(self)
        action.setSeparator(True)
        self._actions.append(action)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        self.items.addWidget(line)
        return action

    def actions(self):
        return self._actions.copy()

    def fit(self, max_height):
        hint = self.items.sizeHint()
        # Include both layout margins and the styled frame; missing frame pixels
        # made single-row icon flyouts overflow vertically and show a scrollbar.
        chrome = 2 + self.frameWidth() * 2
        natural_height = max(hint.height(), self.items.minimumSize().height()) + chrome
        height = min(max_height, natural_height)
        overflow = natural_height > max_height
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if overflow
                                               else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        width = min(430, hint.width() + chrome + (10 if overflow else 0))
        self.setFixedSize(max(34, width), max(30, height))


class InfoPanel(SidePanel):
    def __init__(self, owner, title, text):
        super().__init__(owner)
        self.setFixedSize(430, owner.strip.sizeHint().height())
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 10, 10)
        row = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("panelTitle")
        row.addWidget(label)
        row.addStretch()
        close = QToolButton()
        close.setIcon(make_icon("close"))
        close.clicked.connect(owner.close_sidebar)
        row.addWidget(close)
        root.addLayout(row)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QLabel(text)
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setContentsMargins(4, 8, 8, 8)
        scroll.setWidget(body)
        root.addWidget(scroll)


class ColorPanel(SidePanel):
    def __init__(self, owner):
        super().__init__(owner)
        self.setWindowTitle("My Pen — color bar")
        self.setFixedWidth(84)
        root = QVBoxLayout(self)
        root.setContentsMargins(3, 3, 3, 3)
        root.setSpacing(0)
        owner.palette_mode = QComboBox(self)
        owner.palette_mode.addItems(["16 basic colors", "24 quick colors"])
        expanded = owner.settings.value("expanded_colors", True, type=bool)
        owner.palette_mode.setCurrentIndex(1 if expanded else 0)
        owner.palette_mode.hide()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        root.addLayout(grid)
        owner.swatches = []
        for index, color in enumerate(SIDE_COLORS):
            button = QPushButton()
            button.setFixedSize(25, 25)
            button.setStyleSheet(f"background: {color}; border: 0;")
            button.setToolTip(color.upper())
            button.setAccessibleName("Choose color " + color)
            button.clicked.connect(lambda checked=False, c=color: owner.palette_color(c))
            grid.addWidget(button, index // 3, index % 3)
            button.setVisible(expanded or index < 16)
            owner.swatches.append(button)
        custom = QToolButton()
        custom.setIcon(make_icon("palette"))
        custom.setIconSize(QSize(16, 16))
        custom.setText("RGB")
        custom.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        custom.setToolTip("Custom RGB / HEX color")
        custom.clicked.connect(owner.custom_color)
        root.addWidget(custom)
        owner.palette_mode.currentIndexChanged.connect(owner.palette_changed)
        self.hide()


class SettingsPanel(SidePanel):
    def __init__(self, owner):
        super().__init__(owner)
        self.setWindowTitle("My Pen — settings")
        self.setFixedWidth(430)
        self.setFixedHeight(owner.strip.sizeHint().height())
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 8, 10)
        root.setSpacing(5)
        heading = QHBoxLayout()
        title = QLabel("Settings")
        title.setObjectName("panelTitle")
        heading.addWidget(title)
        heading.addStretch()
        close = QToolButton()
        close.setIcon(make_icon("close"))
        close.setToolTip("Close settings")
        close.setAccessibleName("Close settings")
        close.clicked.connect(owner.close_sidebar)
        heading.addWidget(close)
        root.addLayout(heading)
        rule = QFrame()
        rule.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(rule)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(self.scroll)
        content = QWidget()
        content.setObjectName("panelContent")
        body = QVBoxLayout(content)
        body.setContentsMargins(3, 0, 12, 12)
        body.setSpacing(4)
        self.scroll.setWidget(content)
        self.section(body, "General")
        self.per_tool = self.checkbox(body, "Each tool remembers its own size", owner.per_tool_size,
                                      owner.set_per_tool_size, "perToolSize")
        self.wheel = self.checkbox(body, "Mouse wheel adjusts pen size", owner.canvas.wheel_adjusts_size,
                                   owner.set_wheel_size, "wheelSize")
        self.expanded = self.checkbox(body, "Expanded quick colors (24)",
                                      owner.palette_mode.currentIndex() == 1,
                                      lambda yes: owner.palette_mode.setCurrentIndex(1 if yes else 0), "expandedColors")
        self.highlight = self.checkbox(body, "Highlight the cursor", owner.canvas.highlight_cursor,
                                       owner.set_cursor_highlight, "highlightCursor")
        reset = QPushButton("Reset preferences to default")
        reset.setObjectName("primary")
        reset.clicked.connect(owner.reset_preferences)
        body.addWidget(reset)
        self.section(body, "Glass appearance")
        self.toolbar_glass = self.checkbox(body, "Glass toolbar and attached panels", owner.toolbar_glass,
                                          lambda yes: owner.set_glass("toolbar", enabled=yes), "toolbarGlass")
        self.toolbar_opacity = self.spin_row(body, "Toolbar opacity", 40, 95, owner.toolbar_opacity,
                                            lambda value: owner.set_glass("toolbar", opacity=value))
        self.toolbar_opacity.setSuffix(" %")
        self.background_glass = self.checkbox(body, "Glass canvas background", owner.canvas.background_glass,
                                             lambda yes: owner.set_glass("background", enabled=yes), "backgroundGlass")
        self.background_opacity = self.spin_row(body, "Background opacity", 10, 95, owner.canvas.background_opacity,
                                               lambda value: owner.set_glass("background", opacity=value))
        self.background_opacity.setSuffix(" %")
        note = QLabel("Glass adds transparency. Background applies to white, black and custom boards. Native frosted blur is not included.")
        note.setWordWrap(True)
        body.addWidget(note)
        self.section(body, "Startup and tray")
        self.startup_error = QLabel("")
        self.startup_error.setWordWrap(True)
        self.startup = self.checkbox(body, "Start My Pen when I sign in", owner.startup_manager.enabled(),
                                     self.change_startup, "startAtLogin")
        body.addWidget(self.startup_error)
        tray_note = QLabel("Startup runs hidden in the tray. Use the tray icon to restore My Pen. Exit quits immediately; export drawings first.")
        tray_note.setWordWrap(True)
        body.addWidget(tray_note)
        hide = QPushButton("Hide My Pen to tray")
        hide.clicked.connect(owner.hide_to_tray)
        body.addWidget(hide)
        self.section(body, "Ink tools")
        self.width_edit = self.spin_row(body, "Stroke width", 1, 40, owner.canvas.stroke_width, owner.width_input.setValue)
        self.font_edit = self.spin_row(body, "Text size", 10, 120, owner.canvas.font_size, owner.font_input.setValue)
        fade_row = QHBoxLayout()
        fade_row.addWidget(QLabel("Fading ink"))
        self.fade = QComboBox()
        for seconds in (0, 1, 3, 5, 10):
            self.fade.addItem("Permanent" if not seconds else f"{seconds} seconds", seconds)
        if self.fade.findData(owner.canvas.fade_seconds) < 0:
            self.fade.addItem(f"{owner.canvas.fade_seconds} seconds", owner.canvas.fade_seconds)
        self.fade.setCurrentIndex(max(0, self.fade.findData(owner.canvas.fade_seconds)))
        self.fade.currentIndexChanged.connect(lambda index: owner.choose_fade(self.fade.itemData(index)))
        fade_row.addWidget(self.fade)
        body.addLayout(fade_row)
        self.timer_edit = self.spin_row(body, "Custom fading time", 1, 3600, owner.last_fade,
                                         owner.set_custom_fade)
        self.timer_edit.setSuffix(" seconds")
        self.section(body, "Quick Colors")
        self.quick_buttons = []
        for index in range(4):
            row = QHBoxLayout()
            button = QPushButton()
            button.setFixedSize(26, 26)
            button.setStyleSheet(f"background: {owner.quick_color_values[index]}; border: 1px solid #cbd5dc;")
            button.setAccessibleName(f"Edit quick color {index + 1}")
            button.clicked.connect(lambda checked=False, index=index: self.edit_quick_color(index))
            row.addWidget(button)
            row.addWidget(QLabel(f"Quick color {index + 1}"))
            row.addStretch()
            body.addLayout(row)
            self.quick_buttons.append(button)
        self.section(body, "Screenshot")
        self.ask = QRadioButton("Always ask where to save")
        self.fixed = QRadioButton("Save directly to this folder:")
        self.ask.setChecked(owner.screenshot_ask)
        self.fixed.setChecked(not owner.screenshot_ask)
        self.ask.toggled.connect(owner.set_screenshot_ask)
        body.addWidget(self.ask)
        body.addWidget(self.fixed)
        self.folder_button = QPushButton(owner.screenshot_folder)
        self.folder_button.setToolTip(owner.screenshot_folder)
        self.folder_button.clicked.connect(self.choose_folder)
        body.addWidget(self.folder_button)
        self.entire = self.checkbox(body, "Select the entire screen automatically", owner.screenshot_entire,
                                    owner.set_screenshot_entire, "entireScreenshot")
        self.section(body, "Hotkeys")
        self.disabled = self.checkbox(body, "Disable hotkeys", owner.hotkeys_disabled,
                                      owner.set_hotkeys_disabled, "disableHotkeys")
        note = QLabel("Shortcuts work while My Pen has focus. Global hotkeys are not available yet.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        body.addWidget(note)
        self.hotkey_error = QLabel("")
        self.hotkey_error.setStyleSheet("color: #c5394d;")
        self.hotkey_error.setWordWrap(True)
        body.addWidget(self.hotkey_error)
        self.key_edits = []
        for index, shortcut in enumerate(owner.shortcuts):
            row = QHBoxLayout()
            label = QLabel(owner.shortcut_labels[index])
            label.setMinimumWidth(125)
            row.addWidget(label)
            edit = QKeySequenceEdit(shortcut.key())
            edit.setMaximumSequenceLength(1)
            edit.setClearButtonEnabled(True)
            edit.editingFinished.connect(lambda index=index, edit=edit: self.edit_hotkey(index, edit))
            row.addWidget(edit)
            body.addLayout(row)
            self.key_edits.append(edit)
        reset_keys = QPushButton("Reset hotkeys to default")
        reset_keys.clicked.connect(self.reset_hotkeys)
        body.addWidget(reset_keys)
        body.addStretch()
        footer = QLabel("Changes are saved automatically")
        footer.setObjectName("muted")
        root.addWidget(footer)

    def change_startup(self, enabled):
        try:
            self.owner.enable_startup(enabled)
            self.startup_error.clear()
        except (OSError, ValueError) as error:
            with QSignalBlocker(self.startup):
                self.startup.setChecked(not enabled)
            self.startup_error.setText(str(error))

    def section(self, layout, text):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)

    def checkbox(self, layout, text, checked, callback, name):
        box = QCheckBox(text)
        box.setObjectName(name)
        box.setChecked(checked)
        box.toggled.connect(callback)
        layout.addWidget(box)
        return box

    def spin_row(self, layout, label, minimum, maximum, current, callback):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(current)
        spin.setSuffix(" px")
        spin.valueChanged.connect(callback)
        row.addWidget(spin)
        layout.addLayout(row)
        return spin

    def edit_quick_color(self, index):
        self.owner.open_rgb(self.owner.quick_color_values[index],
                            lambda color: self.owner.set_quick_color(index, color),
                            f"Quick color {index + 1}")

    def choose_folder(self):
        dialog = QFileDialog(self, "My Pen — screenshot folder", self.owner.screenshot_folder)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        if run_dialog(dialog, self.owner.canvas) == QDialog.DialogCode.Accepted:
            folder = dialog.selectedFiles()[0]
            self.owner.set_screenshot_folder(folder)
            self.folder_button.setText(folder)
            self.folder_button.setToolTip(folder)

    def edit_hotkey(self, index, edit):
        if not self.owner.update_shortcut(index, edit.keySequence()):
            self.hotkey_error.setText("That shortcut is already assigned. Choose another combination.")
            with QSignalBlocker(edit):
                edit.setKeySequence(self.owner.shortcuts[index].key())
        else:
            self.hotkey_error.clear()

    def reset_hotkeys(self):
        self.owner.reset_hotkeys()
        for edit, shortcut in zip(self.key_edits, self.owner.shortcuts):
            with QSignalBlocker(edit):
                edit.setKeySequence(shortcut.key())
        self.hotkey_error.clear()


class RGBPanel(SidePanel):
    """Compact RGB/HEX editor sharing the toolbar's native window."""
    def __init__(self, owner, color, callback, title="Ink color"):
        super().__init__(owner)
        self.setFixedSize(320, min(300, owner.strip.sizeHint().height()))
        self.callback = callback
        self.color = QColor(color)
        root = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel(title + " — RGB / HEX"))
        row.addStretch()
        close = QToolButton()
        close.setIcon(make_icon("close"))
        close.clicked.connect(owner.close_sidebar)
        row.addWidget(close)
        root.addLayout(row)
        self.preview = QLabel()
        self.preview.setFixedHeight(38)
        root.addWidget(self.preview)
        self.channels = []
        for label, value in zip(("Red", "Green", "Blue"), self.color.getRgb()[:3]):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 255)
            slider.setValue(value)
            spin = QSpinBox()
            spin.setRange(0, 255)
            spin.setValue(value)
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            spin.valueChanged.connect(self.channels_changed)
            row.addWidget(slider)
            row.addWidget(spin)
            root.addLayout(row)
            self.channels.append(spin)
        self.hex = QLineEdit(self.color.name())
        self.hex.setPlaceholderText("#RRGGBB")
        self.hex.setMaxLength(7)
        self.hex.editingFinished.connect(self.hex_changed)
        root.addWidget(self.hex)
        apply = QPushButton("Apply color")
        apply.setObjectName("primary")
        apply.clicked.connect(self.apply_color)
        root.addWidget(apply)
        self.refresh()

    def channels_changed(self):
        self.color = QColor(*[spin.value() for spin in self.channels])
        self.refresh()

    def hex_changed(self):
        color = QColor(self.hex.text())
        if not color.isValid():
            self.hex.setText(self.color.name())
            return
        self.color = color
        for spin, value in zip(self.channels, color.getRgb()[:3]):
            with QSignalBlocker(spin):
                spin.setValue(value)
            spin.valueChanged.emit(value)
        self.refresh()

    def refresh(self):
        self.preview.setStyleSheet(f"background: {self.color.name()}; border: 1px solid #cbd5dc;")
        self.hex.setText(self.color.name())

    def apply_color(self):
        self.hex_changed()
        color = self.color.name()
        self.owner.close_sidebar()
        self.callback(color)


class StartupPanel(SidePanel):
    def __init__(self, owner):
        super().__init__(owner)
        self.setFixedSize(320, 200)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Start My Pen when you sign in?"))
        note = QLabel("Optional: launch quietly in the system tray. You can change this later in Settings.")
        note.setWordWrap(True)
        root.addWidget(note)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        root.addWidget(self.error)
        yes = QPushButton("Enable startup")
        yes.clicked.connect(self.enable)
        root.addWidget(yes)
        no = QPushButton("Not now")
        no.clicked.connect(self.decline)
        root.addWidget(no)

    def enable(self):
        try:
            self.owner.enable_startup(True)
        except (OSError, ValueError) as error:
            self.error.setText(str(error))
            return
        self.owner.close_sidebar()

    def decline(self):
        self.owner.settings.setValue("startup_prompted", True)
        self.owner.close_sidebar()
