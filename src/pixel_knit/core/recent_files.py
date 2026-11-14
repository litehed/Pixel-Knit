from pathlib import Path

from PySide6.QtCore import QSettings

MAX_RECENT = 10
_KEY = "recent_projects"


def load_recent() -> list[str]:
    paths = QSettings().value(_KEY, [], type=list)
    if not isinstance(paths, list):
        return []
    return [p for p in paths if Path(p).exists()]


def add_recent(path: str) -> None:
    path = str(Path(path).resolve())
    items = [p for p in load_recent() if p != path]
    items.insert(0, path)
    QSettings().setValue(_KEY, items[:MAX_RECENT])


def remove_recent(path: str) -> None:
    QSettings().setValue(_KEY, [p for p in load_recent() if p != path])
