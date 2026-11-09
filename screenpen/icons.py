"""Bundled Lucide SVG controls; custom logo and ink-size previews are retained."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).resolve().parents[1] / "images"
LUCIDE = ASSETS / "icons" / "lucide"
ICON_NAMES = {
    "eye": "eye", "eye_off": "eye-off", "eye_closed": "eye-closed",
    "cursor": "mouse-pointer-2", "highlight_cursor": "mouse-pointer-2",
    "pen": "pencil", "highlighter": "highlighter", "eraser": "eraser",
    "line": "slash", "arrow": "move-up-right", "rectangle": "rectangle-horizontal",
    "ellipse": "circle", "text": "type", "undo": "undo-2", "redo": "redo-2",
    "trash": "trash-2", "board": "presentation", "blackboard": "monitor",
    "transparent": "monitor-slide", "camera": "camera", "clipboard": "clipboard",
    "tray_down": "tray-down", "power": "power",
    "more": "ellipsis", "width": "circle", "close": "circle-x", "folder": "folder-open",
    "settings": "settings-2", "palette": "palette", "info": "info",
    "help": "circle-help", "keyboard": "keyboard", "reset": "rotate-ccw",
    "save": "save", "check": "check",
}


@lru_cache(maxsize=256)
def make_icon(name: str, size=32) -> QIcon:
    if name == "logo":
        return QIcon(str(ASSETS / "app" / "my_pen_icon.png"))
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    try:
        if name.startswith("size_"):
            # Filled circles are actual size samples, rather than decorative icons.
            diameter = int(name.split("_")[1])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#253039"))
            if diameter <= size:
                painter.drawEllipse(QRectF((size-diameter)/2, (size-diameter)/2, diameter, diameter))
            else:
                painter.setPen(QColor("#253039"))
                font = painter.font()
                font.setPixelSize(12)
                painter.setFont(font)
                painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, str(diameter))
        else:
            svg_name = ("timer-off" if name == "fade_off" else "timer") if name.startswith("fade_") else ICON_NAMES[name]
            folder = ASSETS / "icons" / "custom" if svg_name in ("monitor-slide", "tray-down", "power") else LUCIDE
            svg = (folder / (svg_name + ".svg")).read_bytes().replace(b"currentColor", b"#253039")
            if name == "highlight_cursor":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#ffe86a"))
                painter.drawEllipse(QRectF(0, 0, size, size))
            renderer = QSvgRenderer(QByteArray(svg))
            if not renderer.isValid():
                raise ValueError("Invalid bundled Lucide SVG: " + svg_name)
            renderer.render(painter, QRectF(1, 1, size-2, size-2))
            if name == "blackboard":
                painter.fillRect(QRectF(size*.27, size*.26, size*.46, size*.30), QColor("#000000"))
            if name.startswith("fade_") and name != "fade_off":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#28c7e5"))
                painter.drawEllipse(QRectF(size*.68, size*.67, size*.26, size*.26))
    finally:
        painter.end()
    return QIcon(pixmap)
