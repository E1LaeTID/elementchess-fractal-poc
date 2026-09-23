from __future__ import annotations

from dataclasses import dataclass

from .board import Board
from .domain import Element, Orientation, TerrainOwner
from .sudoku import PlacementError, TerrainSudokuRules


_DIRECTION = {
    Orientation.NORTH: (0, -1),
    Orientation.NORTH_EAST: (1, -1),
    Orientation.EAST: (1, 0),
    Orientation.SOUTH_EAST: (1, 1),
    Orientation.SOUTH: (0, 1),
    Orientation.SOUTH_WEST: (-1, 1),
    Orientation.WEST: (-1, 0),
    Orientation.NORTH_WEST: (-1, -1),
}


@dataclass(frozen=True, slots=True)
class OrientationBonusResult:
    piece_coordinate: str
    target_coordinate: str
    zone_id: str
    element: Element
    owner: TerrainOwner
    placed_count: int
    captured_owner: TerrainOwner = TerrainOwner.NONE


class OrientationTerrainBonus:
    """Complète la croix locale visée lorsqu'un élément orienté est tiré."""

    @staticmethod
    def owner_for_zone(board: Board, zone_id: str) -> TerrainOwner:
        piece_counts = {
            owner: sum(
                1
                for cell in board.zone_cells(zone_id)
                if cell.piece is not None and cell.piece.owner == owner.value
            )
            for owner in (TerrainOwner.WHITE, TerrainOwner.BLACK)
        }
        if piece_counts[TerrainOwner.WHITE] != piece_counts[TerrainOwner.BLACK]:
            return max(piece_counts, key=piece_counts.get)
        if piece_counts[TerrainOwner.WHITE] == 0:
            return TerrainOwner.NONE

        token_counts = {
            owner: sum(
                1
                for cell in board.zone_cells(zone_id)
                if cell.terrain_number is not None and cell.terrain_owner is owner
            )
            for owner in (TerrainOwner.WHITE, TerrainOwner.BLACK)
        }
        if token_counts[TerrainOwner.WHITE] == token_counts[TerrainOwner.BLACK]:
            return TerrainOwner.NONE
        return max(token_counts, key=token_counts.get)

    @staticmethod
    def _cross_cells(board: Board, x: int, y: int) -> list:
        target = board.cell(x, y)
        start_x, start_y = TerrainSudokuRules._zone_origin(target)
        coordinates = (
            {(column, y) for column in range(start_x, start_x + Board.ZONE_SIZE)}
            | {(x, line) for line in range(start_y, start_y + Board.ZONE_SIZE)}
        )
        return [
            board.cell(column, line)
            for column, line in sorted(coordinates, key=lambda point: (point[1], point[0]))
            if not board.cell(column, line).is_chess_cell
        ]

    @classmethod
    def _fill_cross(cls, board: Board, x: int, y: int, owner: TerrainOwner) -> int:
        empty = [cell for cell in cls._cross_cells(board, x, y) if cell.terrain_number is None]
        if not empty:
            return 0

        def candidates(cell) -> list[int]:
            valid: list[int] = []
            for value in range(1, 6):
                try:
                    TerrainSudokuRules.validate(board, cell.x, cell.y, value)
                except PlacementError:
                    continue
                valid.append(value)
            return valid

        def solve(remaining: list) -> bool:
            if not remaining:
                return True
            ranked = sorted(
                ((len(candidates(cell)), cell) for cell in remaining),
                key=lambda item: (item[0], item[1].y, item[1].x),
            )
            count, cell = ranked[0]
            if count == 0:
                return False
            next_remaining = [item for item in remaining if item is not cell]
            for value in candidates(cell):
                cell.terrain_number = value
                cell.terrain_owner = owner
                if solve(next_remaining):
                    return True
                cell.terrain_number = None
                cell.terrain_owner = TerrainOwner.NONE
            return False

        if solve(empty):
            return len(empty)
        for cell in empty:
            cell.terrain_number = None
            cell.terrain_owner = TerrainOwner.NONE
        return 0

    @classmethod
    def apply(
        cls,
        board: Board,
        drawn_elements: tuple[Element, ...],
    ) -> tuple[OrientationBonusResult, ...]:
        selected = set(drawn_elements)
        results: list[OrientationBonusResult] = []
        processed_targets: set[tuple[int, int]] = set()
        pieces = [
            cell
            for row in board.rows()
            for cell in row
            if (
                cell.is_chess_cell
                and cell.piece is not None
                and cell.piece.orientation_locked
            )
        ]
        for piece_cell in sorted(pieces, key=lambda cell: (cell.y, cell.x)):
            dx, dy = _DIRECTION[piece_cell.piece.orientation]
            target_x, target_y = piece_cell.x + dx, piece_cell.y + dy
            if not (0 <= target_x < Board.SIZE and 0 <= target_y < Board.SIZE):
                continue
            if (target_x, target_y) in processed_targets:
                continue
            target = board.cell(target_x, target_y)
            if target.zone_id is None or target.terrain not in selected:
                continue
            if board.zone_owner(target.zone_id) is not TerrainOwner.NONE:
                continue
            owner = cls.owner_for_zone(board, target.zone_id)
            if owner is TerrainOwner.NONE:
                continue
            processed_targets.add((target_x, target_y))
            placed = cls._fill_cross(board, target_x, target_y, owner)
            if placed == 0:
                continue
            captured = TerrainSudokuRules.capture_if_complete(board, target.zone_id)
            results.append(OrientationBonusResult(
                piece_cell.coordinate,
                target.coordinate,
                target.zone_id,
                target.terrain,
                owner,
                placed,
                captured,
            ))
        return tuple(results)
