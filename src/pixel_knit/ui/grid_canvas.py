from array import array
import uuid

from PySide6.QtCore import QEvent, QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QUndoStack
from PySide6.QtWidgets import QMenu, QMessageBox, QWidget

from pixel_knit.core.commands import SetBackgroundCommand, StrokeCommand
from pixel_knit.core.geometry import line_cells
from pixel_knit.core.pattern import DEFAULT_COLOR, Pattern
from pixel_knit.ui.theme import ACCENT, BORDER, CANVAS_BACKGROUND, GUIDE, TEXT_MUTED

DIM_ALPHA = 150

MARGIN = 24
MIN_ZOOM = 0.5
MAX_ZOOM = 40.0
ZOOM_STEP = 1.25
WHEEL_ZOOM_RATE = 1.0015
GRID_LINE_MIN_CELL = 6

LABEL_MARGIN = 48
LABEL_GAP = 8
LABEL_STEPS = (1, 5, 10, 50, 100)
LABEL_MIN_SPACING = 14
LABEL_MAX_FONT = 16

GUIDE_STEPS = (5, 10, 50, 100)
GUIDE_MIN_SPACING = 24
GUIDE_WIDTH = 2

MARKER_RING = "#222222"
MARKER_HALO = "#ffffff"

PAINT = "paint"
ERASE = "erase"


class GridCanvas(QWidget):
    paletteChanged = Signal()
    viewerChanged = Signal()
    rowChanged = Signal()
    markersChanged = Signal()

    def __init__(self, pattern: Pattern | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("gridCanvas")
        self.setMinimumSize(300, 300)
        self.pattern = pattern or Pattern()
        self.active_color = DEFAULT_COLOR
        self._stroke: str | None = None  # PAINT or ERASE while a button is held
        self._last_cell: tuple[int, int] | None = None
        self._stroke_button: Qt.MouseButton | None = None
        self._image: QImage | None = None  # chart cache
        self._zoom = 1.0
        self._saved_view = (1.0, QPointF(0, 0))
        self._pan = QPointF(0, 0)
        self._panning = False
        self._last_pan_pos = QPointF()
        self.path: str | None = None
        self.untitled_number = 0
        self.undo_stack = QUndoStack(self)
        self.undo_stack.indexChanged.connect(self._on_stack_changed)
        self._stroke_changes: dict[tuple[int, int], tuple[int, int]] = {}
        self._viewer = False
        self._isolated = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.session_id = uuid.uuid4().hex

    def set_pattern(self, pattern: Pattern) -> None:
        self.pattern = pattern
        self._image = None
        self.undo_stack.clear()
        self.reset_view()

    def set_active_color(self, color: str) -> None:
        self.active_color = color

    @property
    def dirty(self) -> bool:
        return not self.undo_stack.isClean()

    def _chart_image(self) -> QImage:
        if self._image is None:
            p = self.pattern
            argb = [QColor(c).rgb() for c in p.palette]
            pixels = array("I")
            for row in reversed(p.cells):  # row 0 is the bottom of the chart
                pixels.extend([argb[i] for i in row])
            self._image = QImage(
                pixels.tobytes(),
                p.width,
                p.height,
                p.width * 4,
                QImage.Format.Format_RGB32,
            ).copy()  # copy so Qt owns the pixels
        return self._image

    def _on_stack_changed(self, _index: int = 0) -> None:
        if self._stroke is None:
            self.pattern.remove_unused_colors()
        self._image = None
        self.update()
        self.paletteChanged.emit()

    @property
    def viewer_mode(self) -> bool:
        return self._viewer

    @property
    def current_row(self) -> int:
        return self.pattern.current_row

    def set_viewer_mode(self, enabled: bool) -> None:
        if enabled == self._viewer:
            return
        self._viewer = enabled
        if not enabled:
            self._leave_isolated()
        if enabled:
            self.setFocus()
        self.update()
        self.viewerChanged.emit()

    @property
    def isolated(self) -> bool:
        return self._isolated

    def set_isolated(self, enabled: bool) -> None:
        if enabled == self._isolated:
            return
        if enabled:
            self._saved_view = (self._zoom, QPointF(self._pan))
            self._zoom, self._pan = 1.0, QPointF(0, 0)  # the row has its own view
            self._isolated = True
            self._viewer = True
            self.setFocus()
        else:
            self._leave_isolated()
        self.update()
        self.viewerChanged.emit()

    def _leave_isolated(self) -> None:
        if self._isolated:
            self._isolated = False
            self._zoom, self._pan = self._saved_view

    def set_row(self, row: int) -> None:
        row = row % self.pattern.height
        if row != self.pattern.current_row:
            self.pattern.current_row = row
            self.update()
            self.rowChanged.emit()

    def toggle_marker(self, row: int, col: int) -> None:
        markers = self.pattern.markers
        markers.symmetric_difference_update({(row, col)})
        self.update()
        self.markersChanged.emit()

    def clear_markers(self) -> None:
        count = len(self.pattern.markers)
        if not count:
            return
        answer = QMessageBox.question(
            self,
            "Clear Markers",
            f"Remove all {count} stitch marker{'s' if count != 1 else ''}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.pattern.markers.clear()
            self.update()
            self.markersChanged.emit()

    def move_row(self, delta: int) -> None:
        self.set_row(self.pattern.current_row + delta)

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self.update()

    def zoom_by(self, factor: float) -> None:
        self._zoom_at(QPointF(self.width() / 2, self.height() / 2), factor)

    def _raw_cell_at(self, pos: QPointF) -> tuple[int, int]:
        cell, x0, y0 = self._geometry()
        col = int((pos.x() - x0) // cell)
        row = (
            self.pattern.height - 1 - int((pos.y() - y0) // cell)
        )  # undo the bottom-up flip
        return row, col

    def cell_at(self, pos: QPointF) -> tuple[int, int] | None:
        p = self.pattern
        row, col = self._raw_cell_at(pos)
        if 0 <= col < p.width and 0 <= row < p.height:
            return row, col
        return None

    # geometry and view transforms
    def _base_cell(self) -> float:
        p = self.pattern
        usable_w = self.width() - 2 * LABEL_MARGIN
        usable_h = self.height() - 2 * MARGIN
        if self._isolated:
            return min(usable_w / p.width, usable_h)
        return min(usable_w / p.width, usable_h / p.height)

    def _centered_origin(self, cell: float) -> tuple[float, float]:
        p = self.pattern
        x0 = (self.width() - cell * p.width) / 2
        if self._isolated:  # center the current row, not the whole grid
            y0 = (self.height() - cell) / 2 - (p.height - 1 - p.current_row) * cell
        else:
            y0 = (self.height() - cell * p.height) / 2
        return x0, y0

    def _geometry(self) -> tuple[float, float, float]:
        cell = self._base_cell() * self._zoom
        ox, oy = self._centered_origin(cell)
        return cell, ox + self._pan.x(), oy + self._pan.y()

    def _clamp_pan(self) -> None:
        # The grids far edges can travel to the middle of the view
        p = self.pattern
        cell = self._base_cell() * self._zoom
        ox, oy = self._centered_origin(cell)
        grid_w = cell * p.width
        grid_h = cell if self._isolated else cell * p.height
        half_w, half_h = self.width() / 2, self.height() / 2

        pan_x = max(half_w - grid_w - ox, min(half_w - ox, self._pan.x()))
        if self._isolated:
            pan_y = 0.0  # the row stays vertically centered
        else:
            pan_y = max(half_h - grid_h - oy, min(half_h - oy, self._pan.y()))
        self._pan = QPointF(pan_x, pan_y)

    def _zoom_at(self, pos: QPointF, factor: float) -> None:
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self._zoom * factor))
        if new_zoom == self._zoom:
            return

        cell, x0, y0 = self._geometry()
        gx = (pos.x() - x0) / cell  # grid-space point under the cursor, in cells
        gy = (pos.y() - y0) / cell

        self._zoom = new_zoom
        new_cell = self._base_cell() * new_zoom
        ox, oy = self._centered_origin(new_cell)
        self._pan = QPointF(
            pos.x() - gx * new_cell - ox,
            pos.y() - gy * new_cell - oy,
        )
        self._clamp_pan()
        self.update()

    # Drawing cells
    def _apply_stroke(self, pos: QPointF) -> None:
        if self._stroke is None:
            return
        target = self._raw_cell_at(pos)
        start = self._last_cell if self._last_cell is not None else target
        self._last_cell = target

        changed = False
        for row, col in line_cells(start, target):
            changed |= self._paint_cell(row, col)
        if changed:
            self.update()  # once per mouse event, not call

    def _paint_cell(self, row: int, col: int) -> bool:
        p = self.pattern
        if not (0 <= row < p.height and 0 <= col < p.width):
            return False

        if self._stroke == ERASE:
            value = 0
        else:
            size = len(p.palette)
            value = p.index_for(self.active_color)
            if len(p.palette) != size:
                self.paletteChanged.emit()

        old = p.cells[row][col]
        if p.set_cell(row, col, value):
            self._stroke_changes[(row, col)] = (old, value)
            if self._image is not None:
                self._image.setPixelColor(
                    col, p.height - 1 - row, QColor(p.palette[value])
                )
            return True
        return False

    def remove_unused_colors(self) -> None:
        if self.pattern.remove_unused_colors():
            self._image = None
            self.update()
            self.paletteChanged.emit()

    # Drawing grid
    def set_background(self, color: str) -> None:
        color = color.lower()
        if color != self.pattern.palette[0]:
            self.undo_stack.push(SetBackgroundCommand(self.pattern, color))

    def _paint_row_focus(self, painter: QPainter, cell: float, x0: float, y0: float):
        p = self.pattern
        width = cell * p.width
        y = y0 + (p.height - 1 - p.current_row) * cell
        grid_bottom = y0 + p.height * cell

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, DIM_ALPHA))
        painter.drawRect(QRectF(x0, y0, width, y - y0))
        painter.drawRect(QRectF(x0, y + cell, width, grid_bottom - y - cell))

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(ACCENT), 2))
        painter.drawRect(QRectF(x0, y, width, cell))

    def _paint_guide_lines(
        self,
        painter: QPainter,
        cell: float,
        x0: float,
        y0: float,
        target: QRectF,
        first_col: int,
        last_col: int,
        first_row: int,
        last_row: int,
    ):
        p = self.pattern
        step = next(
            (s for s in GUIDE_STEPS if s * cell >= GUIDE_MIN_SPACING), GUIDE_STEPS[-1]
        )
        lines = [
            QLineF(x0 + c * cell, target.top(), x0 + c * cell, target.bottom())
            for c in range(first_col, last_col + 2)
            if 0 < c < p.width and (p.width - c) % step == 0
        ]
        lines += [
            QLineF(target.left(), y0 + r * cell, target.right(), y0 + r * cell)
            for r in range(first_row, last_row + 2)
            if 0 < r < p.height and (p.height - r) % step == 0
        ]
        if lines:
            painter.setPen(QPen(QColor(GUIDE), GUIDE_WIDTH))
            painter.drawLines(lines)

    def _paint_row_numbers(
        self,
        painter: QPainter,
        cell: float,
        x0: float,
        y0: float,
        first: int,
        last: int,
    ):
        p = self.pattern
        step = next(
            (s for s in LABEL_STEPS if s * cell >= LABEL_MIN_SPACING), LABEL_STEPS[-1]
        )
        pixel_size = int(max(9, min(LABEL_MAX_FONT, cell * 0.55)))
        normal = painter.font()
        normal.setPixelSize(pixel_size)
        bold = painter.font()
        bold.setPixelSize(pixel_size)
        bold.setBold(True)

        grid_left = x0
        grid_right = x0 + cell * p.width
        box_h = max(cell, pixel_size * 1.6)
        box_w = LABEL_MARGIN - LABEL_GAP

        for screen_row in range(first, last + 1):
            row = p.height - 1 - screen_row  # row 0 is the bottom row
            number = row + 1
            is_current = self._viewer and row == p.current_row
            if number % step and not is_current:
                continue

            top = y0 + screen_row * cell + cell / 2 - box_h / 2
            if number % 2:  # odd: right side
                box = QRectF(grid_right + LABEL_GAP, top, box_w, box_h)
                align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            else:  # even: left side
                box = QRectF(grid_left - LABEL_GAP - box_w, top, box_w, box_h)
                align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

            painter.setFont(bold if is_current else normal)
            painter.setPen(QColor(ACCENT if is_current else TEXT_MUTED))
            painter.drawText(box, align, str(number))

    def _paint_markers(self, painter: QPainter, cell: float, x0: float, y0: float):
        p = self.pattern
        radius = max(2.0, cell * 0.3)
        width = max(1.5, cell * 0.1)
        halo = QPen(QColor(MARKER_HALO), width + 2)
        ring = QPen(QColor(MARKER_RING), width)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for row, col in p.markers:
            if self._isolated and row != p.current_row:
                continue
            cx = x0 + (col + 0.5) * cell
            cy = y0 + (p.height - 1 - row + 0.5) * cell
            if not (
                -cell <= cx <= self.width() + cell
                and -cell <= cy <= self.height() + cell
            ):
                continue
            center = QPointF(cx, cy)
            painter.setPen(halo)
            painter.drawEllipse(center, radius, radius)
            painter.setPen(ring)
            painter.drawEllipse(center, radius, radius)
        painter.restore()

    def paintEvent(self, event):
        p = self.pattern
        cell, x0, y0 = self._geometry()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(CANVAS_BACKGROUND))

        # Only the cells that are actually on screen
        first_col = max(0, int((0 - x0) // cell))
        last_col = min(p.width - 1, int((self.width() - x0) // cell))
        if self._isolated:
            first_row = last_row = p.height - 1 - p.current_row
        else:
            first_row = max(0, int((0 - y0) // cell))
            last_row = min(p.height - 1, int((self.height() - y0) // cell))
        if first_col > last_col or first_row > last_row:
            return

        source = QRectF(
            first_col, first_row, last_col - first_col + 1, last_row - first_row + 1
        )
        target = QRectF(
            x0 + first_col * cell,
            y0 + first_row * cell,
            source.width() * cell,
            source.height() * cell,
        )
        painter.drawImage(target, self._chart_image(), source)

        if cell >= GRID_LINE_MIN_CELL:
            painter.setPen(QPen(QColor(BORDER), 1))
            lines = [
                QLineF(x0 + c * cell, target.top(), x0 + c * cell, target.bottom())
                for c in range(first_col, last_col + 2)
            ]
            lines += [
                QLineF(target.left(), y0 + r * cell, target.right(), y0 + r * cell)
                for r in range(first_row, last_row + 2)
            ]
            painter.drawLines(lines)

        self._paint_guide_lines(
            painter, cell, x0, y0, target, first_col, last_col, first_row, last_row
        )
        self._paint_row_numbers(painter, cell, x0, y0, first_row, last_row)

        if self._viewer and not self._isolated:
            self._paint_row_focus(painter, cell, x0, y0)
        if self._viewer:
            self._paint_markers(painter, cell, x0, y0)

    # Input Events
    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = WHEEL_ZOOM_RATE ** event.angleDelta().y()
            self._zoom_at(event.position(), factor)
        else:
            delta = event.pixelDelta()
            if delta.isNull():  # regular mouse wheel: no pixel data
                delta = event.angleDelta() / 2

            if self._isolated:  # a row only scrolls sideways
                delta = QPointF(delta.x() or delta.y(), 0)
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
        self.setFocus()
        button = event.button()
        if button == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_pan_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if self._viewer:
            if button == Qt.MouseButton.LeftButton and not self._isolated:
                hit = self.cell_at(event.position())
                if hit is not None:
                    self.set_row(hit[0])
            return
        if self._stroke is not None:
            return
        if button == Qt.MouseButton.LeftButton:
            self._stroke = PAINT
        elif button == Qt.MouseButton.RightButton:
            self._stroke = ERASE
        else:
            return
        self._stroke_button = button
        self._last_cell = None
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

    def _finish_stroke(self) -> None:
        self._last_cell = None
        self._stroke_button = None
        changes, self._stroke_changes = self._stroke_changes, {}
        stroke, self._stroke = self._stroke, None
        if not changes:
            return
        palette = self.pattern.palette
        by_color = {
            pos: (palette[old], palette[new]) for pos, (old, new) in changes.items()
        }
        self.undo_stack.push(
            StrokeCommand(
                self.pattern, by_color, "Paint" if stroke == PAINT else "Erase"
            )
        )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.unsetCursor()
            return
        if event.button() == self._stroke_button:
            self._finish_stroke()

    def contextMenuEvent(self, event):
        if not self._viewer:
            event.ignore()  # in edit mode, right-click erases
            return
        hit = self.cell_at(QPointF(event.pos()))
        if hit is None or (self._isolated and hit[0] != self.pattern.current_row):
            event.ignore()
            return

        row, col = hit
        has_marker = (row, col) in self.pattern.markers
        menu = QMenu(self)
        toggle = menu.addAction(
            "Remove Stitch Marker" if has_marker else "Add Stitch Marker"
        )
        toggle.triggered.connect(lambda: self.toggle_marker(row, col))
        menu.addSeparator()
        clear = menu.addAction("Clear All Markers")
        clear.setEnabled(bool(self.pattern.markers))
        clear.triggered.connect(self.clear_markers)
        menu.exec(event.globalPos())
