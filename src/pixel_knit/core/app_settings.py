from pathlib import Path
from typing import cast

from PySide6.QtCore import QByteArray, QSettings, QStandardPaths

_GEOMETRY = "window/geometry"
_STATE = "window/state"
_PALETTE_VISIBLE = "window/palette_visible"
_LAST_FOLDER = "files/last_folder"


class AppSettings:
    def __init__(self):
        self._store = QSettings()

    @property
    def window_geometry(self) -> QByteArray:
        return cast(
            QByteArray, self._store.value(_GEOMETRY, QByteArray(), type=QByteArray)
        )

    @window_geometry.setter
    def window_geometry(self, value: QByteArray) -> None:
        self._store.setValue(_GEOMETRY, value)

    @property
    def window_state(self) -> QByteArray:
        return cast(
            QByteArray, self._store.value(_STATE, QByteArray(), type=QByteArray)
        )

    @window_state.setter
    def window_state(self, value: QByteArray) -> None:
        self._store.setValue(_STATE, value)

    @property
    def palette_visible(self) -> bool:
        return cast(bool, self._store.value(_PALETTE_VISIBLE, True, type=bool))

    @palette_visible.setter
    def palette_visible(self, value: bool) -> None:
        self._store.setValue(_PALETTE_VISIBLE, value)

    @property
    def last_folder(self) -> str:
        folder = cast(str, self._store.value(_LAST_FOLDER, "", type=str))
        if folder and Path(folder).is_dir():
            return folder
        return QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )

    @last_folder.setter
    def last_folder(self, value: str) -> None:
        self._store.setValue(_LAST_FOLDER, value)
