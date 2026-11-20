from dataclasses import dataclass, field

DEFAULT_COLOR = "#222222"


@dataclass
class Pattern:
    width: int = 17
    height: int = 17
    palette: list[str] = field(default_factory=lambda: ["#ffffff", DEFAULT_COLOR])
    cells: list[list[int]] = field(default_factory=list)
    current_row: int = 0

    def __post_init__(self):
        if not self.cells:
            self.cells = [[0] * self.width for _ in range(self.height)]

    def set_cell(self, row: int, col: int, value: int) -> bool:
        if self.cells[row][col] == value:
            return False
        self.cells[row][col] = value
        return True

    def index_for(self, color: str) -> int:
        color = color.lower()
        if color in self.palette:
            return self.palette.index(color)
        self.palette.append(color)
        return len(self.palette) - 1

    def remove_unused_colors(self) -> bool:
        used = {0}.union(*map(set, self.cells))
        if len(used) == len(self.palette):
            return False
        new_index: dict[int, int] = {}
        kept: list[str] = []
        for old, color in enumerate(self.palette):
            if old in used:
                new_index[old] = len(kept)
                kept.append(color)
        self.palette = kept
        self.cells = [[new_index[i] for i in row] for row in self.cells]
        return True

    def set_background(self, color: str) -> bool:
        color = color.lower()
        if color == self.palette[0]:
            return False
        if color in self.palette:
            # The color is already used by painted cells
            dup = self.palette.index(color)
            self.cells = [
                [0 if i == dup else (i - 1 if i > dup else i) for i in row]
                for row in self.cells
            ]
            del self.palette[dup]
        self.palette[0] = color
        return True
