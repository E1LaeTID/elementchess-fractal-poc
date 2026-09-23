from __future__ import annotations

from .balance import BalanceCombatCalculator, BalancedCombatReport, BalancedPower
from .board import Board
from .movement import PieceMove


CombatPower = BalancedPower
CombatReport = BalancedCombatReport


class CombatCalculator:
    """Façade utilisée par l'interface graphique sur le moteur équilibré."""

    @staticmethod
    def calculate(board: Board, move: PieceMove) -> CombatReport:
        signatures = getattr(board, "element_signatures", None)
        return BalanceCombatCalculator(signatures=signatures).calculate(board, move)
