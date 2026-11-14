from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

PANEL_WIDTH = 240
SWATCH_SIZE = 24
SWATCH_COLUMNS = 7
SV_HEIGHT = 150
HUE_HEIGHT = 16
PICKER_GAP = 12


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


# Saturation/value square with a hue bar underneath
class ColorPicker(QWidget):

    colorChanged = Signal(str)  # "#rrggbb"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(SV_HEIGHT + PICKER_GAP + HUE_HEIGHT)
        self._hue = 0.0
        self._sat = 0.0
        self._val = 0.13
        self._drag: str | None = None

    def color_hex(self) -> str:
        return QColor.fromHsvF(self._hue, self._sat, self._val).name()

    def set_color(self, color: str) -> None:
        qcolor = QColor(color)
        if not qcolor.isValid():
            return
        hue = qcolor.hueF()
        sat = qcolor.saturationF()
        val = qcolor.valueF()
        if hue >= 0:  # greys have no hue
            self._hue = hue
        self._sat, self._val = sat, val
        self.update()

    # geometry helpers
    def _sv_rect(self) -> QRectF:
        return QRectF(0, 0, self.width(), SV_HEIGHT)

    def _hue_rect(self) -> QRectF:
        return QRectF(0, SV_HEIGHT + PICKER_GAP, self.width(), HUE_HEIGHT)

    # painting stuff
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_sv(painter)
        self._paint_hue(painter)

    def _paint_sv(self, painter: QPainter) -> None:
        sv = self._sv_rect()
        clip = QPainterPath()
        clip.addRoundedRect(sv, 6, 6)
        painter.setClipPath(clip)

        painter.fillRect(sv, QColor.fromHsvF(self._hue, 1.0, 1.0))

        white = QLinearGradient(sv.left(), 0, sv.right(), 0)
        white.setColorAt(0, QColor(255, 255, 255, 255))
        white.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(sv, QBrush(white))

        black = QLinearGradient(0, sv.top(), 0, sv.bottom())
        black.setColorAt(0, QColor(0, 0, 0, 0))
        black.setColorAt(1, QColor(0, 0, 0, 255))
        painter.fillRect(sv, QBrush(black))
        painter.setClipping(False)

        center = QPointF(self._sat * sv.width(), (1 - self._val) * sv.height())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 160), 3))
        painter.drawEllipse(center, 6, 6)
        painter.setPen(QPen(QColor("white"), 1.5))
        painter.drawEllipse(center, 6, 6)

    def _paint_hue(self, painter: QPainter) -> None:
        bar = self._hue_rect()
        gradient = QLinearGradient(bar.left(), 0, bar.right(), 0)
        for i in range(7):
            gradient.setColorAt(i / 6, QColor.fromHsvF(min(i / 6, 0.999), 1, 1))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(bar, 5, 5)

        x = self._hue * bar.width()
        handle = QRectF(x - 3, bar.top() - 3, 6, bar.height() + 6)
        painter.setPen(QPen(QColor(0, 0, 0, 160), 1))
        painter.setBrush(QColor("white"))
        painter.drawRoundedRect(handle, 3, 3)

    def mousePressEvent(self, event):
        pos = event.position()
        if self._hue_rect().adjusted(0, -4, 0, 4).contains(pos):
            self._drag = "hue"
        elif self._sv_rect().contains(pos):
            self._drag = "sv"
        else:
            return
        self._update_from(pos)

    def mouseMoveEvent(self, event):
        if self._drag:
            self._update_from(event.position())

    def mouseReleaseEvent(self, event):
        self._drag = None

    def _update_from(self, pos: QPointF) -> None:
        width = max(1, self.width())
        if self._drag == "hue":
            self._hue = _clamp01(pos.x() / width)
        else:
            self._sat = _clamp01(pos.x() / width)
            self._val = 1 - _clamp01(pos.y() / SV_HEIGHT)
        self.update()
        self.colorChanged.emit(self.color_hex())


class PalettePanel(QWidget):
    colorSelected = Signal(str)  # "#rrggbb"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("palettePanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(PANEL_WIDTH)

        self._active = "#222222"
        self._swatches: list[QPushButton] = []

        self._build_ui()
        self._set_active(self._active, sync_picker=True)

    @property
    def active_color(self) -> str:
        return self._active

    def set_palette(self, colors: list[str]) -> None:
        """Show swatches for these colors (the background is excluded by the caller)."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget:
                widget.deleteLater()
        self._swatches.clear()

        for i, color in enumerate(colors):
            swatch = QPushButton()
            swatch.setObjectName("swatch")
            swatch.setCheckable(True)
            swatch.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
            swatch.setToolTip(color)
            swatch.setProperty("color", color)
            swatch.setStyleSheet(
                f"QPushButton#swatch {{ background: {color}; padding: 0;"
                " border: 1px solid #ddd5cc; border-radius: 5px; }"
                "QPushButton#swatch:checked { border: 2px solid #c2566b; }"
            )
            swatch.clicked.connect(lambda _=False, c=color: self._on_swatch_clicked(c))
            self._grid.addWidget(swatch, i // SWATCH_COLUMNS, i % SWATCH_COLUMNS)
            self._swatches.append(swatch)
        self._refresh_selection()

    def _build_ui(self) -> None:
        palette_heading = QLabel("PALETTE")
        palette_heading.setObjectName("sectionHeading")
        self._grid = QGridLayout()
        self._grid.setSpacing(6)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        color_heading = QLabel("COLOR")
        color_heading.setObjectName("sectionHeading")
        self.picker = ColorPicker()
        self.picker.colorChanged.connect(self._on_picker_changed)

        self.preview = QWidget()
        self.preview.setFixedSize(32, 32)
        self.hex_edit = QLineEdit()
        self.hex_edit.setObjectName("hexEdit")
        self.hex_edit.setMaxLength(7)
        self.hex_edit.editingFinished.connect(self._on_hex_entered)
        hex_row = QHBoxLayout()
        hex_row.setSpacing(10)
        hex_row.addWidget(self.preview)
        hex_row.addWidget(self.hex_edit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(palette_heading)
        layout.addLayout(self._grid)
        layout.addSpacing(16)
        layout.addWidget(color_heading)
        layout.addWidget(self.picker)
        layout.addLayout(hex_row)
        layout.addStretch(1)

    # state management
    def _set_active(self, color: str, *, sync_picker: bool) -> None:
        self._active = color
        if sync_picker:
            self.picker.set_color(color)
        self.hex_edit.setText(color)
        self.preview.setStyleSheet(
            f"background: {color}; border: 1px solid #ddd5cc; border-radius: 6px;"
        )
        self._refresh_selection()

    def _refresh_selection(self) -> None:
        for swatch in self._swatches:
            swatch.setChecked(swatch.property("color") == self._active)

    # input handling
    def _on_swatch_clicked(self, color: str) -> None:
        self._set_active(color, sync_picker=True)
        self.colorSelected.emit(color)

    def _on_picker_changed(self, color: str) -> None:
        self._set_active(color, sync_picker=False)
        self.colorSelected.emit(color)

    def _on_hex_entered(self) -> None:
        text = self.hex_edit.text().strip()
        if not text.startswith("#"):
            text = "#" + text
        color = QColor(text)
        if not color.isValid():
            self.hex_edit.setText(self._active)
            return
        self._set_active(color.name(), sync_picker=True)
        self.colorSelected.emit(color.name())
