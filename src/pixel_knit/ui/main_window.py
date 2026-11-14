from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QHBoxLayout,
)
from PySide6.QtGui import QAction, QKeySequence

from pixel_knit.core.recent_files import load_recent, remove_recent
from pixel_knit.ui.start_screen import StartScreen
from pixel_knit.core.pattern import Pattern
from pixel_knit.ui.grid_canvas import ZOOM_STEP, GridCanvas
from pixel_knit.ui.new_project_dialog import NewProjectDialog
from pixel_knit.ui.palette_panel import PalettePanel

WINDOW_NAME = "Pixel Knit"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(900, 700)

        self.current_path: str | None = None

        self.start_screen = StartScreen()
        self.start_screen = StartScreen()
        self.canvas = GridCanvas()
        self.palette_panel = PalettePanel()

        self.editor = QWidget()
        editor_layout = QHBoxLayout(self.editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        editor_layout.addWidget(self.canvas, 1)
        editor_layout.addWidget(self.palette_panel)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.start_screen)
        self.stack.addWidget(self.editor)
        self.setCentralWidget(self.stack)

        self.palette_panel.colorSelected.connect(self.canvas.set_active_color)
        self.canvas.paletteChanged.connect(self._refresh_palette)
        self.canvas.set_active_color(self.palette_panel.active_color)

        self.start_screen.newRequested.connect(self.new_project)
        self.start_screen.openRequested.connect(self.open_dialog)
        self.start_screen.recentChosen.connect(self.open_project)
        self.start_screen.recentRemoveRequested.connect(self._remove_recent)

        self._build_menus()
        self._show_start_screen()

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        open_act = QAction("Open...", self)
        open_act.setShortcut(QKeySequence(QKeySequence.StandardKey.Open))
        file_menu.addAction(open_act)
        self.close_act = QAction("Close Project", self)
        self.close_act.setShortcut(QKeySequence(QKeySequence.StandardKey.Close))
        self.close_act.triggered.connect(self._show_start_screen)
        file_menu.addAction(self.close_act)
        view_menu = self.menuBar().addMenu("&View")

        self.zoom_in_act = QAction("Zoom In", self)
        self.zoom_in_act.setShortcut(QKeySequence(QKeySequence.StandardKey.ZoomIn))
        self.zoom_in_act.triggered.connect(lambda: self.canvas.zoom_by(ZOOM_STEP))

        self.zoom_out_act = QAction("Zoom Out", self)
        self.zoom_out_act.setShortcut(QKeySequence(QKeySequence.StandardKey.ZoomOut))
        self.zoom_out_act.triggered.connect(lambda: self.canvas.zoom_by(1 / ZOOM_STEP))

        self.fit_act = QAction("Fit to Window", self)
        self.fit_act.setShortcut(QKeySequence("Ctrl+0"))
        self.fit_act.triggered.connect(self.canvas.reset_view)

        view_menu.addActions([self.zoom_in_act, self.zoom_out_act, self.fit_act])

        self._editor_actions = [
            self.close_act,
            self.zoom_in_act,
            self.zoom_out_act,
            self.fit_act,
        ]

    def _remove_recent(self, path):
        remove_recent(path)
        self.start_screen.set_recent_projects(load_recent())

    def _show_start_screen(self):
        self.start_screen.set_recent_projects(load_recent())
        self.stack.setCurrentWidget(self.start_screen)
        self.setWindowTitle(WINDOW_NAME)
        self.statusBar().clearMessage()
        for act in self._editor_actions:
            act.setEnabled(False)

    # Project actions
    def new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec():
            width, height = dialog.grid_size
            self._show_editor(Pattern(width=width, height=height))

    def _show_editor(self, pattern: Pattern):
        self.canvas.set_pattern(pattern)
        self._refresh_palette()
        self.stack.setCurrentWidget(self.editor)
        self.setWindowTitle(f"Untitled - {WINDOW_NAME}")
        for act in self._editor_actions:
            act.setEnabled(True)
    
    def _refresh_palette(self):
        self.palette_panel.set_palette(self.canvas.pattern.palette)

    def open_dialog(self):
        pass

    def open_project(self, path: str):
        pass
