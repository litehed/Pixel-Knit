from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout
from PySide6.QtGui import QAction, QKeySequence


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Knit Patterns")

        self._build_menus()

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        open_act = QAction("Open...", self)
        open_act.setShortcut(QKeySequence(QKeySequence.StandardKey.Open))
        open_act.triggered.connect(self.open_pattern)
        file_menu.addAction(open_act)

    def open_pattern(self): ...
    def _on_row_changed(self, row):
        self.statusBar().showMessage(f"Row {row + 1}")
