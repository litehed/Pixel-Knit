from PySide6.QtGui import QUndoCommand

from pixel_knit.core.pattern import Pattern


class StrokeCommand(QUndoCommand):
    def __init__(
        self,
        pattern: Pattern,
        changes: dict[tuple[int, int], tuple[str, str]],
        text: str,
    ):
        super().__init__(text)
        self._pattern = pattern
        self._changes = changes
        self._already_applied = True

    def _apply(self, which: int) -> None:
        index_of: dict[str, int] = {}
        for (row, col), colors in self._changes.items():
            color = colors[which]
            if color not in index_of:
                index_of[color] = self._pattern.index_for(color)
            self._pattern.cells[row][col] = index_of[color]

    def redo(self):
        if self._already_applied:
            self._already_applied = False
            return
        self._apply(1)

    def undo(self):
        self._apply(0)


class SetBackgroundCommand(QUndoCommand):
    def __init__(self, pattern: Pattern, color: str):
        super().__init__("Change Background")
        self._pattern = pattern
        self._color = color
        self._old_background = pattern.palette[0]
        if color in pattern.palette[1:]:
            self._old_palette = list(pattern.palette)
            self._old_cells = [row[:] for row in pattern.cells]
        else:
            self._old_palette = None
            self._old_cells = None

    def redo(self):
        self._pattern.set_background(self._color)

    def undo(self):
        if self._old_palette is None or self._old_cells is None:
            self._pattern.palette[0] = self._old_background
        else:
            self._pattern.palette = list(self._old_palette)
            self._pattern.cells = [row[:] for row in self._old_cells]
