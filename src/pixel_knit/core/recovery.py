import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from pixel_knit.core.pattern import Pattern
from pixel_knit.core.storage import (
    PatternFileError,
    load_pattern,
    pattern_to_dict,
    write_atomic,
)

SUFFIX = ".recovery"


@dataclass
class RecoveryEntry:
    session_id: str
    original_path: str | None
    pattern: Pattern


def _recovery_dir() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    folder = Path(base) / "recovery"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _path_for(session_id: str) -> Path:
    return _recovery_dir() / (session_id + SUFFIX)


def write_snapshot(
    session_id: str, pattern: Pattern, original_path: str | None
) -> None:
    try:
        data = pattern_to_dict(pattern)
        data["recovery"] = {"original_path": original_path}
        write_atomic(str(_path_for(session_id)), data)
    except OSError:
        pass


def delete(session_id: str) -> None:
    try:
        _path_for(session_id).unlink(missing_ok=True)
    except OSError:
        pass


def find_recoverable() -> list[RecoveryEntry]:
    entries = []
    for file in sorted(_recovery_dir().glob("*" + SUFFIX)):
        try:
            pattern = load_pattern(str(file))
            meta = json.loads(file.read_text(encoding="utf-8")).get("recovery", {})
        except (PatternFileError, OSError, ValueError):
            file.unlink(missing_ok=True)  # unreadable, no restore
            continue
        entries.append(
            RecoveryEntry(
                file.name.removesuffix(SUFFIX), meta.get("original_path"), pattern
            )
        )
    return entries
