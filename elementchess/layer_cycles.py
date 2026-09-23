from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .board import Board
from .domain import TerrainOwner


class MobileLayer(Enum):
    TERRAIN_NUMBER = "numéros"
    TERRAIN_ELEMENT = "éléments"


class CycleAxis(Enum):
    ROW = "ligne"
    COLUMN = "colonne"
    TRANSPOSE = "transposition"
    ANTI_TRANSPOSE = "transposition_inverse"


@dataclass(frozen=True, slots=True)
class CycleRecord:
    zone_id: str
    layer: MobileLayer
    axis: CycleAxis
    index: int | None
    direction: int
    permutation: tuple[tuple[str, str], ...]

    @property
    def global_scope(self) -> bool:
        return self.zone_id == "GLOBAL"

    @property
    def indicator_badge(self) -> str:
        return "○" if self.layer is MobileLayer.TERRAIN_ELEMENT else "99"

    @property
    def indicator_arrow(self) -> str:
        if self.axis is CycleAxis.ROW:
            return "⇉" if self.direction > 0 else "⇇"
        if self.axis is CycleAxis.COLUMN:
            return "⇊" if self.direction > 0 else "⇈"
        return "⇄"


class LayerCycleEngine:
    """Permute une couche mobile sans déplacer les cellules ni les pièces."""

    @staticmethod
    def _origin(zone_id: str) -> tuple[int, int]:
        return 1 + (int(zone_id[2]) - 1) * 5, 1 + (int(zone_id[1]) - 1) * 5

    @staticmethod
    def _payload(cell, layer: MobileLayer):
        if layer is MobileLayer.TERRAIN_NUMBER:
            return cell.terrain_number, cell.terrain_owner
        return (cell.terrain,)

    @staticmethod
    def _assign(cell, layer: MobileLayer, payload) -> None:
        if layer is MobileLayer.TERRAIN_NUMBER:
            cell.terrain_number, cell.terrain_owner = payload
        else:
            (cell.terrain,) = payload

    def rotate_continuous(
        self,
        board: Board,
        zone_id: str,
        layer: MobileLayer,
        axis: CycleAxis,
        index: int,
        direction: int,
    ) -> CycleRecord:
        if axis not in (CycleAxis.ROW, CycleAxis.COLUMN):
            raise ValueError("Une rotation continue exige une ligne ou une colonne")
        if not 0 <= index < 5 or direction not in (-1, 1):
            raise ValueError("Index local 0..4 et direction ±1 attendus")
        if (
            layer is MobileLayer.TERRAIN_NUMBER
            and board.zone_owner(zone_id) is not TerrainOwner.NONE
        ):
            raise ValueError("Les numéros d'une parcelle capturée sont exclus des cycles")
        ox, oy = self._origin(zone_id)
        coordinates = (
            [(ox + step, oy + index) for step in range(5)]
            if axis is CycleAxis.ROW
            else [(ox + index, oy + step) for step in range(5)]
        )
        cells = [board.cell(x, y) for x, y in coordinates if not board.cell(x, y).is_chess_cell]
        if len(cells) < 2:
            raise ValueError("L'ensemble continu ne contient pas assez de cellules mobiles")
        if any(
            abs(first.x - second.x) + abs(first.y - second.y) != 1
            for first, second in zip(cells, cells[1:])
        ):
            raise ValueError("La ligne ou colonne est interrompue par une case d'échiquier")
        payloads = [self._payload(cell, layer) for cell in cells]
        rotated = payloads[-direction:] + payloads[:-direction]
        sources = cells[-direction:] + cells[:-direction]
        permutation = []
        for source, destination, payload in zip(sources, cells, rotated):
            self._assign(destination, layer, payload)
            permutation.append((source.coordinate, destination.coordinate))
        return CycleRecord(zone_id, layer, axis, index, direction, tuple(permutation))

    def rotate_global_elements(
        self,
        board: Board,
        axis: CycleAxis,
        index: int,
        direction: int,
    ) -> CycleRecord:
        """Permute une ligne/colonne territoriale complète de la grille 17×17.

        Une seule case réservée aux pièces invalide tout le support : aucun
        segment partiel n'est utilisé. Ce cycle global est réservé aux éléments.
        """
        if axis not in (CycleAxis.ROW, CycleAxis.COLUMN):
            raise ValueError("Le cycle global exige une ligne ou une colonne")
        if not 0 <= index < Board.SIZE or direction not in (-1, 1):
            raise ValueError("Index global 0..16 et direction ±1 attendus")
        coordinates = (
            [(step, index) for step in range(Board.SIZE)]
            if axis is CycleAxis.ROW
            else [(index, step) for step in range(Board.SIZE)]
        )
        cells = [board.cell(x, y) for x, y in coordinates]
        if any(cell.is_chess_cell for cell in cells):
            raise ValueError("La ligne ou colonne globale contient une case de jeu")
        payloads = [self._payload(cell, MobileLayer.TERRAIN_ELEMENT) for cell in cells]
        rotated = payloads[-direction:] + payloads[:-direction]
        sources = cells[-direction:] + cells[:-direction]
        permutation = []
        for source, destination, payload in zip(sources, cells, rotated):
            self._assign(destination, MobileLayer.TERRAIN_ELEMENT, payload)
            permutation.append((source.coordinate, destination.coordinate))
        return CycleRecord(
            "GLOBAL", MobileLayer.TERRAIN_ELEMENT, axis, index, direction,
            tuple(permutation),
        )

    def transpose(
        self,
        board: Board,
        zone_id: str,
        layer: MobileLayer,
        *,
        inverse: bool = False,
    ) -> CycleRecord:
        if (
            layer is MobileLayer.TERRAIN_NUMBER
            and board.zone_owner(zone_id) is not TerrainOwner.NONE
        ):
            raise ValueError("Les numéros d'une parcelle capturée sont exclus des cycles")
        ox, oy = self._origin(zone_id)
        snapshot = {
            (x, y): self._payload(board.cell(x, y), layer)
            for y in range(oy, oy + 5) for x in range(ox, ox + 5)
            if not board.cell(x, y).is_chess_cell
        }
        permutation = []
        for destination in snapshot:
            x, y = destination
            lx, ly = x - ox, y - oy
            source = (ox + ly, oy + lx) if not inverse else (ox + 4 - ly, oy + 4 - lx)
            if source not in snapshot:
                continue
            self._assign(board.cell(*destination), layer, snapshot[source])
            permutation.append((board.cell(*source).coordinate, board.cell(*destination).coordinate))
        axis = CycleAxis.ANTI_TRANSPOSE if inverse else CycleAxis.TRANSPOSE
        return CycleRecord(zone_id, layer, axis, None, -1 if inverse else 1, tuple(permutation))
