"""Noyau console d'ElementChess."""

from .board import Board
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
from .events import GameEvent, GameEventType, OpeningEventSystem, PlayerToken, RotationCommand, TerrainStateCapture
from .sudoku import PlacementError, PlacementPhase, RecycleResult, TerrainSudokuRules, TokenPlacementController
from .movement import MovementEngine, PieceMove
from .combat import CombatCalculator, CombatPower, CombatReport
from .turn_cycle import RoundCycle
from .combat_failures import CombatFailureTracker
from .balance import (
    BalanceCombatCalculator,
    BalanceConfig,
    ConfrontationGeometry,
    ElementMode,
    ElementSignatureField,
    RelationLevel,
)
from .sudoku_balance import SudokuCorrectionEngine, SudokuRiskAnalyzer
from .layer_cycles import CycleAxis, CycleRecord, LayerCycleEngine, MobileLayer
from .game_progress import (
    EmpiricalPhaseLimits, GamePhase, GameProgressEvaluator, HorizonOutcome,
    NPlusFourSelector, ProgressAssessment, ProgressSnapshot,
)

__all__ = [
    "Board",
    "BoundaryKind",
    "Cell",
    "CellTransition",
    "ChessCellState",
    "Element",
    "Orientation",
    "Piece",
    "TerrainCellState",
    "TerrainOwner",
    "GameEvent",
    "GameEventType",
    "OpeningEventSystem",
    "PlayerToken",
    "RotationCommand",
    "TerrainStateCapture",
    "PlacementError",
    "PlacementPhase",
    "TerrainSudokuRules",
    "TokenPlacementController",
    "RecycleResult",
    "MovementEngine",
    "PieceMove",
    "CombatCalculator",
    "CombatPower",
    "CombatReport",
    "RoundCycle",
    "CombatFailureTracker",
    "BalanceCombatCalculator",
    "BalanceConfig",
    "ConfrontationGeometry",
    "ElementMode",
    "ElementSignatureField",
    "RelationLevel",
    "SudokuCorrectionEngine",
    "SudokuRiskAnalyzer",
    "CycleAxis",
    "CycleRecord",
    "LayerCycleEngine",
    "MobileLayer",
    "GamePhase",
    "GameProgressEvaluator",
    "ProgressAssessment",
    "ProgressSnapshot",
    "EmpiricalPhaseLimits",
    "HorizonOutcome",
    "NPlusFourSelector",
]
