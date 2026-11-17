from importlib.resources import files
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from pixel_knit.ui.main_window import MainWindow
from pixel_knit.ui.theme import light_palette


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("PixelKnit")
    app.setApplicationName("PixelKnit")
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setPalette(light_palette())
    try:
        stylesheet = files("pixel_knit").joinpath("resources", "style.qss")
        app.setStyleSheet(stylesheet.read_text(encoding="utf-8"))
    except OSError:
        print("Pixel Knit: style.qss not found, using default styling", file=sys.stderr)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
