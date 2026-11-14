from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
)

from pixel_knit.core.pattern import Pattern
from pixel_knit.core.recent_files import load_recent, remove_recent
from pixel_knit.core.storage import (
    EXTENSION,
    FILE_FILTER,
    PatternFileError,
    load_pattern,
    save_pattern,
)
from pixel_knit.ui.grid_canvas import ZOOM_STEP, GridCanvas
from pixel_knit.ui.new_project_dialog import NewProjectDialog
from pixel_knit.ui.palette_panel import PalettePanel
from pixel_knit.ui.start_screen import StartScreen

WINDOW_NAME = "Pixel Knit"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(900, 700)

        self.current_path: str | None = None
        self._dirty = False

        self.start_screen = StartScreen()
        self.canvas = GridCanvas()
        self.palette_panel = PalettePanel()

        self.palette_dock = QDockWidget("Palette", self)
        self.palette_dock.setObjectName("paletteDock")
        self.palette_dock.setWidget(self.palette_panel)
        self.palette_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.palette_dock)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.start_screen)
        self.stack.addWidget(self.canvas)
        self.setCentralWidget(self.stack)

        self.palette_panel.colorSelected.connect(self.canvas.set_active_color)
        self.canvas.paletteChanged.connect(self._refresh_palette)
        self.canvas.patternEdited.connect(self._on_pattern_edited)
        self.canvas.set_active_color(self.palette_panel.active_color)

        self.start_screen.newRequested.connect(self.new_project)
        self.start_screen.openRequested.connect(self.open_dialog)
        self.start_screen.recentChosen.connect(self.open_project)
        self.start_screen.recentRemoveRequested.connect(self._remove_recent)

        self._build_menus()
        self._show_start_screen()

    # Menu and toolbar setup
    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")

        new_act = QAction("New...", self)
        new_act.setShortcut(QKeySequence(QKeySequence.StandardKey.New))
        new_act.triggered.connect(self.new_project)

        open_act = QAction("Open...", self)
        open_act.setShortcut(QKeySequence(QKeySequence.StandardKey.Open))
        open_act.triggered.connect(self.open_dialog)

        self.save_act = QAction("Save", self)
        self.save_act.setShortcut(QKeySequence(QKeySequence.StandardKey.Save))
        self.save_act.triggered.connect(self.save)

        self.save_as_act = QAction("Save As...", self)
        self.save_as_act.setShortcut(QKeySequence(QKeySequence.StandardKey.SaveAs))
        self.save_as_act.triggered.connect(self.save_as)

        file_menu.addActions([new_act, open_act])
        file_menu.addSeparator()
        file_menu.addActions([self.save_act, self.save_as_act])

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

        self.palette_act = self.palette_dock.toggleViewAction()
        view_menu.addActions([self.zoom_in_act, self.zoom_out_act, self.fit_act])
        view_menu.addAction(self.palette_act)

        # Actions that only make sense while a pattern is open
        self._editor_actions = [
            self.save_act,
            self.save_as_act,
            self.zoom_in_act,
            self.zoom_out_act,
            self.fit_act,
            self.palette_act,
        ]

    # Page transitions
    def _show_start_screen(self):
        self.start_screen.set_recent_projects(load_recent())
        self.stack.setCurrentWidget(self.start_screen)
        self.palette_dock.hide()
        self.current_path = None
        self._set_dirty(False)
        self.setWindowTitle(WINDOW_NAME)
        self.statusBar().clearMessage()
        for act in self._editor_actions:
            act.setEnabled(False)

    def _show_editor(self, pattern: Pattern, path: str | None):
        self.canvas.set_pattern(pattern)
        self._refresh_palette()
        self.palette_panel.reset_active_color()
        self.current_path = path
        self._set_dirty(False)
        self._update_title()
        self.stack.setCurrentWidget(self.canvas)
        self.palette_dock.show()
        for act in self._editor_actions:
            act.setEnabled(True)

    def _refresh_palette(self):
        # palette[0] is the background, so it isn't shown as a swatch
        self.palette_panel.set_palette(self.canvas.pattern.palette[1:])

    # project handling
    def new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec() and self._confirm_discard():
            width, height = dialog.grid_size
            self._show_editor(Pattern(width=width, height=height), None)

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open pattern", "", FILE_FILTER)
        if path:
            self.open_project(path)

    def open_project(self, path: str):
        if not self._confirm_discard():
            return
        try:
            pattern = load_pattern(path)
        except PatternFileError as err:
            QMessageBox.warning(self, WINDOW_NAME, f"Couldn't open that file.\n\n{err}")
            return
        self._show_editor(pattern, path)

    def _remove_recent(self, path: str):
        remove_recent(path)
        self.start_screen.set_recent_projects(load_recent())

    # Save handling
    def save(self) -> bool:
        if self.current_path is None:
            return self.save_as()
        return self._write(self.current_path)

    def save_as(self) -> bool:
        suggested = self.current_path or f"Untitled{EXTENSION}"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save pattern", suggested, FILE_FILTER
        )
        if not path:
            return False
        if not path.lower().endswith(EXTENSION):
            path += EXTENSION
        return self._write(path)

    def _write(self, path: str) -> bool:
        try:
            save_pattern(self.canvas.pattern, path)
        except OSError as err:
            QMessageBox.warning(self, WINDOW_NAME, f"Couldn't save the file.\n\n{err}")
            return False
        self.current_path = path
        self._set_dirty(False)
        self._update_title()
        return True

    # Handling edits and saving
    def _on_pattern_edited(self):
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool):
        self._dirty = dirty
        self.setWindowModified(dirty)

    def _update_title(self):
        name = Path(self.current_path).stem if self.current_path else "Untitled"
        # Qt replaces the [*] marker with an asterisk while the window is modified
        self.setWindowTitle(f"{name}[*] - {WINDOW_NAME}")

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        name = Path(self.current_path).stem if self.current_path else "Untitled"
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(WINDOW_NAME)
        box.setText(f"Save changes to {name}?")
        box.setInformativeText("Your changes will be lost if you don't save them.")
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        choice = box.exec()
        if choice == QMessageBox.StandardButton.Save:
            return self.save()
        return choice == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
