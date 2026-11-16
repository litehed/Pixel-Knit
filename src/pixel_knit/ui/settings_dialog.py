from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

NAV_WIDTH = 150

# Page titles for the sidebar; swap these out as real settings appear
PAGES = ["General", "Display", "Files"]


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(560, 380)

        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(NAV_WIDTH)

        self.pages = QStackedWidget()
        for title in PAGES:
            self.nav.addItem(title)
            self.pages.addWidget(self._build_page(title))
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self.nav)
        body.addWidget(self.pages, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(body, 1)
        layout.addWidget(buttons)

    @staticmethod
    def _build_page(title: str) -> QWidget:
        heading = QLabel(title)
        heading.setObjectName("settingsPageTitle")

        placeholder = QLabel("Nothing to configure here yet.")
        placeholder.setObjectName("emptyState")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(placeholder, 1)
        return page
