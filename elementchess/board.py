from __future__ import annotations

import random
from math import ceil

from .domain import (
    Cell,
    CellTransition,
    BoundaryKind,
    ChessCellState,
    Element,
    Orientation,
    Piece,
    TerrainCellState,
    TerrainOwner,
)


class Board:
    SIZE = 17
    ZONE_SIZE = 5

    def __init__(self, number_seed: int = 426) -> None:
        self._number_seed = number_seed
        self.captured_zones: dict[str, TerrainOwner] = {}
        self._cells = [
            [self._create_cell(x, y) for x in range(self.SIZE)]
            for y in range(self.SIZE)
        ]

    @classmethod
    def _create_cell(cls, x: int, y: int) -> Cell:
        zone_id = cls.zone_id_at(x, y)
        on_horizontal_edge = y in (0, cls.SIZE - 1)
        on_vertical_edge = x in (0, cls.SIZE - 1)
        if on_horizontal_edge and on_vertical_edge:
            boundary_kind = BoundaryKind.ANGULAR
        elif on_horizontal_edge or on_vertical_edge:
            boundary_kind = BoundaryKind.LATERAL
        else:
            boundary_kind = BoundaryKind.NONE
        return Cell(
            x=x,
            y=y,
            zone_id=zone_id,
            terrain_state=(
                TerrainCellState.NOT_APPLICABLE
                if x % 2 == 1 and y % 2 == 1
                else TerrainCellState.UNASSIGNED
            ),
            boundary_kind=boundary_kind,
            chess_state=(ChessCellState.EMPTY if x % 2 == 1 and y % 2 == 1 else ChessCellState.UNAVAILABLE),
        )

    @classmethod
    def zone_id_at(cls, x: int, y: int) -> str | None:
        cls._validate_coordinates(x, y)
        if x in (0, 16) or y in (0, 16):
            return None
        zone_col = (x - 1) // 5 + 1
        zone_row = (y - 1) // 5 + 1
        return f"Z{zone_row}{zone_col}"

    @classmethod
    def _validate_coordinates(cls, x: int, y: int) -> None:
        if not (0 <= x < cls.SIZE and 0 <= y < cls.SIZE):
            raise IndexError(f"Cellule hors plateau : ({x}, {y})")

    def cell(self, x: int, y: int) -> Cell:
        self._validate_coordinates(x, y)
        return self._cells[y][x]

    def rows(self) -> tuple[tuple[Cell, ...], ...]:
        return tuple(tuple(row) for row in self._cells)

    def zone_owner(self, zone_id: str | None) -> TerrainOwner:
        if zone_id is None:
            return TerrainOwner.NONE
        return self.captured_zones.get(zone_id, TerrainOwner.NONE)

    def zone_cells(self, zone_id: str) -> tuple[Cell, ...]:
        return tuple(
            cell for row in self._cells for cell in row if cell.zone_id == zone_id
        )

    def zone_has_piece(self, zone_id: str, owner: TerrainOwner) -> bool:
        """Indique si le joueur occupe actuellement la parcelle avec une pièce."""
        if owner is TerrainOwner.NONE:
            return False
        return any(
            cell.piece is not None and cell.piece.owner == owner.value
            for cell in self.zone_cells(zone_id)
        )

    def capture_zone(self, zone_id: str, owner: TerrainOwner) -> None:
        if owner is TerrainOwner.NONE:
            raise ValueError("Une parcelle doit être capturée par un joueur")
        self.captured_zones[zone_id] = owner
        for cell in self.zone_cells(zone_id):
            if not cell.is_chess_cell:
                cell.terrain_state = TerrainCellState.CAPTURED
                cell.transition = CellTransition.LOCKED

    def terrain_winner(self) -> TerrainOwner:
        """Retourne le camp qui aligne trois parcelles capturées."""
        lines = (
            ("Z11", "Z12", "Z13"), ("Z21", "Z22", "Z23"),
            ("Z31", "Z32", "Z33"), ("Z11", "Z21", "Z31"),
            ("Z12", "Z22", "Z32"), ("Z13", "Z23", "Z33"),
            ("Z11", "Z22", "Z33"), ("Z13", "Z22", "Z31"),
        )
        for owner in (TerrainOwner.WHITE, TerrainOwner.BLACK):
            if any(all(self.zone_owner(zone_id) is owner for zone_id in line) for line in lines):
                return owner
        return TerrainOwner.NONE

    def neighbors8(self, x: int, y: int) -> tuple[Cell, ...]:
        """Retourne l'environnement complet d'une position d'échiquier."""
        cell = self.cell(x, y)
        if not cell.is_chess_cell:
            raise ValueError(f"{cell.coordinate} n'est pas une cellule d'échiquier")
        return tuple(
            self.cell(x + dx, y + dy)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if not (dx == 0 and dy == 0)
        )

    def assign_element(self, x: int, y: int, element: Element) -> None:
        if element is Element.NONE:
            raise ValueError("NONE désassigne une cellule ; utiliser clear_elements()")
        cell = self.cell(x, y)
        if cell.is_chess_cell:
            raise ValueError(f"{cell.coordinate} est réservée aux pièces d'échecs")
        cell.terrain = element
        cell.terrain_state = TerrainCellState.ASSIGNED

    def clear_elements(self) -> None:
        for row in self._cells:
            for cell in row:
                cell.terrain = Element.NONE
                cell.terrain_state = (
                    TerrainCellState.NOT_APPLICABLE
                    if cell.is_chess_cell
                    else TerrainCellState.UNASSIGNED
                )

    def assign_random_elements(self, seed: int | None = None) -> None:
        """Distribue un sac équilibré sur les 289 cellules, puis le mélange."""
        rng = random.Random(seed)
        elements = tuple(element for element in Element if element is not Element.NONE)
        terrain_cells = [
            cell for row in self._cells for cell in row
            if not cell.is_chess_cell
        ]
        bag = [elements[index % len(elements)] for index in range(len(terrain_cells))]
        rng.shuffle(bag)
        for cell, element in zip(terrain_cells, bag):
            self.assign_element(cell.x, cell.y, element)

    def assign_circumference_elements(self) -> None:
        """Assigne les huit signatures élémentaires autour du carré 15×15."""
        for index in range(1, self.SIZE - 1):
            self.assign_element(index, 0, Element.WATER)
            self.assign_element(self.SIZE - 1, index, Element.THUNDER)
            self.assign_element(index, self.SIZE - 1, Element.MAGMAT)
            self.assign_element(0, index, Element.WOOD)

        corner_elements = {
            (0, 0): Element.ICE,
            (self.SIZE - 1, 0): Element.WIND,
            (self.SIZE - 1, self.SIZE - 1): Element.FIRE,
            (0, self.SIZE - 1): Element.EARTH,
        }
        for (x, y), element in corner_elements.items():
            self.assign_element(x, y, element)

    def clear_demo(self) -> None:
        self.captured_zones.clear()
        for row in self._cells:
            for cell in row:
                cell.terrain = Element.NONE
                cell.terrain_number = None
                cell.terrain_owner = TerrainOwner.NONE
                cell.piece = None
                cell.transition = CellTransition.STABLE
                cell.terrain_state = (
                    TerrainCellState.NOT_APPLICABLE
                    if cell.is_chess_cell
                    else TerrainCellState.UNASSIGNED
                )
                cell.chess_state = ChessCellState.EMPTY if cell.is_chess_cell else ChessCellState.UNAVAILABLE

    def generate_terrain_numbers(self, seed: int | None = None) -> None:
        """Crée neuf carrés latins 5×5 : chaque ligne/colonne locale vaut 15."""
        rng = random.Random(seed)
        for zone_row in range(3):
            for zone_col in range(3):
                symbols = [1, 2, 3, 4, 5]
                row_order = list(range(5))
                col_order = list(range(5))
                rng.shuffle(symbols)
                rng.shuffle(row_order)
                rng.shuffle(col_order)
                for local_y in range(5):
                    for local_x in range(5):
                        x = 1 + zone_col * 5 + local_x
                        y = 1 + zone_row * 5 + local_y
                        value = symbols[(row_order[local_y] + col_order[local_x]) % 5]
                        cell = self.cell(x, y)
                        cell.terrain_number = None if cell.is_chess_cell else value

        for index in range(self.SIZE):
            self.cell(index, 0).terrain_number = None
            self.cell(index, 16).terrain_number = None
            self.cell(0, index).terrain_number = None
            self.cell(16, index).terrain_number = None

    def preposition_terrain_numbers(
        self,
        seed: int | None = None,
        fraction: float = 1 / 6,
    ) -> None:
        """Pose des indices valides sur ceil(25 × fraction) cellules par zone."""
        if not 0 < fraction <= 1:
            raise ValueError("La fraction de prépositionnement doit être comprise entre 0 et 1")
        rng = random.Random(seed)
        clues_per_zone = ceil(self.ZONE_SIZE * self.ZONE_SIZE * fraction)
        for row in self._cells:
            for cell in row:
                cell.terrain_number = None
                cell.terrain_owner = TerrainOwner.NONE

        for zone_row in range(3):
            for zone_col in range(3):
                symbols = [1, 2, 3, 4, 5]
                row_offsets = list(range(5))
                col_offsets = list(range(5))
                rng.shuffle(symbols)
                rng.shuffle(row_offsets)
                rng.shuffle(col_offsets)
                candidates: list[tuple[Cell, int]] = []
                for local_y in range(5):
                    for local_x in range(5):
                        x = 1 + zone_col * 5 + local_x
                        y = 1 + zone_row * 5 + local_y
                        cell = self.cell(x, y)
                        if cell.is_chess_cell:
                            continue
                        value = symbols[(row_offsets[local_y] + col_offsets[local_x]) % 5]
                        candidates.append((cell, value))
                for cell, value in rng.sample(candidates, clues_per_zone):
                    cell.terrain_number = value

    def place_demo_pieces(self) -> None:
        back_rank = (
            ("rook", "R"), ("knight", "N"), ("bishop", "B"), ("queen", "Q"),
            ("king", "K"), ("bishop", "B"), ("knight", "N"), ("rook", "R"),
        )
        samples: list[tuple[int, int, Piece]] = []
        for file, (kind, symbol) in enumerate(back_rank):
            x = file * 2 + 1
            samples.extend((
                (x, 1, Piece(f"black-{kind}", symbol.lower(), "NOIR", Orientation.SOUTH, Element.NONE)),
                (x, 3, Piece("black-pawn", "p", "NOIR", Orientation.SOUTH, Element.NONE)),
                (x, 13, Piece("white-pawn", "P", "BLANC", Orientation.NORTH, Element.NONE)),
                (x, 15, Piece(f"white-{kind}", symbol, "BLANC", Orientation.NORTH, Element.NONE)),
            ))
        for x, y, piece in samples:
            self.cell(x, y).piece = piece
            self.cell(x, y).chess_state = ChessCellState.OCCUPIED

    def assign_demo_elements(self) -> None:
        zone_elements = (
            Element.WATER, Element.FIRE, Element.WIND,
            Element.WOOD, Element.EARTH, Element.ICE,
            Element.MAGMAT, Element.THUNDER, Element.WATER,
        )
        for row in self._cells:
            for cell in row:
                if cell.zone_id is not None:
                    if cell.is_chess_cell:
                        continue
                    zone_index = (int(cell.zone_id[1]) - 1) * 3 + int(cell.zone_id[2]) - 1
                    self.assign_element(cell.x, cell.y, zone_elements[zone_index])
        self.assign_circumference_elements()

    def load_demo(self) -> None:
        """Pipeline : grille → pièces → éléments → numéros temporaires."""
        self.clear_demo()
        self.place_demo_pieces()
        self.assign_demo_elements()
        self.generate_terrain_numbers(self._number_seed)

        self.cell(7, 13).transition = CellTransition.TRANSFORMING
        self.cell(7, 13).chess_state = ChessCellState.TRANSFORMING
        self.cell(7, 12).transition = CellTransition.ENTERING
        self.cell(15, 15).transition = CellTransition.LOCKED

    def load_opening(self, seed: int | None = None) -> None:
        """État jouable initial : grille, pièces, éléments secrets, aucun jeton."""
        self.clear_demo()
        self.place_demo_pieces()
        self.assign_random_elements(seed)
