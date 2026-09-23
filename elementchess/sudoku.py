from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import count

from .board import Board
from .domain import TerrainOwner
from .tokens import PlayerToken


_RECYCLE_IDS = count(1)


class PlacementPhase(Enum):
    WHITE_TOKENS = "jetons_blancs"
    BLACK_TOKENS = "jetons_noirs"
    PIECES_PENDING = "placement_des_pièces_à_implémenter"


class PlacementError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PlacementResult:
    token: PlayerToken
    coordinate: str
    zone_id: str
    zone_complete: bool
    captured_owner: TerrainOwner = TerrainOwner.NONE


@dataclass(frozen=True, slots=True)
class RecycleResult:
    zone_id: str
    removed: int
    returned: int
    discarded: int


class TerrainSudokuRules:
    """Contraintes numériques locales à chacune des neuf parcelles 5×5."""

    @staticmethod
    def _zone_origin(cell) -> tuple[int, int]:
        return 1 + ((cell.x - 1) // 5) * 5, 1 + ((cell.y - 1) // 5) * 5

    @staticmethod
    def _continuous_segment(line: list, target) -> list:
        """Sous-ligne terrain contenant la cible, bornée par les cases pièce.

        Une case d'échiquier coupe la contrainte : deux nombres placés de part
        et d'autre n'appartiennent pas au même segment de mini-sudoku.
        """
        target_index = line.index(target)
        start = target_index
        end = target_index
        while start > 0 and not line[start - 1].is_chess_cell:
            start -= 1
        while end + 1 < len(line) and not line[end + 1].is_chess_cell:
            end += 1
        return line[start:end + 1]

    @classmethod
    def validate(
        cls,
        board: Board,
        x: int,
        y: int,
        value: int,
        owner: TerrainOwner | None = None,
    ) -> None:
        if value not in range(1, 6):
            raise PlacementError("La valeur d'un jeton doit être comprise entre 1 et 5")
        cell = board.cell(x, y)
        if cell.zone_id is None:
            raise PlacementError("Les jetons se placent uniquement dans une parcelle 5×5")
        if board.zone_owner(cell.zone_id) is not TerrainOwner.NONE:
            raise PlacementError("Cette parcelle est déjà capturée")
        if owner is not None and not board.zone_has_piece(cell.zone_id, owner):
            raise PlacementError(
                "Vous ne pouvez poser un jeton que dans une parcelle occupée par l'une de vos pièces"
            )
        if cell.is_chess_cell:
            raise PlacementError("Cette cellule est réservée à une pièce d'échecs")
        if cell.terrain_number is not None:
            raise PlacementError("Cette cellule possède déjà un jeton")

        start_x, start_y = cls._zone_origin(cell)
        row = [board.cell(column, y) for column in range(start_x, start_x + 5)]
        column = [board.cell(x, line) for line in range(start_y, start_y + 5)]
        for full_line, label in ((row, "ligne"), (column, "colonne")):
            line = cls._continuous_segment(full_line, cell)
            values = [item.terrain_number for item in line if item.terrain_number is not None]
            if value in values:
                raise PlacementError(f"Le numéro {value} existe déjà sur cette {label}")
            candidate = values + [value]
            if sum(candidate) > 15:
                raise PlacementError(f"La somme de cette {label} dépasserait 15")
            if len(line) == 5 and len(candidate) == 5 and sum(candidate) != 15:
                raise PlacementError(f"Une {label} complète doit totaliser 15")

    @classmethod
    def is_zone_complete(cls, board: Board, zone_id: str) -> bool:
        cells = [cell for row in board.rows() for cell in row if cell.zone_id == zone_id and not cell.is_chess_cell]
        if not cells or any(cell.terrain_number is None for cell in cells):
            return False
        for cell in cells:
            start_x, start_y = cls._zone_origin(cell)
            row = [board.cell(column, cell.y) for column in range(start_x, start_x + 5)]
            column = [board.cell(cell.x, line) for line in range(start_y, start_y + 5)]
            for full_line in (row, column):
                line = cls._continuous_segment(full_line, cell)
                values = [item.terrain_number for item in line]
                if len(values) != len(set(values)):
                    return False
                if len(line) == 5 and sum(values) != 15:
                    return False
        return True

    @classmethod
    def capture_if_complete(cls, board: Board, zone_id: str) -> TerrainOwner:
        if not cls.is_zone_complete(board, zone_id):
            return TerrainOwner.NONE
        counts = {
            owner: sum(
                1 for cell in board.zone_cells(zone_id)
                if cell.terrain_number is not None and cell.terrain_owner is owner
            )
            for owner in (TerrainOwner.WHITE, TerrainOwner.BLACK)
        }
        if counts[TerrainOwner.WHITE] == counts[TerrainOwner.BLACK]:
            return TerrainOwner.NONE
        owner = max(counts, key=counts.get)
        board.capture_zone(zone_id, owner)
        return owner


class TokenPlacementController:
    def __init__(
        self,
        board: Board,
        hands: dict[TerrainOwner, tuple[PlayerToken, ...]],
        placement_order: tuple[TerrainOwner, ...] = (TerrainOwner.WHITE, TerrainOwner.BLACK),
    ) -> None:
        self.board = board
        self.hands = hands
        if not placement_order:
            raise ValueError("L'ordre de placement ne peut pas être vide")
        self.placement_order = placement_order
        self.order_index = 0
        self.active_owner = placement_order[0]
        self.phase = self._phase_for(self.active_owner)
        self.selected_token_id: str | None = None
        self.placed_ids: set[str] = set()

    @staticmethod
    def _phase_for(owner: TerrainOwner) -> PlacementPhase:
        return (
            PlacementPhase.WHITE_TOKENS
            if owner is TerrainOwner.WHITE
            else PlacementPhase.BLACK_TOKENS
        )

    def _advance_phase(self) -> None:
        self.selected_token_id = None
        self.order_index += 1
        if self.order_index >= len(self.placement_order):
            self.phase = PlacementPhase.PIECES_PENDING
            return
        self.active_owner = self.placement_order[self.order_index]
        self.phase = self._phase_for(self.active_owner)

    def pass_tokens(self) -> TerrainOwner:
        """Conserve tous les jetons non joués et ouvre la phase suivante."""
        owner = self.active_owner
        self._advance_phase()
        return owner

    def remaining(self, owner: TerrainOwner) -> tuple[PlayerToken, ...]:
        return tuple(token for token in self.hands[owner] if token.identifier not in self.placed_ids)

    def select(self, token_id: str) -> PlayerToken:
        token = next(
            (token for token in self.remaining(self.active_owner) if token.identifier == token_id),
            None,
        )
        if token is None:
            raise PlacementError("Ce jeton n'appartient pas au joueur actif")
        self.selected_token_id = token_id
        return token

    def place_selected(self, x: int, y: int) -> PlacementResult:
        if self.selected_token_id is None:
            raise PlacementError("Sélectionnez d'abord un jeton")
        token = self.select(self.selected_token_id)
        TerrainSudokuRules.validate(self.board, x, y, token.value, token.owner)
        cell = self.board.cell(x, y)
        cell.terrain_number = token.value
        cell.terrain_owner = token.owner
        self.placed_ids.add(token.identifier)
        self.selected_token_id = None
        zone_id = cell.zone_id or ""
        complete = TerrainSudokuRules.is_zone_complete(self.board, zone_id)
        captured_owner = TerrainSudokuRules.capture_if_complete(self.board, zone_id)
        result = PlacementResult(token, cell.coordinate, zone_id, complete, captured_owner)
        if not self.remaining(self.active_owner):
            self._advance_phase()
        return result

    def recycle_zone_at(self, x: int, y: int) -> RecycleResult:
        cell = self.board.cell(x, y)
        zone_id = cell.zone_id
        if zone_id is None:
            raise PlacementError("Choisissez une parcelle 5×5")
        if self.board.zone_owner(zone_id) is not TerrainOwner.NONE:
            raise PlacementError("Une parcelle capturée ne peut plus être recyclée")
        owned = [
            item for item in self.board.zone_cells(zone_id)
            if item.terrain_number is not None and item.terrain_owner is self.active_owner
        ]
        if not owned:
            raise PlacementError("Vous n'avez aucun jeton à recycler sur cette parcelle")

        room = max(0, 21 - len(self.remaining(self.active_owner)))
        returned_values = [item.terrain_number for item in owned[:room]]
        recycled = []
        for value in returned_values:
            recycled.append(PlayerToken(
                f"recycle-{self.active_owner.value.lower()}-{next(_RECYCLE_IDS)}",
                self.active_owner,
                int(value),
            ))
        self.hands[self.active_owner] = self.hands[self.active_owner] + tuple(recycled)
        for item in owned:
            item.terrain_number = None
            item.terrain_owner = TerrainOwner.NONE
        self.selected_token_id = None
        return RecycleResult(zone_id, len(owned), len(recycled), len(owned) - len(recycled))
