from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from statistics import mean

from .balance import (
    BalanceCombatCalculator,
    ConfrontationGeometry,
    ElementMode,
    ElementSignatureField,
    RelationLevel,
)
from .board import Board
from .domain import ChessCellState, Element, Orientation, Piece, TerrainOwner
from .movement import PieceMove
from .sudoku_balance import SudokuRiskAnalyzer


@dataclass(frozen=True, slots=True)
class Distribution:
    samples: int
    minimum: int
    maximum: int
    average: float
    q10: int
    median: int
    q90: int


@dataclass(frozen=True, slots=True)
class GeometryStatistics:
    geometry: str
    attack: Distribution
    defense: Distribution
    attack_win_probability: float
    defense_win_probability: float
    equality_probability: float


@dataclass(frozen=True, slots=True)
class SudokuStatistics:
    samples: int
    blocked_probability: float
    forced_probability: float
    mean_minimum_candidates: float


@dataclass(frozen=True, slots=True)
class TerminalRaceConfig:
    attack_attempt_probability: float = 0.63
    terrain_capture_probability: float = 0.12
    checkmate_probability: float = 0.022
    token_placements: tuple[int, ...] = (0, 1, 1, 2, 2)
    maximum_rounds: int = 100


@dataclass(frozen=True, slots=True)
class TerminalRaceStatistics:
    samples: int
    three_failed_attacks: float
    three_captured_terrains: float
    stock_reaches_twenty_one: float
    checkmate: float
    censored: float
    average_terminal_round: float


@dataclass(frozen=True, slots=True)
class BalanceReport:
    seed: int
    iterations: int
    geometries: tuple[GeometryStatistics, ...]
    sudoku: SudokuStatistics
    terminal_race: TerminalRaceStatistics

    def to_dict(self) -> dict:
        return asdict(self)


def _distribution(values: list[int]) -> Distribution:
    ordered = sorted(values)
    size = len(ordered)
    pick = lambda q: ordered[min(size - 1, int((size - 1) * q))]
    return Distribution(size, ordered[0], ordered[-1], round(mean(ordered), 3), pick(0.1), pick(0.5), pick(0.9))


class BalanceMonteCarlo:
    PIECES = ("pawn", "knight", "bishop", "rook", "queen", "king")
    POSITIONS = {
        ConfrontationGeometry.FORWARD: ((7, 9), (7, 7)),
        ConfrontationGeometry.HORIZONTAL: ((7, 7), (9, 7)),
        ConfrontationGeometry.DIAGONAL: ((7, 7), (9, 9)),
    }

    def __init__(self, seed: int = 426) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def _signatures(self) -> ElementSignatureField:
        field = ElementSignatureField()
        elements = [element for element in Element if element is not Element.NONE]
        for element in elements:
            mode = self.rng.choice(tuple(ElementMode))
            level = RelationLevel.NEUTRAL if mode is ElementMode.NEUTRAL else self.rng.choice(tuple(RelationLevel)[1:])
            field.set(element, mode, level)
        return field

    def _combat_sample(self, geometry: ConfrontationGeometry):
        board = Board()
        board.clear_demo()
        board.assign_random_elements(self.rng.randrange(2**32))
        start, destination = self.POSITIONS[geometry]
        attack_kind = self.rng.choice(self.PIECES)
        defense_kind = self.rng.choice(self.PIECES)
        attacker = Piece(f"white-{attack_kind}", "A", TerrainOwner.WHITE.value, Orientation.NORTH)
        defender = Piece(f"black-{defense_kind}", "D", TerrainOwner.BLACK.value, Orientation.SOUTH)
        board.cell(*start).piece = attacker
        board.cell(*start).chess_state = ChessCellState.OCCUPIED
        board.cell(*destination).piece = defender
        board.cell(*destination).chess_state = ChessCellState.OCCUPIED
        path = tuple(
            (cell.x, cell.y) for cell in board.neighbors8(*start)
            if not cell.is_chess_cell and self.rng.random() < 0.35
        )
        for x, y in path:
            if self.rng.random() < 0.5:
                board.cell(x, y).terrain_number = self.rng.randint(1, 5)
                board.cell(x, y).terrain_owner = TerrainOwner.WHITE
        for cell in board.neighbors8(*destination):
            if self.rng.random() < 0.35:
                cell.terrain_number = self.rng.randint(1, 5)
                cell.terrain_owner = TerrainOwner.BLACK
        move = PieceMove(start, destination, path, defender)
        return BalanceCombatCalculator(signatures=self._signatures()).calculate(board, move)

    def _sudoku_sample(self):
        board = Board()
        board.clear_demo()
        board.generate_terrain_numbers(self.rng.randrange(2**32))
        cells = [cell for cell in board.zone_cells("Z22") if not cell.is_chess_cell]
        keep = self.rng.randint(3, min(12, len(cells)))
        preserved = set(self.rng.sample([(cell.x, cell.y) for cell in cells], keep))
        for cell in cells:
            if (cell.x, cell.y) not in preserved:
                cell.terrain_number = None
        # Une erreur contrôlée sur quatre permet de mesurer le détecteur de blocage.
        if self.rng.random() < 0.25:
            empty = [cell for cell in cells if cell.terrain_number is None]
            if empty:
                target = self.rng.choice(empty)
                target.terrain_number = self.rng.randint(1, 5)
        return SudokuRiskAnalyzer.analyze(board, "Z22")

    def _terminal_race(
        self,
        iterations: int,
        failure_probability: float,
        config: TerminalRaceConfig | None = None,
    ) -> TerminalRaceStatistics:
        config = config or TerminalRaceConfig()
        outcomes = {"failures": 0, "terrains": 0, "stock": 0, "checkmate": 0, "censored": 0}
        terminal_rounds = []
        for _ in range(iterations):
            failures = terrains = 0
            clean_turns = 0
            stock = 5
            for round_number in range(1, config.maximum_rounds + 1):
                stock += 2
                stock -= min(stock, self.rng.choice(config.token_placements))
                if self.rng.random() < config.terrain_capture_probability:
                    terrains += 1
                attacked = self.rng.random() < config.attack_attempt_probability
                if attacked and self.rng.random() < failure_probability:
                    failures += 1
                    clean_turns = 0
                else:
                    clean_turns += 1
                    if clean_turns >= 2 and failures:
                        failures -= 1
                        clean_turns = 0
                outcome = (
                    "failures" if failures >= 3 else
                    "terrains" if terrains >= 3 else
                    "stock" if stock >= 21 else
                    "checkmate" if self.rng.random() < config.checkmate_probability else None
                )
                if outcome:
                    outcomes[outcome] += 1
                    terminal_rounds.append(round_number)
                    break
            else:
                outcomes["censored"] += 1
                terminal_rounds.append(config.maximum_rounds)
        return TerminalRaceStatistics(
            samples=iterations,
            three_failed_attacks=round(outcomes["failures"] / iterations, 6),
            three_captured_terrains=round(outcomes["terrains"] / iterations, 6),
            stock_reaches_twenty_one=round(outcomes["stock"] / iterations, 6),
            checkmate=round(outcomes["checkmate"] / iterations, 6),
            censored=round(outcomes["censored"] / iterations, 6),
            average_terminal_round=round(mean(terminal_rounds), 3),
        )

    def run(self, iterations: int = 10_000) -> BalanceReport:
        if iterations < 1:
            raise ValueError("Le nombre d'itérations doit être positif")
        geometries = []
        for geometry in ConfrontationGeometry:
            reports = [self._combat_sample(geometry) for _ in range(iterations)]
            attacks = [report.attack.total for report in reports]
            defenses = [report.defense.total for report in reports]
            geometries.append(GeometryStatistics(
                geometry=geometry.value,
                attack=_distribution(attacks),
                defense=_distribution(defenses),
                attack_win_probability=round(mean(report.attack_win_probability for report in reports), 6),
                defense_win_probability=round(mean(report.defense_win_probability for report in reports), 6),
                equality_probability=round(sum(a == d for a, d in zip(attacks, defenses)) / iterations, 6),
            ))
        risks = [self._sudoku_sample() for _ in range(iterations)]
        sudoku = SudokuStatistics(
            samples=iterations,
            blocked_probability=round(sum(risk.blocked for risk in risks) / iterations, 6),
            forced_probability=round(sum(risk.forced_cells > 0 for risk in risks) / iterations, 6),
            mean_minimum_candidates=round(mean(risk.minimum_candidates for risk in risks), 3),
        )
        failure_probability = mean(item.defense_win_probability for item in geometries)
        terminal_race = self._terminal_race(iterations, failure_probability)
        return BalanceReport(self.seed, iterations, tuple(geometries), sudoku, terminal_race)


def main() -> None:
    parser = argparse.ArgumentParser(description="Laboratoire stochastique ElementChess")
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=426)
    parser.add_argument("--output", type=str)
    args = parser.parse_args()
    report = BalanceMonteCarlo(args.seed).run(args.iterations)
    payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
