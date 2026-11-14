from dataclasses import dataclass, field


@dataclass
class Pattern:
    width: int = 17
    height: int = 17
    palette: list[str] = field(default_factory=lambda: ["#ffffff", "#222222"])
    cells: list[list[int]] = field(default_factory=list)

    def __post_init__(self):
        if not self.cells:
            self.cells = [[0] * self.width for _ in range(self.height)]

    def set_cell(self, row: int, col: int, value: int) -> bool:
        if self.cells[row][col] == value:
            return False
        self.cells[row][col] = value
        return True
