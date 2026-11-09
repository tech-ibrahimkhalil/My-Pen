"""Attached developer card. All artwork and brand icons are bundled locally."""
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QByteArray, QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget
from .icons import ASSETS, make_icon
from .panels import SidePanel

LINKS = [
    ('YouTube', 'youtube', '#ff0033', 'https://www.youtube.com/@AutomationInsiderX?sub_confirmation=1'),
    ('LinkedIn', 'linkedin', '#0077b5', 'https://www.linkedin.com/in/ibrahim-khalil-tech/'),
    ('GitHub', 'github', '#24292f', 'https://github.com/tech-ibrahimkhalil'),
    ('Gmail', 'gmail', '#ea4335', 'mailto:tech.ibrahimkhalil@gmail.com'),
    ('WhatsApp', 'whatsapp', '#22c965', 'https://wa.me/8801741412002'),
    ('Telegram', 'telegram', '#24a1de', 'https://t.me/superengineer'),
    ('X', 'x', '#000000', 'https://x.com/ibrahim_kha_lil'),
    ('Facebook', 'facebook', '#0866ff', 'https://www.facebook.com/ibrahimkhalil.tech'),
    ('Instagram', 'instagram', '#dc288c', 'https://www.instagram.com/ibrahim_khalil_tech/'),
    ('Blog', 'blogger', '#ff942f', 'https://super-engineers.blogspot.com/'),
]


@lru_cache(maxsize=16)
def brand_icon(name, color):
    pixmap = QPixmap(56, 56)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if name == 'linkedin':
        # LinkedIn is no longer distributed by Simple Icons; use the reference's "in" monogram.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(QRectF(1, 1, 26, 26), 2, 2)
        painter.setPen(QColor('white'))
        font = painter.font();font.setPixelSize(23);font.setBold(True);painter.setFont(font)
        painter.drawText(QRectF(1, 0, 26, 28), Qt.AlignmentFlag.AlignCenter, 'in')
    else:
        svg = (ASSETS / 'icons' / 'brands' / (name + '.svg')).read_bytes()
        svg = svg.replace(b'<svg ', ('<svg fill="'+color+'" ').encode(), 1)
        QSvgRenderer(QByteArray(svg)).render(painter, QRectF(1, 1, 26, 26))
    painter.end()
    return QIcon(pixmap)


class DeveloperPhoto(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(76, 76)
        self.photo = QPixmap(str(ASSETS / 'app' / 'developer.png'))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath();clip.addRoundedRect(QRectF(self.rect()), 18, 18)
        painter.setClipPath(clip)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self.photo)
        painter.end()


class DeveloperPanel(SidePanel):
    def __init__(self, owner):
        super().__init__(owner)
        self.setFixedSize(430, min(398, owner.strip.sizeHint().height()))
        self.setObjectName('developerCard')
        self.setStyleSheet('''
QFrame#developerCard { border: 1px solid rgba(255,255,255,210); border-radius: 18px; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(238,247,255,220),stop:0.5 rgba(213,232,246,205),stop:1 rgba(191,216,235,220)); }
QWidget { font-family: 'Segoe UI', sans-serif; color: #203c55; background: transparent; }
QLabel#devName { font-size: 20px; font-weight: 700; }
QLabel#devCaption { font-size: 13px; }
QPushButton { background: rgba(255,255,255,185); color: #203c55; border: 1px solid rgba(255,255,255,225); border-radius: 16px; text-align: left; padding: 0 14px; font-size: 16px; }
QPushButton:hover { background: rgba(255,255,255,235); }
QPushButton:pressed { background: rgba(195,224,242,235); }
QToolButton { background: transparent; border: 0; }
QToolButton:hover { background: rgba(255,255,255,165); }
''')
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)
        header = QHBoxLayout();header.setSpacing(14)
        self.photo = DeveloperPhoto();header.addWidget(self.photo)
        text = QVBoxLayout();text.setSpacing(3)
        for name, value in [('devCaption','Developed By'),('devName','Engr Ibrahim Khalil'),('devCaption','Think Beyond Limits')]:
            label = QLabel(value);label.setObjectName(name);text.addWidget(label)
        header.addLayout(text, 1)
        close = QToolButton();close.setIcon(make_icon('close'));close.setToolTip('Close developer card')
        close.clicked.connect(owner.close_sidebar)
        header.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)
        grid = QGridLayout();grid.setSpacing(10)
        self.link_buttons = {}
        for i, (label, icon, color, url) in enumerate(LINKS):
            button = QPushButton('  '+label)
            button.setIcon(brand_icon(icon, color));button.setIconSize(QSize(25,25))
            button.setFixedHeight(46)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(url)
            button.setAccessibleName(label+' — '+url)
            button.clicked.connect(lambda checked=False, url=url: self.open_link(url))
            grid.addWidget(button, i//2, i%2)
            self.link_buttons[label] = button
        grid.setColumnStretch(0,1);grid.setColumnStretch(1,1)
        root.addLayout(grid)
        self.error = QLabel('');self.error.setWordWrap(True);self.error.hide()
        root.addWidget(self.error)

    def open_link(self, url):
        if not QDesktopServices.openUrl(QUrl(url)):
            self.error.setText('Could not open the link. Check your default browser or email app.')
            self.error.show()
