from math import ceil

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap

from pixel_knit.core.pattern import Pattern
from pixel_knit.ui.theme import BORDER

THUMB_SIZE = 44


def render_thumbnail(pattern: Pattern, size: int = THUMB_SIZE) -> QPixmap:
    step = max(1, ceil(max(pattern.width, pattern.height) / size))
    w = ceil(pattern.width / step)
    h = ceil(pattern.height / step)

    colors = [QColor(c) for c in pattern.palette]
    image = QImage(w, h, QImage.Format.Format_RGB32)
    for y in range(h):
        row = max(0, pattern.height - 1 - y * step)  # row 0 is the bottom row
        for x in range(w):
            col = min(pattern.width - 1, x * step)
            image.setPixelColor(x, y, colors[pattern.cells[row][col]])

    scaled = image.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,  # keep the hard pixel edges
    )
    pixmap = QPixmap.fromImage(scaled)

    painter = QPainter(pixmap)
    painter.setPen(QPen(QColor(BORDER), 1))
    painter.drawRect(pixmap.rect().adjusted(0, 0, -1, -1))
    painter.end()
    return pixmap
