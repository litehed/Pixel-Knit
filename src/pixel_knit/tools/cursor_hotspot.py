"""Find a tool icon's cursor hotspot by clicking on it

Run from the project folder:
    uv run python src/pixel_knit/tools/cursor_hotspot.py pencil

"""

import sys
from importlib.resources import files

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

ZOOM = 16


class HotspotPicker(QWidget):
    def __init__(self, icon_name: str):
        super().__init__()
        path = files("pixel_knit").joinpath("resources", "icons", f"{icon_name}.png")
        self.pixmap = QPixmap(str(path))
        if self.pixmap.isNull():
            sys.exit(f"Couldn't find {path}")
        self.hotspot: tuple[int, int] | None = None
        self.setWindowTitle(f"{icon_name}: click the pixel that does the work")
        self.setFixedSize(self.pixmap.width() * ZOOM, self.pixmap.height() * ZOOM)
        self.setMouseTracking(True)

    def _pixel_at(self, pos) -> tuple[int, int]:
        return pos.x() // ZOOM, pos.y() // ZOOM

    def paintEvent(self, event):
        painter = QPainter(self)
        for y in range(self.pixmap.height()):
            for x in range(self.pixmap.width()):
                shade = "#eeeeee" if (x + y) % 2 == 0 else "#dddddd"
                painter.fillRect(x * ZOOM, y * ZOOM, ZOOM, ZOOM, QColor(shade))
        painter.drawPixmap(self.rect(), self.pixmap)

        painter.setPen(QPen(QColor(0, 0, 0, 40), 1))
        for i in range(1, self.pixmap.width()):
            painter.drawLine(i * ZOOM, 0, i * ZOOM, self.height())
            painter.drawLine(0, i * ZOOM, self.width(), i * ZOOM)

        if self.hotspot is not None:
            x, y = self.hotspot
            painter.setPen(QPen(QColor("red"), 2))
            painter.drawRect(QRect(x * ZOOM, y * ZOOM, ZOOM, ZOOM))

    def mouseMoveEvent(self, event):
        x, y = self._pixel_at(event.position().toPoint())
        self.setWindowTitle(f"pixel ({x}, {y}): click to choose")

    def mousePressEvent(self, event):
        self.hotspot = self._pixel_at(event.position().toPoint())
        print(f"hotspot = {self.hotspot}")
        self.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    picker = HotspotPicker(sys.argv[1] if len(sys.argv) > 1 else "pencil")
    picker.show()
    sys.exit(app.exec())
