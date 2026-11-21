from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QKeySequence,
    QPixmap,
    QUndoGroup,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabBar,
    QTabWidget,
)

from pixel_knit.core import recovery
from pixel_knit.core.app_settings import AppSettings
from pixel_knit.core.pattern import Pattern
from pixel_knit.core.recent_files import add_recent, load_recent, remove_recent
from pixel_knit.core.storage import (
    EXTENSION,
    FILE_FILTER,
    PatternFileError,
    load_pattern,
    same_file,
    save_current_row,
    save_pattern,
)
from pixel_knit.ui.autosave import AutosaveManager
from pixel_knit.ui.grid_canvas import ZOOM_STEP, GridCanvas
from pixel_knit.ui.new_project_dialog import NewProjectDialog
from pixel_knit.ui.palette_panel import PalettePanel
from pixel_knit.ui.settings_dialog import SettingsDialog
from pixel_knit.ui.start_screen import StartScreen
from pixel_knit.ui.thumbnail import render_thumbnail

WINDOW_NAME = "Pixel Knit"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = AppSettings()
        self.resize(900, 700)

        self.start_screen = StartScreen()
        self.palette_panel = PalettePanel()

        self.palette_dock = QDockWidget("Palette", self)
        self.palette_dock.setObjectName("paletteDock")
        self.palette_dock.setWidget(self.palette_panel)
        self.palette_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.palette_dock)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("projectTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.addTab(self.start_screen, "Home")
        bar = self.tabs.tabBar()
        bar.setTabButton(0, QTabBar.ButtonPosition.LeftSide, None)
        bar.setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.setCentralWidget(self.tabs)

        self.palette_panel.colorSelected.connect(self._on_color_selected)
        self.palette_panel.backgroundRequested.connect(self._on_background_requested)
        self.tabs.tabCloseRequested.connect(self._close_tab)

        self.start_screen.newRequested.connect(self.new_project)
        self.start_screen.openRequested.connect(self.open_dialog)
        self.start_screen.recentChosen.connect(self.open_project)
        self.start_screen.recentRemoveRequested.connect(self._remove_recent)

        self.undo_group = QUndoGroup(self)
        # always empty keeps Undo/Redo disabled on Home tab
        self._home_stack = QUndoStack(self)
        self.undo_group.addStack(self._home_stack)

        self._pending_row_saves: set[GridCanvas] = set()
        self._row_save_timer = QTimer(self)
        self._row_save_timer.setSingleShot(True)
        self._row_save_timer.setInterval(500)
        self._row_save_timer.timeout.connect(self._flush_row_saves)

        self.autosave = AutosaveManager(self)

        self._build_menus()
        self._build_toolbar()
        self._restore_window_layout()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._thumb_cache: dict[str, tuple[float, QPixmap]] = {}
        self._palette_wanted = self.settings.palette_visible
        self._on_tab_changed(0)
        self.palette_dock.visibilityChanged.connect(self._on_palette_visibility)
        QTimer.singleShot(0, self._offer_recovery)

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

        edit_menu = self.menuBar().addMenu("&Edit")
        undo_act = self.undo_group.createUndoAction(self)
        undo_act.setShortcut(QKeySequence(QKeySequence.StandardKey.Undo))
        redo_act = self.undo_group.createRedoAction(self)
        redo_act.setShortcut(QKeySequence(QKeySequence.StandardKey.Redo))
        edit_menu.addActions([undo_act, redo_act])

        self.settings_act = QAction("Settings...", self)
        self.settings_act.setShortcut(QKeySequence("Ctrl+,"))
        self.settings_act.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.settings_act.triggered.connect(self.open_settings)
        edit_menu.addSeparator()
        edit_menu.addAction(self.settings_act)

        view_menu = self.menuBar().addMenu("&View")

        self.zoom_in_act = QAction("Zoom In", self)
        self.zoom_in_act.setShortcut(QKeySequence(QKeySequence.StandardKey.ZoomIn))
        self.zoom_in_act.triggered.connect(lambda: self._zoom(ZOOM_STEP))

        self.zoom_out_act = QAction("Zoom Out", self)
        self.zoom_out_act.setShortcut(QKeySequence(QKeySequence.StandardKey.ZoomOut))
        self.zoom_out_act.triggered.connect(lambda: self._zoom(1 / ZOOM_STEP))

        self.fit_act = QAction("Fit to Window", self)
        self.fit_act.setShortcut(QKeySequence("Ctrl+0"))
        self.fit_act.triggered.connect(self._fit_view)

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

    def _build_toolbar(self):
        toolbar = self.addToolBar("View")
        toolbar.setObjectName("viewToolbar")
        toolbar.setMovable(False)

        self.viewer_act = QAction("View Mode", self)
        self.viewer_act.setCheckable(True)
        self.viewer_act.setShortcut(QKeySequence("V"))
        self.viewer_act.setToolTip("Follow the chart row by row (V)")
        self.viewer_act.triggered.connect(self._set_viewer_mode)

        self.isolate_act = QAction("Isolate Row", self)
        self.isolate_act.setCheckable(True)
        self.isolate_act.setShortcut(QKeySequence("I"))
        self.isolate_act.setToolTip("Show only the current row (I)")
        self.isolate_act.triggered.connect(self._set_isolated)

        self.row_down_act = QAction("Previous Row", self)
        self.row_down_act.setShortcut(QKeySequence("Down"))
        self.row_down_act.setToolTip("Previous row (Down)")
        self.row_down_act.triggered.connect(lambda: self._move_row(-1))

        self.row_up_act = QAction("Next Row", self)
        self.row_up_act.setShortcut(QKeySequence("Up"))
        self.row_up_act.setToolTip("Next row (Up)")
        self.row_up_act.triggered.connect(lambda: self._move_row(+1))

        self.row_label = QLabel()
        self.row_label.setObjectName("rowLabel")

        toolbar.addAction(self.viewer_act)
        toolbar.addAction(self.isolate_act)
        toolbar.addSeparator()
        toolbar.addAction(self.row_down_act)
        toolbar.addAction(self.row_up_act)
        toolbar.addWidget(self.row_label)

    def _set_viewer_mode(self, enabled: bool):
        canvas = self._current_canvas()
        if canvas is not None:
            canvas.set_viewer_mode(enabled)

    def _set_isolated(self, enabled: bool):
        canvas = self._current_canvas()
        if canvas is not None:
            canvas.set_isolated(enabled)

    def _move_row(self, delta: int):
        canvas = self._current_canvas()
        if canvas is not None:
            canvas.move_row(delta)

    def _sync_viewer_ui(self):
        canvas = self._current_canvas()
        viewing = canvas is not None and canvas.viewer_mode
        self.viewer_act.setEnabled(canvas is not None)
        self.viewer_act.setChecked(viewing)
        self.row_up_act.setEnabled(viewing)
        self.row_down_act.setEnabled(viewing)
        self.isolate_act.setEnabled(canvas is not None)
        self.isolate_act.setChecked(canvas is not None and canvas.isolated)
        if canvas is not None and viewing:
            self.row_label.setText(
                f"Row {canvas.current_row + 1} of {canvas.pattern.height}"
            )
        else:
            self.row_label.setText("")

    # Tab helpers
    def _current_canvas(self) -> GridCanvas | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, GridCanvas) else None

    @staticmethod
    def _display_name(canvas: GridCanvas) -> str:
        if canvas.path:
            return Path(canvas.path).stem
        if canvas.untitled_number > 1:
            return f"Untitled {canvas.untitled_number}"
        return "Untitled"

    def _refresh_tab(self, canvas: GridCanvas):
        marker = "*" if canvas.dirty else ""
        self.tabs.setTabText(
            self.tabs.indexOf(canvas), self._display_name(canvas) + marker
        )
        if canvas is self._current_canvas():
            self.setWindowTitle(f"{self._display_name(canvas)}[*] - {WINDOW_NAME}")
            self.setWindowModified(canvas.dirty)

    def _on_tab_changed(self, index: int):
        canvas = self._current_canvas()
        self.undo_group.setActiveStack(
            canvas.undo_stack if canvas is not None else self._home_stack
        )
        on_project = canvas is not None
        self.palette_dock.setVisible(on_project and self._palette_wanted)
        for act in self._editor_actions:
            act.setEnabled(on_project)
        self._sync_viewer_ui()

        if canvas is None:  # Home
            self.start_screen.set_recent_projects(self._recent_entries())
            self.setWindowTitle(WINDOW_NAME)
            self.setWindowModified(False)
            return
        self.palette_panel.set_active_color(canvas.active_color)
        canvas.setFocus()
        self._refresh_palette()
        self._refresh_tab(canvas)

    def _on_palette_visibility(self, visible: bool):
        if self._current_canvas() is not None and self.isVisible():
            self._palette_wanted = visible

    def _on_color_selected(self, color: str):
        canvas = self._current_canvas()
        if canvas:
            canvas.set_active_color(color)

    def _on_background_requested(self, color: str):
        canvas = self._current_canvas()
        if canvas:
            canvas.set_background(color)

    def _refresh_palette(self):
        canvas = self._current_canvas()
        if canvas:
            self.palette_panel.set_palette(canvas.pattern.palette[1:])
            self.palette_panel.set_background(canvas.pattern.palette[0])

    def _find_tab(self, path: str, ignore: GridCanvas | None = None) -> int | None:
        for i in range(self.tabs.count()):
            canvas = self.tabs.widget(i)
            if (
                isinstance(canvas, GridCanvas)
                and canvas is not ignore
                and canvas.path
                and same_file(canvas.path, path)
            ):
                return i
        return None

    def _next_untitled_number(self) -> int:
        taken = set()
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, GridCanvas) and tab.path is None:
                taken.add(tab.untitled_number)
        number = 1
        while number in taken:
            number += 1
        return number

    def _open_tab(self, pattern: Pattern, path: str | None) -> GridCanvas:
        canvas = GridCanvas(pattern)
        canvas.path = path
        if path is None:
            canvas.untitled_number = self._next_untitled_number()
        canvas.paletteChanged.connect(self._refresh_palette)
        canvas.undo_stack.cleanChanged.connect(
            lambda _clean, c=canvas: self._refresh_tab(c)
        )
        self.undo_group.addStack(canvas.undo_stack)
        canvas.viewerChanged.connect(self._sync_viewer_ui)
        canvas.rowChanged.connect(self._sync_viewer_ui)
        canvas.rowChanged.connect(lambda c=canvas: self._queue_row_save(c))
        self.autosave.watch(canvas)
        canvas.set_active_color(self.palette_panel.active_color)
        index = self.tabs.addTab(canvas, self._display_name(canvas))
        self.tabs.setCurrentIndex(index)
        return canvas

    def _close_tab(self, index: int):
        self._flush_row_saves()
        canvas = self.tabs.widget(index)
        if isinstance(canvas, GridCanvas) and self._confirm_discard(canvas):
            self.autosave.discard(canvas)
            self.tabs.removeTab(index)
            canvas.undo_stack.blockSignals(True)
            canvas.deleteLater()

    def _zoom(self, factor: float):
        canvas = self._current_canvas()
        if canvas is not None:
            canvas.zoom_by(factor)

    def _fit_view(self):
        canvas = self._current_canvas()
        if canvas is not None:
            canvas.reset_view()

    # project management
    def new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec():
            width, height = dialog.grid_size
            self._open_tab(Pattern(width=width, height=height), None)

    def open_settings(self):
        SettingsDialog(self).exec()

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open pattern", self.settings.last_folder, FILE_FILTER
        )
        if path:
            self.open_project(path)

    def open_project(self, path: str):
        existing = self._find_tab(path)
        if existing is not None:
            self.tabs.setCurrentIndex(existing)
            return
        try:
            pattern = load_pattern(path)
        except PatternFileError as err:
            QMessageBox.warning(self, WINDOW_NAME, f"Couldn't open that file.\n\n{err}")
            return
        add_recent(path)
        self.settings.last_folder = str(Path(path).parent)
        self._open_tab(pattern, path)

    def _remove_recent(self, path: str):
        remove_recent(path)
        self.start_screen.set_recent_projects(self._recent_entries())

    def _recent_entries(self) -> list[tuple[str, QPixmap | None]]:
        return [(path, self._thumbnail_for(path)) for path in load_recent()]

    def _thumbnail_for(self, path: str) -> QPixmap | None:
        try:
            mtime = Path(path).stat().st_mtime
            cached = self._thumb_cache.get(path)
            if cached and cached[0] == mtime:
                return cached[1]
            pixmap = render_thumbnail(load_pattern(path))
        except (OSError, PatternFileError):
            return None  # still list the file, just without a preview
        self._thumb_cache[path] = (mtime, pixmap)
        return pixmap

    # Saving
    def save(self) -> bool:
        canvas = self._current_canvas()
        return canvas is not None and self._save(canvas)

    def save_as(self) -> bool:
        canvas = self._current_canvas()
        return canvas is not None and self._save_as(canvas)

    def _save(self, canvas: GridCanvas) -> bool:
        if canvas.path is None:
            return self._save_as(canvas)
        return self._write(canvas, canvas.path)

    def _save_as(self, canvas: GridCanvas) -> bool:
        suggested = canvas.path or str(
            Path(self.settings.last_folder) / f"{self._display_name(canvas)}{EXTENSION}"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save pattern", suggested, FILE_FILTER
        )
        if not path:
            return False
        if not path.lower().endswith(EXTENSION):
            path += EXTENSION
        if self._find_tab(path, ignore=canvas) is not None:
            QMessageBox.warning(
                self,
                WINDOW_NAME,
                f"{Path(path).name} is already open in another tab.\n\n"
                "Close that tab first, or save under a different name.",
            )
            return False
        return self._write(canvas, path)

    def _write(self, canvas: GridCanvas, path: str) -> bool:
        canvas.remove_unused_colors()
        try:
            save_pattern(canvas.pattern, path)
        except OSError as err:
            QMessageBox.warning(self, WINDOW_NAME, f"Couldn't save the file.\n\n{err}")
            return False

        canvas.path = path
        canvas.undo_stack.setClean()
        add_recent(path)
        self.settings.last_folder = str(Path(path).parent)
        self._refresh_tab(canvas)
        return True

    def _queue_row_save(self, canvas: GridCanvas):
        if canvas.path:
            self._pending_row_saves.add(canvas)
            self._row_save_timer.start()  # restarts the countdown

    def _flush_row_saves(self):
        self._row_save_timer.stop()
        pending, self._pending_row_saves = self._pending_row_saves, set()
        for canvas in pending:
            if canvas.path:
                try:
                    save_current_row(canvas.path, canvas.current_row)
                except (OSError, ValueError):
                    pass

    # Handling unsaved changes
    def _offer_recovery(self):
        entries = recovery.find_recoverable()
        if not entries:
            return
        names = "\n".join(
            "• " + (Path(e.original_path).stem if e.original_path else "Untitled")
            for e in entries
        )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(WINDOW_NAME)
        box.setText("Pixel Knit closed unexpectedly. Restore your unsaved work?")
        box.setInformativeText(names)
        restore_btn = box.addButton("Restore", QMessageBox.ButtonRole.AcceptRole)
        discard_btn = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(restore_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked is discard_btn:
            for entry in entries:
                recovery.delete(entry.session_id)
        elif clicked is restore_btn:
            for entry in entries:
                path = entry.original_path
                if path is not None and not Path(path).exists():
                    path = None  # the file was moved or deleted
                canvas = self._open_tab(entry.pattern, path)
                canvas.session_id = entry.session_id  # keep its recovery file alive
                canvas.undo_stack.resetClean()  # mark as unsaved

    def _confirm_discard(self, canvas: GridCanvas) -> bool:
        if not canvas.dirty:
            return True
        self.tabs.setCurrentWidget(canvas)  # show which project is being asked about
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(WINDOW_NAME)
        box.setText(f"Save changes to {self._display_name(canvas)}?")
        box.setInformativeText("Your changes will be lost if you don't save them.")
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        choice = box.exec()
        if choice == QMessageBox.StandardButton.Save:
            return self._save(canvas)
        return choice == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent):
        for i in range(self.tabs.count()):
            canvas = self.tabs.widget(i)
            if isinstance(canvas, GridCanvas) and not self._confirm_discard(canvas):
                event.ignore()
                return
        for i in range(self.tabs.count()):
            canvas = self.tabs.widget(i)
            if isinstance(canvas, GridCanvas):
                self.autosave.discard(canvas)
                canvas.undo_stack.blockSignals(True)
        self._flush_row_saves()
        self._save_window_layout()
        event.accept()

    def _restore_window_layout(self):
        geometry = self.settings.window_geometry
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)
        state = self.settings.window_state
        if not state.isEmpty():
            self.restoreState(state)

    def _save_window_layout(self):
        self.settings.window_geometry = self.saveGeometry()
        self.settings.window_state = self.saveState()
        self.settings.palette_visible = self._palette_wanted
