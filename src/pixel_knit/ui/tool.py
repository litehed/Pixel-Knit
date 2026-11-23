from enum import Enum
from importlib.resources import files

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

ICON_SIZE = 32


class Tool(Enum):
    PENCIL = ("pencil", "Pencil", "P")
    ERASER = ("eraser", "Eraser", "E")

    def __init__(self, icon_name: str, label: str, shortcut: str):
        self.icon_name = icon_name
        self.label = label
        self.shortcut = shortcut

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
