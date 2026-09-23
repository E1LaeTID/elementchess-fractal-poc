from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from math import floor

from .board import Board
from .domain import TerrainOwner


class GamePhase(IntEnum):
    EARLY = 0
    MIDDLE = 1
    LATE = 2


@dataclass(frozen=True, slots=True)
class ProgressSnapshot:
    round_number: int
    captured_terrains: int
    assigned_uncaptured_numbers: int
    uncaptured_number_slots: int
    pieces_on_board: int
    failure_points: int
    tokens_in_hands: int


@dataclass(frozen=True, slots=True)
class EmpiricalPhaseLimits:
    """Limites déduites d'un corpus, jamais de numéros de tours imposés."""

    early_upper: float
    late_lower: float
    sample_count: int
    source: str = "empirical_progress_terciles"


@dataclass(frozen=True, slots=True)
class ProgressAssessment:
    score: float
    phase: GamePhase
    components: dict[str, float]
    limits: EmpiricalPhaseLimits


class GameProgressEvaluator:
    """Classe un état relativement à des trajectoires de référence observées."""

    FEATURE_NAMES = (
        "round_rank", "captured_terrain_ratio", "filled_uncaptured_ratio",
        "material_reduction_ratio", "failure_pressure_ratio",
        "stock_saturation_ratio",
    )

    def __init__(self, weights: dict[str, float]) -> None:
        self.weights = dict(weights)
        if set(self.weights) != set(self.FEATURE_NAMES):
            raise ValueError("Un poids est requis pour chacune des six observations")
        if any(value < 0 for value in self.weights.values()) or sum(self.weights.values()) <= 0:
            raise ValueError("Les poids doivent être positifs et avoir une somme non nulle")
        total = sum(self.weights.values())
        self.weights = {name: value / total for name, value in self.weights.items()}

    @staticmethod
    def snapshot(board: Board, *, round_number: int, failure_points: int = 0,
                 tokens_in_hands: int = 0) -> ProgressSnapshot:
        uncaptured = [
            cell for row in board.rows() for cell in row
            if cell.zone_id is not None and not cell.is_chess_cell
            and board.zone_owner(cell.zone_id) is TerrainOwner.NONE
        ]
        return ProgressSnapshot(
            max(0, round_number),
            sum(board.zone_owner(f"Z{r}{c}") is not TerrainOwner.NONE
                for r in range(1, 4) for c in range(1, 4)),
            sum(cell.terrain_number is not None for cell in uncaptured),
            len(uncaptured),
            sum(cell.piece is not None for row in board.rows() for cell in row),
            max(0, failure_points), max(0, tokens_in_hands),
        )

    @staticmethod
    def _ratio(value: float, maximum: float) -> float:
        return min(1.0, max(0.0, value / maximum)) if maximum else 0.0

    @staticmethod
    def _rank(value: float, corpus: list[float]) -> float:
        if not corpus:
            raise ValueError("Le corpus de référence ne peut pas être vide")
        return sum(item <= value for item in corpus) / len(corpus)

    def components(self, snapshot: ProgressSnapshot, *,
                   observed_rounds: list[int]) -> dict[str, float]:
        return {
            "round_rank": self._rank(snapshot.round_number, observed_rounds),
            "captured_terrain_ratio": self._ratio(snapshot.captured_terrains, 9),
            "filled_uncaptured_ratio": self._ratio(
                snapshot.assigned_uncaptured_numbers, snapshot.uncaptured_number_slots
            ),
            "material_reduction_ratio": 1.0 - self._ratio(snapshot.pieces_on_board, 32),
            "failure_pressure_ratio": self._ratio(snapshot.failure_points, 6),
            "stock_saturation_ratio": self._ratio(snapshot.tokens_in_hands, 42),
        }

    def score(self, snapshot: ProgressSnapshot, *, observed_rounds: list[int]) -> float:
        values = self.components(snapshot, observed_rounds=observed_rounds)
        return sum(self.weights[name] * values[name] for name in self.FEATURE_NAMES)

    @staticmethod
    def _quantile(values: list[float], probability: float) -> float:
        ordered = sorted(values)
        if not ordered:
            raise ValueError("Aucune trajectoire pour déduire les limites")
        position = (len(ordered) - 1) * probability
        lower = floor(position)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = position - lower
        return ordered[lower] * (1 - fraction) + ordered[upper] * fraction

    @classmethod
    def fit_limits(cls, trajectory_scores: list[float]) -> EmpiricalPhaseLimits:
        if len(trajectory_scores) < 3:
            raise ValueError("Au moins trois états observés sont nécessaires")
        return EmpiricalPhaseLimits(
            cls._quantile(trajectory_scores, 1 / 3),
            cls._quantile(trajectory_scores, 2 / 3),
            len(trajectory_scores),
        )

    def assess(self, snapshot: ProgressSnapshot, *, observed_rounds: list[int],
               limits: EmpiricalPhaseLimits,
               previous_phase: GamePhase | None = None) -> ProgressAssessment:
        components = self.components(snapshot, observed_rounds=observed_rounds)
        score = sum(self.weights[name] * components[name] for name in self.FEATURE_NAMES)
        phase = (GamePhase.EARLY if score < limits.early_upper else
                 GamePhase.MIDDLE if score < limits.late_lower else GamePhase.LATE)
        if previous_phase is not None:
            phase = max(phase, previous_phase)
        return ProgressAssessment(round(score, 6), GamePhase(phase), components, limits)


@dataclass(frozen=True, slots=True)
class HorizonOutcome:
    """Mesures simulées au tour N+4 pour une action candidate."""

    action: str
    blockage_risk: float
    strategic_advantage_gap: float
    terminal_risk_gap: float
    dilemma_score: float


class NPlusFourSelector:
    """Choisit une permutation seulement si elle domine le scénario témoin."""

    @staticmethod
    def select(baseline: HorizonOutcome, candidates: list[HorizonOutcome], *,
               preserve_advantage_tolerance: float,
               terminal_risk_tolerance: float) -> HorizonOutcome:
        admissible = [
            item for item in candidates
            if item.blockage_risk < baseline.blockage_risk
            and abs(item.strategic_advantage_gap - baseline.strategic_advantage_gap)
            <= preserve_advantage_tolerance
            and abs(item.terminal_risk_gap) <= terminal_risk_tolerance
        ]
        if not admissible:
            return baseline
        return min(admissible, key=lambda item: (item.blockage_risk, -item.dilemma_score, item.action))
