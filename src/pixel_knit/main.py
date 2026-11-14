import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from pixel_knit.ui.main_window import MainWindow

STYLE_PATH = Path(__file__).parent / "resources" / "style.qss"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PixelKnit")
    app.setStyleSheet(STYLE_PATH.read_text(encoding="utf-8"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
