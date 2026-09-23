from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .board import Board
from .domain import CellTransition, TerrainOwner
from .sudoku import TerrainSudokuRules


VALUES = frozenset(range(1, 6))


class CorrectionOperation(Enum):
    ROTATE_ROW_LEFT = "rotation_ligne_gauche"
    ROTATE_ROW_RIGHT = "rotation_ligne_droite"
    ROTATE_COLUMN_UP = "rotation_colonne_haut"
    ROTATE_COLUMN_DOWN = "rotation_colonne_bas"
    TRANSPOSE = "transposition"
    ANTI_TRANSPOSE = "transposition_inverse"


@dataclass(frozen=True, slots=True)
class CellRisk:
    coordinate: str
    candidates: frozenset[int]


@dataclass(frozen=True, slots=True)
class SudokuRiskSignature:
    zone_id: str
    blocked_cells: int
    forced_cells: int
    minimum_candidates: int
    remaining_cells: int
    incomplete_rows: int
    incomplete_columns: int
    cells: tuple[CellRisk, ...]

    @property
    def blocked(self) -> bool:
        return self.blocked_cells > 0


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    operation: CorrectionOperation | None
    before: SudokuRiskSignature
    after: SudokuRiskSignature
    applied: bool
    reason: str
    support_index: int | None = None


class SudokuRiskAnalyzer:
    @staticmethod
    def _origin(zone_id: str) -> tuple[int, int]:
        return 1 + (int(zone_id[2]) - 1) * 5, 1 + (int(zone_id[1]) - 1) * 5

    @classmethod
    def candidates(cls, board: Board, x: int, y: int) -> frozenset[int]:
        cell = board.cell(x, y)
        if cell.zone_id is None or cell.is_chess_cell or cell.terrain_number is not None:
            return frozenset()
        start_x, start_y = cls._origin(cell.zone_id)
        full_row = [board.cell(column, y) for column in range(start_x, start_x + 5)]
        full_column = [board.cell(x, line) for line in range(start_y, start_y + 5)]
        row = TerrainSudokuRules._continuous_segment(full_row, cell)
        column = TerrainSudokuRules._continuous_segment(full_column, cell)
        used = {
            item.terrain_number for item in row + column
            if item.terrain_number is not None
        }
        candidates = VALUES - used
        valid = set()
        for value in candidates:
            possible = True
            for line in (row, column):
                assigned = [item.terrain_number for item in line if item.terrain_number is not None]
                if sum(assigned) + value > 15:
                    possible = False
                if len(line) == 5 and len(assigned) + 1 == 5 and sum(assigned) + value != 15:
                    possible = False
            if possible:
                valid.add(value)
        return frozenset(valid)

    @classmethod
    def analyze(cls, board: Board, zone_id: str) -> SudokuRiskSignature:
        origin_x, origin_y = cls._origin(zone_id)
        risks = []
        for y in range(origin_y, origin_y + 5):
            for x in range(origin_x, origin_x + 5):
                cell = board.cell(x, y)
                if not cell.is_chess_cell and cell.terrain_number is None:
                    risks.append(CellRisk(cell.coordinate, cls.candidates(board, x, y)))
        sizes = [len(item.candidates) for item in risks]
        incomplete_rows = sum(
            any(not board.cell(x, y).is_chess_cell and board.cell(x, y).terrain_number is None
                for x in range(origin_x, origin_x + 5))
            for y in range(origin_y, origin_y + 5)
        )
        incomplete_columns = sum(
            any(not board.cell(x, y).is_chess_cell and board.cell(x, y).terrain_number is None
                for y in range(origin_y, origin_y + 5))
            for x in range(origin_x, origin_x + 5)
        )
        return SudokuRiskSignature(
            zone_id=zone_id,
            blocked_cells=sum(size == 0 for size in sizes),
            forced_cells=sum(size == 1 for size in sizes),
            minimum_candidates=min(sizes, default=0),
            remaining_cells=len(risks),
            incomplete_rows=incomplete_rows,
            incomplete_columns=incomplete_columns,
            cells=tuple(risks),
        )


class ProbabilityDictionary:
    """Choisit une correction ; il ne modifie jamais les roues élémentaires."""

    def __init__(self) -> None:
        self.weights = {
            "blocked": (1, 1, 1, 1, 4, 4),
            "fragile": (2, 2, 2, 2, 1, 1),
            "healthy": (1, 1, 1, 1, 0, 0),
        }

    def choose(self, risk: SudokuRiskSignature, rng: random.Random) -> CorrectionOperation:
        key = "blocked" if risk.blocked_cells else "fragile" if risk.forced_cells else "healthy"
        operations = tuple(CorrectionOperation)
        return rng.choices(operations, weights=self.weights[key], k=1)[0]


class SudokuCorrectionEngine:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.dictionary = ProbabilityDictionary()

    @staticmethod
    def _snapshot(board: Board, zone_id: str):
        return {
            (cell.x, cell.y): (cell.terrain_number, cell.terrain_owner, cell.terrain)
            for cell in board.zone_cells(zone_id) if not cell.is_chess_cell
        }

    @staticmethod
    def _restore(board: Board, snapshot) -> None:
        for (x, y), (number, owner, element) in snapshot.items():
            cell = board.cell(x, y)
            cell.terrain_number, cell.terrain_owner, cell.terrain = number, owner, element

    @staticmethod
    def _mobile(board: Board, coordinates: Iterable[tuple[int, int]], allow_locked: bool):
        cells = [board.cell(x, y) for x, y in coordinates if not board.cell(x, y).is_chess_cell]
        if not allow_locked and any(
            cell.transition is CellTransition.LOCKED or cell.terrain_owner is not TerrainOwner.NONE
            for cell in cells
        ):
            return []
        return cells

    @staticmethod
    def _continuous_segments(cells):
        segments = []
        current = []
        for cell in cells:
            if current and abs(cell.x - current[-1].x) + abs(cell.y - current[-1].y) != 1:
                segments.append(current)
                current = []
            current.append(cell)
        if current:
            segments.append(current)
        return segments

    def apply(
        self,
        board: Board,
        zone_id: str,
        operation: CorrectionOperation | None = None,
        *,
        allow_locked: bool = False,
    ) -> CorrectionResult:
        before = SudokuRiskAnalyzer.analyze(board, zone_id)
        if board.zone_owner(zone_id) is not TerrainOwner.NONE:
            return CorrectionResult(
                operation, before, before, False,
                "parcelle capturée : numéros exclus du cycle d'équilibrage",
            )
        operation = operation or self.dictionary.choose(before, self.rng)
        snapshot = self._snapshot(board, zone_id)
        origin_x, origin_y = SudokuRiskAnalyzer._origin(zone_id)
        support_index = None
        if operation in (CorrectionOperation.ROTATE_ROW_LEFT, CorrectionOperation.ROTATE_ROW_RIGHT):
            rows = []
            for local_index, y in enumerate(range(origin_y, origin_y + 5)):
                coordinates = [(x, y) for x in range(origin_x, origin_x + 5)]
                if any(board.cell(x, y).is_chess_cell for x, y in coordinates):
                    continue
                rows.append((local_index, self._mobile(board, coordinates, allow_locked)))
            support_index, cells = next(
                ((index, line) for index, line in rows if len(line) == 5),
                (None, []),
            )
        elif operation in (CorrectionOperation.ROTATE_COLUMN_UP, CorrectionOperation.ROTATE_COLUMN_DOWN):
            columns = []
            for local_index, x in enumerate(range(origin_x, origin_x + 5)):
                coordinates = [(x, y) for y in range(origin_y, origin_y + 5)]
                if any(board.cell(x, y).is_chess_cell for x, y in coordinates):
                    continue
                columns.append((local_index, self._mobile(board, coordinates, allow_locked)))
            support_index, cells = next(
                ((index, line) for index, line in columns if len(line) == 5),
                (None, []),
            )
        else:
            cells = self._mobile(
                board,
                ((x, y) for y in range(origin_y, origin_y + 5) for x in range(origin_x, origin_x + 5)),
                allow_locked,
            )
        if not cells:
            return CorrectionResult(operation, before, before, False, "ensemble verrouillé ou non continu")

        if operation in (
            CorrectionOperation.ROTATE_ROW_LEFT,
            CorrectionOperation.ROTATE_COLUMN_UP,
            CorrectionOperation.ROTATE_ROW_RIGHT,
            CorrectionOperation.ROTATE_COLUMN_DOWN,
        ):
            values = [(cell.terrain_number, cell.terrain_owner) for cell in cells]
            step = 1 if operation in (CorrectionOperation.ROTATE_ROW_LEFT, CorrectionOperation.ROTATE_COLUMN_UP) else -1
            rotated = values[step:] + values[:step]
            for cell, value in zip(cells, rotated):
                cell.terrain_number, cell.terrain_owner = value
        else:
            source = dict(snapshot)
            for y in range(origin_y, origin_y + 5):
                for x in range(origin_x, origin_x + 5):
                    cell = board.cell(x, y)
                    if cell.is_chess_cell:
                        continue
                    local_x, local_y = x - origin_x, y - origin_y
                    if operation is CorrectionOperation.TRANSPOSE:
                        sx, sy = origin_x + local_y, origin_y + local_x
                    else:
                        sx, sy = origin_x + 4 - local_y, origin_y + 4 - local_x
                    if (sx, sy) in source:
                        cell.terrain_number, cell.terrain_owner = source[(sx, sy)][:2]
        after = SudokuRiskAnalyzer.analyze(board, zone_id)
        improved = (after.blocked_cells, after.forced_cells) < (before.blocked_cells, before.forced_cells)
        if before.blocked and not improved:
            self._restore(board, snapshot)
            return CorrectionResult(operation, before, before, False, "correction rejetée : risque non réduit")
        return CorrectionResult(
            operation, before, after, True,
            "permutation enregistrable et résolution préservée", support_index,
        )
