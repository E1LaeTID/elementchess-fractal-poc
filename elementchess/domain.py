from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Element(Enum):
    NONE = ("--", "Aucun", 37)
    WATER = ("EA", "Eau", 36)
    FIRE = ("FE", "Feu", 31)
    WIND = ("VE", "Vent", 96)
    WOOD = ("BO", "Bois", 32)
    EARTH = ("TE", "Terre", 33)
    ICE = ("GL", "Glace", 97)
    MAGMAT = ("MA", "Magmat", 91)
    THUNDER = ("FO", "Foudre", 95)

    def __init__(self, code: str, label: str, ansi_color: int) -> None:
        self.code = code
        self.label = label
        self.ansi_color = ansi_color


class Orientation(Enum):
    NORTH = (0, "N", "↑")
    NORTH_EAST = (1, "NE", "↗")
    EAST = (2, "E", "→")
    SOUTH_EAST = (3, "SE", "↘")
    SOUTH = (4, "S", "↓")
    SOUTH_WEST = (5, "SO", "↙")
    WEST = (6, "O", "←")
    NORTH_WEST = (7, "NO", "↖")

    def __init__(self, step: int, code: str, arrow: str) -> None:
        self.step = step
        self.code = code
        self.arrow = arrow


class CellTransition(Enum):
    STABLE = (".", "stable")
    ENTERING = (">", "entrée")
    LEAVING = ("<", "sortie")
    TRANSFORMING = ("*", "transformation")
    LOCKED = ("#", "verrouillée")

    def __init__(self, symbol: str, label: str) -> None:
        self.symbol = symbol
        self.label = label


class TerrainCellState(Enum):
    NOT_APPLICABLE = "sans état élémentaire"
    UNASSIGNED = "non assignée"
    ASSIGNED = "assignée"
    TRANSFORMING = "transformation"
    CAPTURED = "capturée"


class TerrainOwner(Enum):
    NONE = "personne"
    WHITE = "BLANC"
    BLACK = "NOIR"


class ChessCellState(Enum):
    UNAVAILABLE = "indisponible"
    EMPTY = "libre"
    OCCUPIED = "occupée"
    TRANSFORMING = "transformation"


class BoundaryKind(Enum):
    NONE = "intérieure"
    LATERAL = "bord latéral"
    ANGULAR = "bord angulaire"


@dataclass(frozen=True, slots=True)
class Piece:
    identifier: str
    symbol: str
    owner: str
    orientation: Orientation = Orientation.NORTH
    affinity: Element = Element.NONE
    orientation_locked: bool = False


@dataclass(slots=True)
class Cell:
    x: int
    y: int
    zone_id: str | None
    terrain: Element = Element.NONE
    terrain_number: int | None = None
    terrain_owner: TerrainOwner = TerrainOwner.NONE
    terrain_state: TerrainCellState = TerrainCellState.UNASSIGNED
    boundary_kind: BoundaryKind = BoundaryKind.NONE
    chess_state: ChessCellState = ChessCellState.UNAVAILABLE
    piece: Piece | None = None
    transition: CellTransition = CellTransition.STABLE

    @property
    def coordinate(self) -> str:
        return f"{chr(65 + self.x)}{self.y + 1}"

    @property
    def is_border(self) -> bool:
        return self.x in (0, 16) or self.y in (0, 16)

    @property
    def is_chess_cell(self) -> bool:
        return self.x % 2 == 1 and self.y % 2 == 1
