"""Drawing objects, history and shared rendering. Coordinates use Qt logical pixels."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPainterPathStroker, QPen


@dataclass
class Mark:
    kind: str
    color: str
    width: float
    points: list[tuple[float, float, float]] = field(default_factory=list)
    text: str = ""
    font_size: int = 28
    created_at: float = 0
    fade_after: float = 0

    def opacity(self, now=None) -> float:
        if self.fade_after <= 0 or self.created_at <= 0:
            return 1.0
        remaining = self.fade_after - ((time.monotonic() if now is None else now) - self.created_at)
        return max(0, min(1, remaining / min(1, self.fade_after / 2)))

    def path(self) -> QPainterPath:
        signature = (self.kind, len(self.points), self.points[-1] if self.points else None, self.width)
        if getattr(self, "_path_signature", None) == signature:
            return self._path_value
        path = QPainterPath()
        if not self.points:
            return path
        x, y, _ = self.points[0]
        start = QPointF(x, y)
        end = QPointF(*self.points[-1][:2])
        path.moveTo(start)
        if self.kind in ("pen", "highlighter"):
            for px, py, _ in self.points[1:]:
                path.lineTo(px, py)
            if len(self.points) == 1:
                path.lineTo(x + 0.01, y)
        elif self.kind in ("line", "arrow"):
            path.lineTo(end)
            if self.kind == "arrow" and start != end:
                angle = math.atan2(end.y() - y, end.x() - x)
                length = max(14, self.width * 4)
                for offset in (-math.pi / 6, math.pi / 6):
                    path.moveTo(end)
                    path.lineTo(end.x() - length * math.cos(angle + offset),
                                end.y() - length * math.sin(angle + offset))
        elif self.kind == "rectangle":
            path.addRect(QRectF(start, end).normalized())
        elif self.kind == "ellipse":
            path.addEllipse(QRectF(start, end).normalized())
        self._path_signature, self._path_value = signature, path
        return path

    def outline(self) -> QPainterPath:
        signature = (self.kind, len(self.points), self.points[-1] if self.points else None,
                     self.width, self.text, self.font_size)
        if getattr(self, "_outline_signature", None) == signature:
            return self._outline_value
        if self.kind == "text" and self.points:
            font = QFont()
            font.setPixelSize(self.font_size)
            path = QPainterPath()
            path.addText(QPointF(*self.points[0][:2]), font, self.text)
            self._outline_signature, self._outline_value = signature, path
            return path
        stroker = QPainterPathStroker()
        stroker.setWidth(self.width)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        result = stroker.createStroke(self.path())
        self._outline_signature, self._outline_value = signature, result
        return result

    def bounds(self) -> QRectF:
        if self.kind == "text":
            return self.outline().boundingRect().adjusted(-3, -3, 3, 3)
        # Paths are cached for committed marks; pressure never exceeds the selected width.
        margin = self.width / 2 + 3
        return self.path().boundingRect().adjusted(-margin, -margin, margin, margin)


class Document:
    def __init__(self):
        self.marks: list[Mark] = []
        self._undo: list[list[Mark]] = []
        self._redo: list[list[Mark]] = []
        self.revision = 0
        self.on_change = None

    def touched(self):
        self.revision += 1
        if self.on_change:
            self.on_change()

    def checkpoint(self):
        # Committed Marks are immutable by convention; edits replace objects.
        self._undo.append(self.marks.copy())
        self._undo = self._undo[-100:]
        self._redo.clear()

    def add(self, mark: Mark):
        if mark.fade_after > 0 and mark.created_at == 0:
            mark.created_at = time.monotonic()
        self.checkpoint()
        self.marks.append(mark)
        self.touched()

    def expire(self, now=None):
        now = time.monotonic() if now is None else now
        expired_ids = {id(mark) for mark in self.marks if mark.fade_after > 0 and mark.opacity(now) <= 0}
        if not expired_ids:
            return False
        expired = lambda mark: id(mark) in expired_ids
        changed = True
        self.marks = [m for m in self.marks if not expired(m)]
        # Expired ink cannot reappear later through undo/redo.
        self._undo = [[m for m in snapshot if not expired(m)] for snapshot in self._undo]
        self._redo = [[m for m in snapshot if not expired(m)] for snapshot in self._redo]
        self.touched()
        return changed

    def clear(self):
        if self.marks:
            self.checkpoint()
            self.marks.clear()
            self.touched()

    def undo(self):
        if self._undo:
            self._redo.append(self.marks.copy())
            self.marks = self._undo.pop()
            self.touched()

    def redo(self):
        if self._redo:
            self._undo.append(self.marks.copy())
            self.marks = self._redo.pop()
            self.touched()

    def erase(self, start: QPointF, end: QPointF, radius: float, checkpoint=True) -> bool:
        # Sweep the eraser between samples, so quick drags do not skip thin strokes.
        path = QPainterPath(start)
        path.lineTo(end if start != end else end + QPointF(0.01, 0))
        stroker = QPainterPathStroker()
        stroker.setWidth(radius * 2)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        sweep = stroker.createStroke(path)
        box = sweep.boundingRect()
        remaining = [m for m in self.marks if not (box.intersects(m.bounds()) and sweep.intersects(m.outline()))]
        changed = len(remaining) != len(self.marks)
        if changed and checkpoint:
            self.checkpoint()
        self.marks = remaining
        if changed:
            self.touched()
        return changed


def paint_mark(painter: QPainter, mark: Mark):
    if not mark.points:
        return
    painter.save()
    painter.setOpacity(mark.opacity())
    color = QColor(mark.color)
    if mark.kind == "text":
        painter.setPen(color)
        font = QFont()
        font.setPixelSize(mark.font_size)
        painter.setFont(font)
        painter.drawText(QPointF(*mark.points[0][:2]), mark.text)
    elif mark.kind == "pen":
        painter.setBrush(color)
        signature = (len(mark.points), mark.points[-1], mark.width)
        if getattr(mark, "_pen_signature", None) != signature:
            runs = []
            for index in range(1, len(mark.points)):
                width = mark.width * max(0.15, min(1, mark.points[index][2]))
                if not runs or runs[-1][0] != width:
                    runs.append((width, QPainterPath(QPointF(*mark.points[index - 1][:2]))))
                runs[-1][1].lineTo(QPointF(*mark.points[index][:2]))
            mark._pen_signature, mark._pen_runs = signature, runs
        x, y, pressure = mark.points[0]
        first_width = mark.width * max(0.15, min(1, pressure))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(x, y), first_width / 2, first_width / 2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for width, path in mark._pen_runs:
            painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
    else:
        if mark.kind == "highlighter":
            color.setAlphaF(0.3)
            # Fill a single outline: overlapping segments within one stroke stay even.
            painter.fillPath(mark.outline(), color)
        else:
            painter.setPen(QPen(color, mark.width, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(mark.path())
    painter.restore()


def paint_document(painter: QPainter, document: Document, region=None):
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for mark in document.marks:
        if region is None or region.intersects(mark.bounds()):
            paint_mark(painter, mark)
