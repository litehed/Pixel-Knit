from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from pixel_knit.core.pattern import DEFAULT_COLOR, Pattern
from pixel_knit.ui.theme import BORDER, CANVAS_BACKGROUND

MARGIN = 24
MIN_ZOOM = 0.5
MAX_ZOOM = 40.0
ZOOM_STEP = 1.25
WHEEL_ZOOM_RATE = 1.0015
GRID_LINE_MIN_CELL = 6

PAINT = "paint"
ERASE = "erase"


class GridCanvas(QWidget):
    paletteChanged = Signal()
    patternEdited = Signal()

    def __init__(self, pattern: Pattern | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("gridCanvas")
        self.setMinimumSize(300, 300)
        self.pattern = pattern or Pattern()
        self.active_color = DEFAULT_COLOR
        self._stroke: str | None = None  # PAINT or ERASE while a button is held
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._panning = False
        self._last_pan_pos = QPointF()

    def set_pattern(self, pattern: Pattern) -> None:
        self.pattern = pattern
        self.reset_view()

    def set_active_color(self, color: str) -> None:
        self.active_color = color

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self.update()

    def zoom_by(self, factor: float) -> None:
        self._zoom_at(QPointF(self.width() / 2, self.height() / 2), factor)

    def cell_at(self, pos: QPointF) -> tuple[int, int] | None:
        p = self.pattern
        cell, x0, y0 = self._geometry()
        col = int((pos.x() - x0) // cell)
        row = p.height - 1 - int((pos.y() - y0) // cell)  # undo the bottom-up flip
        if 0 <= col < p.width and 0 <= row < p.height:
            return row, col
        return None

    # geometry and view transforms
    def _base_cell(self) -> float:
        p = self.pattern
        return min(
            (self.width() - 2 * MARGIN) / p.width,
            (self.height() - 2 * MARGIN) / p.height,
        )

    def _geometry(self) -> tuple[float, float, float]:
        p = self.pattern
        cell = self._base_cell() * self._zoom
        x0 = (self.width() - cell * p.width) / 2 + self._pan.x()
        y0 = (self.height() - cell * p.height) / 2 + self._pan.y()
        return cell, x0, y0

    def _clamp_pan(self) -> None:
        limit_x, limit_y = self.width() / 2, self.height() / 2
        self._pan = QPointF(
            max(-limit_x, min(limit_x, self._pan.x())),
            max(-limit_y, min(limit_y, self._pan.y())),
        )

    def _zoom_at(self, pos: QPointF, factor: float) -> None:
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self._zoom * factor))
        if new_zoom == self._zoom:
            return

        p = self.pattern
        cell, x0, y0 = self._geometry()
        gx = (pos.x() - x0) / cell  # grid-space point under the cursor, in cells
        gy = (pos.y() - y0) / cell

        self._zoom = new_zoom
        new_cell = self._base_cell() * new_zoom
        new_x0 = pos.x() - gx * new_cell
        new_y0 = pos.y() - gy * new_cell
        self._pan = QPointF(
            new_x0 - (self.width() - new_cell * p.width) / 2,
            new_y0 - (self.height() - new_cell * p.height) / 2,
        )
        self._clamp_pan()
        self.update()

    # Drawing cells
    def _apply_stroke(self, pos: QPointF) -> None:
        hit = self.cell_at(pos)
        if hit is None or self._stroke is None:
            return

        if self._stroke == ERASE:
            value = 0
        else:
            # Only add the color to the palette once a cell is actually painted
            size = len(self.pattern.palette)
            value = self.pattern.index_for(self.active_color)
            if len(self.pattern.palette) != size:
                self.paletteChanged.emit()

        row, col = hit
        if self.pattern.set_cell(row, col, value):
            self.update()
            self.patternEdited.emit()

    # Drawing grid
    def paintEvent(self, event):
        p = self.pattern
        cell, x0, y0 = self._geometry()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(CANVAS_BACKGROUND))

        if cell >= GRID_LINE_MIN_CELL:
            painter.setPen(QPen(QColor(BORDER), 1))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        # Only loop over the cells that are actually on screen
        first_col = max(0, int((0 - x0) // cell))
        last_col = min(p.width - 1, int((self.width() - x0) // cell))
        first_screen_row = max(0, int((0 - y0) // cell))
        last_screen_row = min(p.height - 1, int((self.height() - y0) // cell))

        for screen_row in range(first_screen_row, last_screen_row + 1):
            row = p.height - 1 - screen_row  # row 0 is at the bottom
            y = y0 + screen_row * cell
            for col in range(first_col, last_col + 1):
                painter.setBrush(QColor(p.palette[p.cells[row][col]]))
                painter.drawRect(QRectF(x0 + col * cell, y, cell, cell))

    # Input Events
    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = WHEEL_ZOOM_RATE ** event.angleDelta().y()
            self._zoom_at(event.position(), factor)
        else:
            delta = event.pixelDelta()
            if delta.isNull():  # regular mouse wheel: no pixel data
                delta = event.angleDelta() / 2
            self._pan += QPointF(delta)
            self._clamp_pan()
            self.update()

    def event(self, e):
        # Mac trackpad pinch arrives as a native gesture, not a wheel event.
        if (
            e.type() == QEvent.Type.NativeGesture
            and e.gestureType() == Qt.NativeGestureType.ZoomNativeGesture
        ):
            self._zoom_at(e.position(), 1.0 + e.value())
            return True
        return super().event(e)

    def mousePressEvent(self, event):
        button = event.button()
        if button == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_pan_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if button == Qt.MouseButton.LeftButton:
            self._stroke = PAINT
        elif button == Qt.MouseButton.RightButton:
            self._stroke = ERASE
        else:
            return
        self._apply_stroke(event.position())

    def mouseMoveEvent(self, event):
        if self._panning:
            pos = event.position()
            self._pan += pos - self._last_pan_pos
            self._last_pan_pos = pos
            self._clamp_pan()
            self.update()
            return
        self._apply_stroke(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.unsetCursor()
            return
        self._stroke = None
