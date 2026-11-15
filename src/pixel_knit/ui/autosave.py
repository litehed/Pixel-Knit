from PySide6.QtCore import QObject, QTimer
from shiboken6 import isValid

from pixel_knit.core import recovery
from pixel_knit.ui.grid_canvas import GridCanvas

AUTOSAVE_INTERVAL_MS = 3000


class AutosaveManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending: set[GridCanvas] = set()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self._timer.timeout.connect(self.flush)

    def watch(self, canvas: GridCanvas) -> None:
        canvas.undo_stack.indexChanged.connect(lambda _=0, c=canvas: self._queue(c))
        canvas.undo_stack.cleanChanged.connect(
            lambda clean, c=canvas: self.discard(c) if clean else None
        )

    def discard(self, canvas: GridCanvas) -> None:
        self._pending.discard(canvas)
        recovery.delete(canvas.session_id)

    def flush(self) -> None:
        pending, self._pending = self._pending, set()
        for canvas in pending:
            if isValid(canvas) and isValid(canvas.undo_stack) and canvas.dirty:
                recovery.write_snapshot(canvas.session_id, canvas.pattern, canvas.path)

    def _queue(self, canvas: GridCanvas) -> None:
        self._pending.add(canvas)
        if not self._timer.isActive():  # throttle, not debounce
            self._timer.start()
