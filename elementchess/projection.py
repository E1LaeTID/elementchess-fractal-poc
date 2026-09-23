from __future__ import annotations

from dataclasses import dataclass

from .board import Board


@dataclass(frozen=True, slots=True)
class ChessPosition:
    file: int
    rank: int

    def __post_init__(self) -> None:
        if not (0 <= self.file < 8 and 0 <= self.rank < 8):
            raise IndexError(f"Position hors échiquier : ({self.file}, {self.rank})")

    @property
    def coordinate(self) -> str:
        return f"{chr(65 + self.file)}{self.rank + 1}"


class ChessProjection:
    """Projection des 8×8 positions de pièces dans le terrain 17×17.

    Une pièce se place au centre d'une cellule d'échiquier logique. Deux
    positions adjacentes utilisent des ancres espacées de deux cellules de
    terrain : la cellule intermédiaire reste un environnement partagé.
    """

    SIZE = 8

    @staticmethod
    def terrain_anchor(position: ChessPosition) -> tuple[int, int]:
        return position.file * 2 + 1, position.rank * 2 + 1

    @staticmethod
    def from_terrain(x: int, y: int) -> ChessPosition | None:
        Board._validate_coordinates(x, y)
        if x % 2 == 0 or y % 2 == 0:
            return None
        return ChessPosition((x - 1) // 2, (y - 1) // 2)

