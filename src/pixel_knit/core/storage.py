import json
import os
import re
from pathlib import Path

from pixel_knit.core.pattern import Pattern

EXTENSION = ".pknit"
FILE_FILTER = "Pixel Knit Patterns (*.pknit)"

FORMAT_NAME = "pixel-knit"
FORMAT_VERSION = 1
MAX_DIMENSION = 1000

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class PatternFileError(Exception):
    pass


def write_atomic(path: str, data: dict) -> None:
    target = Path(path)
    # Write to a temp file first, then swap it in, so a crash or full disk
    # mid-save can't leave a half-written (corrupt) pattern behind.
    temp = target.with_name(target.name + ".tmp")
    temp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temp, target)


def pattern_to_dict(pattern: Pattern) -> dict:
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "width": pattern.width,
        "height": pattern.height,
        "palette": pattern.palette,
        "cells": pattern.cells,
        "current_row": pattern.current_row,
    }


def save_pattern(pattern: Pattern, path: str) -> None:
    write_atomic(path, pattern_to_dict(pattern))


def save_current_row(path: str, row: int) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format") != FORMAT_NAME:
        raise ValueError("not a pattern file")
    data["current_row"] = row
    write_atomic(path, data)


def load_pattern(path: str) -> Pattern:
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
    except OSError as err:
        raise PatternFileError(f"The file couldn't be read: {err.strerror or err}")
    except ValueError:
        raise PatternFileError("The file isn't valid pattern data.")

    return _parse(data)


def _parse(data) -> Pattern:
    if not isinstance(data, dict) or data.get("format") != FORMAT_NAME:
        raise PatternFileError("This doesn't look like a Pixel Knit pattern.")

    version = data.get("version")
    if not isinstance(version, int) or version < 1:
        raise PatternFileError("The file has no valid version number.")
    if version > FORMAT_VERSION:
        raise PatternFileError(
            "This pattern was made with a newer version of Pixel Knit."
        )

    width, height = data.get("width"), data.get("height")
    palette, cells = data.get("palette"), data.get("cells")

    if not (_is_dimension(width) and _is_dimension(height)):
        raise PatternFileError("The pattern's size is invalid.")

    if (
        not isinstance(palette, list)
        or not palette
        or not all(isinstance(c, str) and _HEX_COLOR.match(c) for c in palette)
    ):
        raise PatternFileError("The pattern's palette is invalid.")
    palette = [c.lower() for c in palette]

    if not isinstance(cells, list) or len(cells) != height:
        raise PatternFileError("The pattern's grid doesn't match its size.")
    for row in cells:
        if (
            not isinstance(row, list)
            or len(row) != width
            or not all(isinstance(i, int) and 0 <= i < len(palette) for i in row)
        ):
            raise PatternFileError("The pattern's grid contains invalid cells.")

    assert isinstance(width, int) and isinstance(height, int)
    row = data.get("current_row", 0)
    if not isinstance(row, int) or not 0 <= row < height:
        row = 0

    return Pattern(
        width=width, height=height, palette=palette, cells=cells, current_row=row
    )


def _is_dimension(value) -> bool:
    return isinstance(value, int) and 1 <= value <= MAX_DIMENSION
