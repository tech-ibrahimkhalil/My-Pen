"""Overlay / normal-window canvas with mouse, tablet and single-touch input."""
from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QCursor, QImage, QPainter, QPen, QRegion
from PySide6.QtWidgets import QDialog, QInputDialog, QWidget, QLineEdit

from .icons import make_icon
from .drawing import Document, Mark, paint_document, paint_mark
from .dialogs import run_dialog


class Canvas(QWidget):
    closed = Signal()
    changed = Signal()
    width_requested = Signal(int)
    interaction_started = Signal()
    text_editing_changed = Signal()

    def nativeEvent(self, event_type, message):
        # Windows waits for a possible hold-to-right-click and draws a ring
        # at pen-down. Opt out on this drawing window only; tablet pressure
        # and ordinary mouse / pen events continue through Qt unchanged.
        # https://learn.microsoft.com/windows/win32/tablet/wm-tablet-querysystemgesturestatus-message
        if sys.platform == "win32" and event_type == b"windows_generic_MSG":
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x02CC:  # WM_TABLET_QUERYSYSTEMGESTURESTATUS
                return True, (0x00000001 | 0x00000008 | 0x00000010 | 0x00010000)
                # Disable press/hold, pen tap/barrel feedback and flicks.
        return False, 0  # Let Qt/platform processing handle every other message.

    def __init__(self, windowed=False):
        super().__init__()
        self.windowed = windowed
        self.document = Document()
        self.tool = "pen"
        self.color = "#ef4444"
        self.stroke_width = 4
        self.font_size = 28
        self.background_glass = False
        self.background_opacity = 45
        self.background_color = "#ffffff"
        self.text_editor = None
        self._blocked_gesture = False
        self.board = "white" if windowed else "transparent"
        self.ghost = False
        self.ink_visible = True
        self.fade_seconds = 0
        self.highlight_cursor = False
        self.wheel_adjusts_size = True
        self.allow_close = False
        self.pending: Mark | None = None
        self._last = QPointF()
        self._erasing = False
        self._erase_changed = False
        self._touch_active = False
        self._ink_cache = None
        self._cached_revision = -1
        self._cached_ids = ()
        self._pending_cache = None
        self._pending_drawn = 0
        self._fading_marks = []
        self._last_cursor = None
        self.setWindowTitle("My Pen — drawing canvas")
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if not windowed:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                                Qt.WindowType.WindowStaysOnTopHint |
                                Qt.WindowType.Tool)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.update_cursor()
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(50)
        self.animation_timer.timeout.connect(self.animate)
        self.document.on_change = self.document_changed

    @property
    def highlight_cursor(self):
        return getattr(self, "_highlight_cursor", False)

    @highlight_cursor.setter
    def highlight_cursor(self, enabled):
        self._highlight_cursor = bool(enabled)
        if hasattr(self, "animation_timer"):
            if self._last_cursor is not None:
                self.update(self.cursor_rect(self._last_cursor))
            self.sync_animation()

    def document_changed(self):
        self._fading_marks = [mark for mark in self.document.marks if mark.fade_after > 0]
        self.sync_animation()
        self.update()

    def sync_animation(self):
        needed = self.isVisible() and (bool(self._fading_marks) or self.highlight_cursor)
        if needed and not self.animation_timer.isActive():
            self.animation_timer.start()
        elif not needed:
            self.animation_timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            from .windows_input import disable_pen_feedback
            try:
                disable_pen_feedback(int(self.winId()))
            except OSError:
                import logging
                logging.getLogger(__name__).exception("Could not disable native pen feedback")
        self.apply_input_mode()
        self.update_toolbar_exclusion()
        self.document.expire()
        self.sync_animation()

    def hideEvent(self, event):
        self.animation_timer.stop()
        super().hideEvent(event)

    def resizeEvent(self, event):
        self._ink_cache = None
        self._pending_cache = None
        self._cached_revision = -1
        self._cached_ids = ()
        self.update_toolbar_exclusion()
        super().resizeEvent(event)

    def cursor_rect(self, point):
        return QRect(point.x() - 26, point.y() - 26, 52, 52)

    def animate(self):
        if not self.isVisible():
            self.animation_timer.stop()
            return
        fading = tuple(self._fading_marks)
        if fading and self.document.expire():
            self.changed.emit()
        for mark in fading:
            self.update(mark.bounds().toAlignedRect())
        if self.highlight_cursor:
            position = self.mapFromGlobal(QCursor.pos())
            if position != self._last_cursor:
                if self._last_cursor is not None:
                    self.update(self.cursor_rect(self._last_cursor))
                self.update(self.cursor_rect(position))
                self._last_cursor = position

    def update_cursor(self):
        if self.ghost:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self.tool in ("pen", "highlighter", "eraser"):
            pixmap = make_icon(self.tool, 28).pixmap(28, 28)
            self.setCursor(QCursor(pixmap, 2, 25))
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor if self.tool == "text" else Qt.CursorShape.ArrowCursor)

    def toolbar_region(self, opaque=False):
        toolbar = getattr(self, "toolbar", None)
        if toolbar is None or not toolbar.isVisible():
            return QRegion()
        region = (QRegion() if toolbar.toolbar_glass else toolbar.opaque_region()) if opaque else toolbar.mask()
        return region.translated(self.mapFromGlobal(toolbar.mapToGlobal(QPoint(0, 0))))

    def update_toolbar_exclusion(self):
        # Native input hole keeps toolbar clickable even when the overlay is activated.
        self.setMask(QRegion(self.rect()).subtracted(self.toolbar_region(opaque=True)))
        self.update()

    def protected(self, point):
        return self.toolbar_region().contains(point.toPoint())

    def board_color(self, exporting=False):
        color = {"white": QColor("white"), "black": QColor("#000000"),
                "custom": QColor(self.background_color),
                "transparent": QColor(0, 0, 0, 0 if exporting else 1)}[self.board]
        if self.background_glass and self.board != "transparent":
            color.setAlphaF(self.background_opacity / 100)
        return color

    def start_text(self, point):
        self.finish_text()
        self._text_point = QPointF(point)
        editor = self.text_editor = QLineEdit(self)
        editor.setPlaceholderText("Enter text")
        editor.setStyleSheet(f"QLineEdit {{ color: {self.color}; background: white; border: 1px dashed #08b7dc; font-size: {self.font_size}px; }}")
        editor.setGeometry(max(0, min(int(point.x()), self.width()-min(360,self.width()))),
                           max(0, min(int(point.y())-self.font_size, self.height()-self.font_size-16)),
                           min(360,self.width()), self.font_size+16)
        editor.returnPressed.connect(self.finish_text)
        editor.installEventFilter(self)
        editor.show()
        self.text_editing_changed.emit()
        editor.setFocus()

    def finish_text(self, cancel=False):
        editor = self.text_editor
        if editor is None:
            return
        self.text_editor = None
        text = editor.text()
        editor.hide()
        editor.deleteLater()
        self.text_editing_changed.emit()
        if not cancel and text.strip():
            point = self._text_point
            self.document.add(Mark("text", self.color, self.stroke_width,
                                   [(point.x(), point.y(), 1)], text=text,
                                   font_size=self.font_size, fade_after=self.fade_seconds))
            self.changed.emit()

    def eventFilter(self, watched, event):
        if watched is self.text_editor and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.finish_text(cancel=True)
            return True
        return super().eventFilter(watched, event)

    def set_ghost(self, enabled):
        if self.ghost == bool(enabled):
            return
        self.cancel_input()
        self.ghost = bool(enabled)
        self.apply_input_mode()
        self.update_cursor()
        self.update()

    def apply_input_mode(self):
        if not self.windowed:
            if self.windowHandle() is None:
                self.winId()
            if sys.platform == "win32":
                from .windows_input import set_click_through
                try:
                    set_click_through(int(self.winId()), self.ghost)
                except OSError:
                    # Retain the Qt fallback if native input-style access fails.
                    import logging
                    logging.getLogger(__name__).exception("Native click-through failed")
                    self.apply_qt_input_flags()
            else:
                self.apply_qt_input_flags()
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.ghost)

    def apply_qt_input_flags(self):
        handle = self.windowHandle()
        flags = handle.flags()
        mask = (Qt.WindowType.WindowTransparentForInput |
                Qt.WindowType.WindowDoesNotAcceptFocus)
        updated = flags | mask if self.ghost else flags & ~mask
        if updated != flags:
            handle.setFlags(updated)

    def cancel_input(self):
        self.finish_text(cancel=True)
        self.pending = None
        self._erasing = False
        self._touch_active = False
        self._pending_cache = None
        self._pending_drawn = 0
        self.update()

    def blank_layer(self):
        ratio = self.devicePixelRatioF()
        image = QImage(max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)),
                       QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(ratio)
        image.fill(Qt.GlobalColor.transparent)
        return image

    def draw_pending_pen(self):
        mark = self.pending
        if mark is None or mark.kind != "pen":
            return
        if self._pending_cache is None:
            self._pending_cache = self.blank_layer()
            self._pending_drawn = 0
        painter = QPainter(self._pending_cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._pending_drawn == 0:
            paint_mark(painter, Mark("pen", mark.color, mark.width, [mark.points[0]]))
            self._pending_drawn = 1
        for index in range(self._pending_drawn, len(mark.points)):
            paint_mark(painter, Mark("pen", mark.color, mark.width, mark.points[index-1:index+1]))
        self._pending_drawn = len(mark.points)
        painter.end()

    def committed_layer(self):
        if self._cached_revision == self.document.revision and self._ink_cache is not None:
            return self._ink_cache
        ids = tuple(id(mark) for mark in self.document.marks)
        incremental = self._ink_cache is not None and ids[:len(self._cached_ids)] == self._cached_ids
        start = len(self._cached_ids) if incremental else 0
        if not incremental:
            self._ink_cache = self.blank_layer()
        painter = QPainter(self._ink_cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for mark in self.document.marks[start:]:
            paint_mark(painter, mark)
        painter.end()
        self._cached_ids = ids
        self._cached_revision = self.document.revision
        return self._ink_cache

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # A nearly invisible fill lets native overlays receive pointer events in blank areas.
        color = self.board_color()
        painter.fillRect(self.rect(), color)
        # Paint the board under transparent gutters/shadow, but never ink over controls.
        painter.setClipRegion(QRegion(self.rect()).subtracted(self.toolbar_region()))
        if self.ink_visible:
            if self._fading_marks:
                paint_document(painter, self.document, QRectF(event.rect()))
                # Static cache cannot preserve draw order across an expiring mark.
                self._cached_revision = -1
                self._ink_cache = None
            else:
                painter.drawImage(QPoint(0, 0), self.committed_layer())
        if self.pending and self.ink_visible:
            if self.pending.kind == "pen":
                self.draw_pending_pen()
                painter.drawImage(QPoint(0, 0), self._pending_cache)
            else:
                paint_mark(painter, self.pending)
        if self.highlight_cursor:
            position = self.mapFromGlobal(QCursor.pos())
            if self.rect().contains(position):
                painter.setPen(QPen(QColor(212, 158, 0, 190), 2))
                painter.setBrush(QColor(255, 221, 0, 85))
                painter.drawEllipse(QPointF(position), 22, 22)
        if self.windowed and self.ghost:
            painter.setPen(QColor("#64748b"))
            painter.drawText(16, 24, "Ghost preview — use the toolbar to return to Draw")
        painter.end()

    def begin(self, point, pressure=1.0):
        if self.ghost or self.protected(point):
            return
        self._blocked_gesture = False
        self.interaction_started.emit()
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self._last = point
        if self.tool == "eraser":
            # One history checkpoint for the whole eraser gesture.
            self._erasing = True
            self._erase_changed = self.document.erase(point, point, max(10, self.stroke_width * 2))
            self.update()
        elif self.tool == "text":
            self.start_text(point)
        else:
            width = self.stroke_width
            self.pending = Mark(self.tool, self.color, width,
                                [(point.x(), point.y(), pressure)], fade_after=self.fade_seconds)
            self.update()

    def move_input(self, point, pressure=1.0, modifiers=Qt.KeyboardModifier.NoModifier):
        # A drag begun on the canvas keeps its mouse/tablet capture and stores
        # points behind the toolbar. A new press on controls remains protected.
        if self.protected(point) and self.pending is None and not self._erasing:
            return
        if self.ghost or self._blocked_gesture:
            return
        if self._erasing:
            self._erase_changed |= self.document.erase(self._last, point,
                                                       max(10, self.stroke_width * 2),
                                                       checkpoint=not self._erase_changed)
            self._last = point
        elif self.pending:
            mark = self.pending
            previous = QPointF(*mark.points[-1][:2])
            if mark.kind in ("pen", "highlighter"):
                if (point - previous).manhattanLength() < 0.25:
                    return
                mark.points.append((point.x(), point.y(), pressure))
                if mark.kind == "pen":
                    self.draw_pending_pen()
                    margin = mark.width + 4
                    self.update(QRectF(previous, point).normalized().adjusted(-margin,-margin,margin,margin).toAlignedRect())
                    return
            else:
                start = QPointF(*mark.points[0][:2])
                if modifiers & Qt.KeyboardModifier.ShiftModifier:
                    dx, dy = point.x() - start.x(), point.y() - start.y()
                    if mark.kind in ("rectangle", "ellipse"):
                        size = max(abs(dx), abs(dy))
                        point = start + QPointF(size if dx >= 0 else -size,
                                                size if dy >= 0 else -size)
                    else:
                        point = (QPointF(point.x(), start.y()) if abs(dx) >= abs(dy)
                                 else QPointF(start.x(), point.y()))
                mark.points = [mark.points[0], (point.x(), point.y(), pressure)]
        self.update()

    def end(self):
        if self.pending:
            self.document.add(self.pending)
            self.pending = None
            self._pending_cache = None
            self._pending_drawn = 0
            self.changed.emit()
        if self._erasing:
            self._erasing = False
            self.changed.emit()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._touch_active:
            self.begin(event.position())
            event.accept()

    def wheelEvent(self, event):
        if self.wheel_adjusts_size and not self.ghost and event.angleDelta().y():
            delta = 1 if event.angleDelta().y() > 0 else -1
            self.width_requested.emit(max(1, min(40, self.stroke_width + delta)))
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Shift and self.pending and self.pending.kind not in ("pen", "highlighter"):
            self.move_input(QPointF(self.mapFromGlobal(QCursor.pos())),
                            modifiers=event.modifiers() | Qt.KeyboardModifier.ShiftModifier)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Shift and self.pending and self.pending.kind not in ("pen", "highlighter"):
            self.move_input(QPointF(self.mapFromGlobal(QCursor.pos())),
                            modifiers=event.modifiers() & ~Qt.KeyboardModifier.ShiftModifier)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and not self._touch_active:
            self.move_input(event.position(), modifiers=event.modifiers())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._touch_active:
            if self.pending:
                self.move_input(event.position(), modifiers=event.modifiers())
            self.end()
            event.accept()

    def tabletEvent(self, event):
        kind = event.type()
        if kind == QEvent.Type.TabletPress:
            self.begin(event.position(), event.pressure())
        elif kind == QEvent.Type.TabletMove:
            self.move_input(event.position(), event.pressure(), event.modifiers())
        elif kind == QEvent.Type.TabletRelease:
            self.end()
        event.accept()  # Avoid duplicate synthesized mouse strokes.

    def event(self, event):
        kind = event.type()
        if kind in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            points = event.points()
            if kind == QEvent.Type.TouchBegin and points:
                self._touch_active = True
                self.begin(points[0].position())
            elif kind == QEvent.Type.TouchUpdate and points:
                self.move_input(points[0].position())
            elif kind == QEvent.Type.TouchEnd:
                self.end()
                self._touch_active = False
            event.accept()
            return True
        if kind == QEvent.Type.TouchCancel:
            self.cancel_input()
            event.accept()
            return True
        return super().event(event)

    def export_image(self) -> QImage:
        """Export the canvas only. Never capture the desktop or toolbar implicitly."""
        ratio = self.devicePixelRatioF()
        image = QImage(round(self.width() * ratio), round(self.height() * ratio),
                       QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(ratio)
        image.fill(self.board_color(exporting=True))
        painter = QPainter(image)
        paint_document(painter, self.document)
        painter.end()
        return image

    def closeEvent(self, event):
        # The toolbar owns exit confirmation; keep the canvas open if exit is cancelled.
        if self.allow_close:
            event.accept()
            return
        event.ignore()
        self.closed.emit()
