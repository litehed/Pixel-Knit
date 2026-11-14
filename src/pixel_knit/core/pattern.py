from dataclasses import dataclass, field

DEFAULT_COLOR = "#222222"


@dataclass
class Pattern:
    width: int = 17
    height: int = 17
    palette: list[str] = field(default_factory=lambda: ["#ffffff", DEFAULT_COLOR])
    cells: list[list[int]] = field(default_factory=list)

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
