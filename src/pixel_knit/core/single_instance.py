import ctypes
import getpass
from pathlib import Path
import sys

from PySide6.QtCore import QLockFile, QObject, QStandardPaths, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

CONNECT_TIMEOUT_MS = 500


# This lets the user only use one instance of this app at once
class SingleInstance(QObject):
    activateRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = f"PixelKnit-{getpass.getuser()}"
        folder = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        folder.mkdir(parents=True, exist_ok=True)
        self._lock = QLockFile(str(folder / "app.lock"))
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)

    def claim(self) -> bool:
        if not self._lock.tryLock(0):
            return False
        QLocalServer.removeServer(self._name)  # clear a socket left by a crashed run
        self._server.listen(self._name)
        return True

    def wake_existing(self) -> None:
        self._allow_foreground()
        socket = QLocalSocket()
        socket.connectToServer(self._name)
        if socket.waitForConnected(CONNECT_TIMEOUT_MS):
            socket.write(b"activate")
            socket.waitForBytesWritten(CONNECT_TIMEOUT_MS)
            socket.disconnectFromServer()

    # Windows lame boo, I have to hand focus back to the original copy
    def _allow_foreground(self) -> None:
        if sys.platform != "win32":
            return
        info = self._lock.getLockInfo()  # (pid, hostname, app name) of the lock owner
        if info:
            ctypes.windll.user32.AllowSetForegroundWindow(info[0])

    def release(self) -> None:
        self._server.close()
        self._lock.unlock()

    def _on_connection(self) -> None:
        while (connection := self._server.nextPendingConnection()) is not None:
            connection.deleteLater()
            self.activateRequested.emit()
