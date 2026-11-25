from enum import Enum
from importlib.resources import files

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCursor, QIcon, QPixmap, QTransform

ICON_SIZE = 32


class Tool(Enum):
    # icon file name, tooltip label, shortcut, and the cursor's hotspot
    PENCIL = ("pencil", "Pencil", "P", (29, 29))
    ERASER = ("eraser", "Eraser", "E", (24, 24))
    MARKER = ("marker", "Stitch Marker", "M", (16, 16))

    def __init__(
        self, icon_name: str, label: str, shortcut: str, hotspot: tuple[int, int]
    ):
        self.icon_name = icon_name
        self.label = label
        self.shortcut = shortcut
        self.hotspot = hotspot

    @property
    def icon(self) -> QIcon:
        folder = files("pixel_knit").joinpath("resources", "icons")
        icon = QIcon()
        icon.addFile(
            str(folder.joinpath(f"{self.icon_name}.png")), QSize(ICON_SIZE, ICON_SIZE)
        )
        icon.addFile(
            str(folder.joinpath(f"{self.icon_name}@2x.png")),
            QSize(ICON_SIZE * 2, ICON_SIZE * 2),
        )
        return icon

    def cursor(self, dpr: float = 1.0, flipped: bool = False) -> QCursor:
        folder = files("pixel_knit").joinpath("resources", "icons")
        names = [f"{self.icon_name}@2x.png", f"{self.icon_name}.png"]
        if dpr <= 1.0:
            names.reverse()
        pixmap = QPixmap()
        for name in names:
            pixmap = QPixmap(str(folder.joinpath(name)))
            if not pixmap.isNull():
                break
        if pixmap.isNull():
            return QCursor(Qt.CursorShape.ArrowCursor)

        if flipped:
            pixmap = pixmap.transformed(QTransform().rotate(180))
        pixmap.setDevicePixelRatio(pixmap.width() / ICON_SIZE)  # keep it 32 points wide
        return QCursor(pixmap, *self.hotspot)
