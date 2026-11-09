"""Region screenshot selection with physical-pixel crops on scaled displays."""
from datetime import datetime
import math
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, Signal, QStandardPaths
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QToolButton, QWidget

from .dialogs import run_dialog
from .icons import make_icon


def crop_pixels(image: QImage, rect: QRect) -> QImage:
    """Convert a logical selection to image pixels; output has no UI scale factor."""
    if rect.isEmpty():
        return QImage()
    ratio = image.devicePixelRatio()
    left, top = math.floor(rect.x() * ratio), math.floor(rect.y() * ratio)
    right, bottom = math.ceil((rect.x() + rect.width()) * ratio), math.ceil((rect.y() + rect.height()) * ratio)
    bounds = QRect(left, top, right - left, bottom - top).intersected(image.rect())
    result = image.copy(bounds)
    result.setDevicePixelRatio(1)
    return result


class CaptureSelector(QWidget):
    finished = Signal()

    def __init__(self, screenshot: QImage, geometry: QRect, canvas):
        super().__init__()
        self.screenshot = screenshot
        self.canvas = canvas
        self.anchor = None
        self.selection = QRect()
        self.dragging = False
        self._finished = False
        self.setWindowTitle("My Pen — select screenshot area")
        self.setWindowIcon(make_icon("logo"))
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(geometry)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.actions = QWidget(self)
        self.actions.setStyleSheet("QWidget { background: white; color: #111; } "
                                  "QToolButton { border: 0; padding: 4px; } "
                                  "QToolButton:hover { background: #cdf5fc; }")
        layout = QHBoxLayout(self.actions)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        for name, tip, callback in [("folder", "Save selected screenshot", self.save),
                                     ("clipboard", "Copy selected screenshot", self.copy),
                                     ("close", "Cancel screenshot [Esc]", self.finish)]:
            button = QToolButton()
            button.setIcon(make_icon(name))
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.setFixedSize(32, 32)
            button.clicked.connect(callback)
            layout.addWidget(button)
        self.actions.adjustSize()
        self.actions.hide()
        self.hint = QLabel("Drag to select an area • Esc to cancel", self)
        self.hint.setStyleSheet("background: #ffffff; color: #111; padding: 7px;")
        self.hint.adjustSize()
        self.hint.move(12, 12)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(self.rect(), self.screenshot)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        if not self.selection.isEmpty():
            painter.save()
            painter.setClipRect(self.selection)
            painter.drawImage(self.rect(), self.screenshot)
            painter.restore()
            painter.setPen(QPen(QColor("#ffffff"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.selection.adjusted(0, 0, -1, -1))
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.finish()
        elif event.button() == Qt.MouseButton.LeftButton:
            self.anchor = event.position().toPoint()
            self.selection = QRect()
            self.dragging = True
            self.actions.hide()
            self.hint.hide()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.selection = QRect(self.anchor, event.position().toPoint()).normalized().intersected(self.rect())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.selection = QRect(self.anchor, event.position().toPoint()).normalized().intersected(self.rect())
            self.dragging = False
            if self.selection.width() < 2 or self.selection.height() < 2:
                self.selection = QRect()
                self.hint.show()
            else:
                x = min(self.selection.right() - self.actions.width() + 1,
                        self.width() - self.actions.width() - 4)
                y = self.selection.bottom() + 5
                if y + self.actions.height() > self.height():
                    y = max(0, self.selection.top() - self.actions.height() - 5)
                self.actions.move(max(0, x), y)
                self.actions.show()
            self.update()

    def selected_image(self):
        return crop_pixels(self.screenshot, self.selection)

    def select_entire(self):
        self.selection = self.rect()
        self.hint.hide()
        self.actions.move(max(0, self.width() - self.actions.width() - 6),
                          max(0, self.height() - self.actions.height() - 6))
        self.actions.show()
        self.update()

    def copy(self):
        if self.selection.isEmpty():
            return
        QApplication.clipboard().setImage(self.selected_image())
        self.finish()

    def save(self):
        if self.selection.isEmpty():
            return
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        owner = getattr(self.canvas, "dialog_parent", None)
        if owner is not None and not getattr(owner, "screenshot_ask", True):
            try:
                folder = Path(owner.screenshot_folder)
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / ("My_Pen_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".png")
                if not self.selected_image().save(str(path), "PNG"):
                    raise OSError("The image could not be written.")
                self.finish()
            except OSError:
                self.hint.setText("Could not save in your chosen folder. Check permissions in Settings.")
                self.hint.adjustSize()
                self.hint.show()
            return
        dialog = QFileDialog(self, "My Pen — save screenshot", folder)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setDefaultSuffix("png")
        dialog.setNameFilter("PNG image (*.png)")
        dialog.selectFile("My_Pen_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png")
        if run_dialog(dialog, self.canvas) == QDialog.DialogCode.Accepted:
            if self.selected_image().save(dialog.selectedFiles()[0], "PNG"):
                self.finish()
            else:
                self.hint.setText("Could not save. Choose a writable folder and try again.")
                self.hint.adjustSize()
                self.hint.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.finish()
        else:
            super().keyPressEvent(event)

    def finish(self):
        if not self._finished:
            self._finished = True
            self.hide()
            self.finished.emit()

    def closeEvent(self, event):
        self.finish()
        event.accept()
