# Shared UI colors
from PySide6.QtGui import QColor, QPalette

CANVAS_BACKGROUND = "#faf8f5"
BORDER = "#ddd5cc"
ACCENT = "#c2566b"

TEXT = "#2b2623"
TEXT_MUTED = "#8a817a"
TEXT_DISABLED = "#b9b0a8"
SURFACE = "#ffffff"
SURFACE_HOVER = "#f6f1ec"
HOVER = "#e8e1da"


def light_palette() -> QPalette:
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: CANVAS_BACKGROUND,
        QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: SURFACE,
        QPalette.ColorRole.AlternateBase: SURFACE_HOVER,
        QPalette.ColorRole.Text: TEXT,
        QPalette.ColorRole.PlaceholderText: TEXT_MUTED,
        QPalette.ColorRole.Button: SURFACE,
        QPalette.ColorRole.ButtonText: TEXT,
        QPalette.ColorRole.ToolTipBase: SURFACE,
        QPalette.ColorRole.ToolTipText: TEXT,
        QPalette.ColorRole.Highlight: ACCENT,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.Link: ACCENT,
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(TEXT_DISABLED))
    return palette
