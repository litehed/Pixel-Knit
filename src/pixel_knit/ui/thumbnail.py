from array import array

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPixmap

from pixel_knit.core.pattern import Pattern
from pixel_knit.ui.theme import BORDER

THUMB_SIZE = 44


def render_thumbnail(
    pattern: Pattern, size: int = THUMB_SIZE, dpr: float | None = None
) -> QPixmap:
    if dpr is None:
        screen = QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen else 1.0
    target = max(1, round(size * dpr))  # real screen pixels

    argb = [QColor(c).rgb() for c in pattern.palette]
    pixels = array("I")
    for row in reversed(pattern.cells):
        pixels.extend([argb[i] for i in row])
    data = pixels.tobytes()
    image = QImage(
        data,
        pattern.width,
        pattern.height,
        pattern.width * 4,
        QImage.Format.Format_RGB32,
    ).copy()

    # Big charts are averaged down so thin lines survive
    if max(pattern.width, pattern.height) > target:
        mode = Qt.TransformationMode.SmoothTransformation
    else:
        mode = Qt.TransformationMode.FastTransformation
    scaled = image.scaled(target, target, Qt.AspectRatioMode.KeepAspectRatio, mode)
    pixmap = QPixmap.fromImage(scaled)
    pixmap.setDevicePixelRatio(dpr)

    painter = QPainter(pixmap)
    painter.setPen(QPen(QColor(BORDER), 1))
    logical = pixmap.deviceIndependentSize()
    painter.drawRect(QRectF(0.5, 0.5, logical.width() - 1, logical.height() - 1))
    painter.end()
    return pixmap
