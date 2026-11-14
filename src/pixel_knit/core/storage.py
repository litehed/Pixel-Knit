import json
from dataclasses import asdict
from pathlib import Path


EXTENSION = ".pknit"
FILE_FILTER = "Pixel Knit patterns (*.pknit)"


# def save_pattern(pattern: Pattern, path: str) -> None:
#     Path(path).write_text(json.dumps(asdict(pattern)), encoding="utf-8")

    
# def load_pattern(path: str) -> Pattern:
#     return Pattern(**json.loads(Path(path).read_text(encoding="utf-8")))