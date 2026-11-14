from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox

from pixel_knit.core.storage import MAX_DIMENSION

MIN_SIZE = 2
DEFAULT_SIZE = 17


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")

        self._width = self._make_spinbox()
        self._height = self._make_spinbox()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("Width", self._width)
        form.addRow("Height", self._height)
        form.addRow(buttons)

    @staticmethod
    def _make_spinbox() -> QSpinBox:
        spinbox = QSpinBox()
        spinbox.setRange(MIN_SIZE, MAX_DIMENSION)
        spinbox.setValue(DEFAULT_SIZE)
        return spinbox

    @property
    def grid_size(self) -> tuple[int, int]:
        return self._width.value(), self._height.value()
