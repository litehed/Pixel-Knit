from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QPixmap

import pixel_knit.ui.thumbnail

CONTENT_WIDTH = 480


class StartScreen(QWidget):
    newRequested = Signal()
    openRequested = Signal()
    recentChosen = Signal(str)
    recentRemoveRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("startScreen")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._build_ui()
        self.set_recent_projects([])

    def set_recent_projects(self, entries: list[tuple[str, QPixmap | None]]) -> None:
        self.recent_list.clear()
        for path, thumbnail in entries:
            self._add_recent_item(path, thumbnail)

        has_items = self.recent_list.count() > 0
        self.recent_list.setVisible(has_items)
        self.empty_label.setVisible(not has_items)

    def _build_ui(self) -> None:
        content = QWidget()
        content.setFixedWidth(CONTENT_WIDTH)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(self._build_header())
        layout.addSpacing(28)
        layout.addLayout(self._build_actions())
        layout.addSpacing(36)
        layout.addLayout(self._build_recent_section())

        outer = QVBoxLayout(self)
        outer.addStretch(1)
        outer.addWidget(content, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(2)

    def _build_header(self) -> QVBoxLayout:
        title = QLabel("Pixel Knit")
        title.setObjectName("startTitle")

        subtitle = QLabel("Design and follow knitting charts")
        subtitle.setObjectName("startSubtitle")

        header = QVBoxLayout()
        header.setSpacing(4)
        header.addWidget(title)
        header.addWidget(subtitle)
        return header

    def _build_actions(self) -> QHBoxLayout:
        new_btn = QPushButton("New Project")
        new_btn.setObjectName("primaryButton")
        new_btn.clicked.connect(self.newRequested)

        open_btn = QPushButton("Open Project")
        open_btn.clicked.connect(self.openRequested)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addWidget(new_btn)
        actions.addWidget(open_btn)
        return actions

    def _build_recent_section(self) -> QVBoxLayout:
        heading = QLabel("RECENT")
        heading.setObjectName("sectionHeading")

        self.empty_label = QLabel("Projects you open or save will show up here.")
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(120)

        self.recent_list = QListWidget()
        self.recent_list.setObjectName("recentList")
        self.recent_list.setMaximumHeight(280)
        self.recent_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.recent_list.itemActivated.connect(self._on_item_activated)
        self.recent_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_list.customContextMenuRequested.connect(self._show_context_menu)

        section = QVBoxLayout()
        section.setSpacing(8)
        section.addWidget(heading)
        section.addWidget(self.empty_label)
        section.addWidget(self.recent_list)
        return section

    def _add_recent_item(self, path: str, thumbnail: QPixmap | None) -> None:
        name = QLabel(Path(path).stem)
        name.setObjectName("recentName")
        location = QLabel(str(Path(path).parent))
        location.setObjectName("recentPath")

        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(name)
        text.addWidget(location)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 8, 12, 8)
        row_layout.setSpacing(12)
        row_layout.addLayout(text, 1)
        if thumbnail is not None:
            preview = QLabel()
            preview.setObjectName("recentThumb")
            preview.setPixmap(thumbnail)
            row_layout.addWidget(
                preview,
                alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        item.setSizeHint(row.sizeHint())
        self.recent_list.addItem(item)
        self.recent_list.setItemWidget(item, row)

    # handlers for signals from the recent list
    def _on_item_activated(self, item: QListWidgetItem) -> None:
        self.recentChosen.emit(item.data(Qt.ItemDataRole.UserRole))

    def _show_context_menu(self, pos) -> None:
        item = self.recent_list.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        remove = menu.addAction("Remove from list")
        if menu.exec(self.recent_list.mapToGlobal(pos)) == remove:
            self.recentRemoveRequested.emit(item.data(Qt.ItemDataRole.UserRole))
