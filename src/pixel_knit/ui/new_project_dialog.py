from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")

        self._width = QSpinBox()
        self._width.setRange(2, 200)
        self._width.setValue(17)
        self._height = QSpinBox()
        self._height.setRange(2, 200)
        self._height.setValue(17)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("Width", self._width)
        form.addRow("Height", self._height)
        form.addRow(buttons)

    @property
    def grid_size(self) -> tuple[int, int]:
        return self._width.value(), self._height.value()
