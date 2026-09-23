import unittest

from elementchess.board import Board
from elementchess.domain import TerrainOwner
from elementchess.game_progress import (
    GamePhase, GameProgressEvaluator, HorizonOutcome, NPlusFourSelector,
    ProgressSnapshot,
)
from elementchess.layer_cycles import CycleAxis, LayerCycleEngine, MobileLayer
from elementchess.sudoku_balance import (
    CorrectionOperation,
    SudokuCorrectionEngine,
    SudokuRiskAnalyzer,
)


class SudokuBalanceTest(unittest.TestCase):
    def test_candidate_dictionary_detects_a_forced_cell(self):
        board = Board()
        board.clear_demo()
        board.generate_terrain_numbers(42)
        cells = [cell for cell in board.zone_cells("Z11") if not cell.is_chess_cell]
        target = cells[0]
        for cell in cells:
            if cell is not target:
                cell.terrain_number = cell.terrain_number
        target.terrain_number = None
        candidates = SudokuRiskAnalyzer.candidates(board, target.x, target.y)
        self.assertEqual(len(candidates), 1)

    def test_number_cycle_does_not_move_elements_or_coordinates(self):
        board = Board()
        board.load_demo()
        before_elements = {(c.x, c.y): c.terrain for c in board.zone_cells("Z11")}
        record = LayerCycleEngine().rotate_continuous(
            board, "Z11", MobileLayer.TERRAIN_NUMBER, CycleAxis.ROW, 1, 1
        )
        self.assertTrue(record.permutation)
        self.assertEqual(before_elements, {(c.x, c.y): c.terrain for c in board.zone_cells("Z11")})

    def test_cycle_rejects_a_discontinuous_row(self):
        board = Board()
        board.load_demo()
        with self.assertRaisesRegex(ValueError, "interrompue"):
            LayerCycleEngine().rotate_continuous(
                board, "Z11", MobileLayer.TERRAIN_NUMBER, CycleAxis.ROW, 0, 1
            )

    def test_global_element_cycle_uses_complete_17_cell_line(self):
        board = Board()
        board.load_demo()
        before = [board.cell(x, 0).terrain for x in range(Board.SIZE)]
        record = LayerCycleEngine().rotate_global_elements(
            board, CycleAxis.ROW, 0, 1
        )
        after = [board.cell(x, 0).terrain for x in range(Board.SIZE)]
        self.assertEqual(after, before[-1:] + before[:-1])
        self.assertTrue(record.global_scope)
        self.assertEqual(record.indicator_badge, "○")
        self.assertEqual(record.indicator_arrow, "⇉")
        self.assertEqual(len(record.permutation), 17)

    def test_global_element_cycle_rejects_whole_discontinuous_line(self):
        board = Board()
        board.load_demo()
        before = [board.cell(x, 1).terrain for x in range(Board.SIZE)]
        with self.assertRaisesRegex(ValueError, "contient une case de jeu"):
            LayerCycleEngine().rotate_global_elements(
                board, CycleAxis.ROW, 1, 1
            )
        self.assertEqual(before, [board.cell(x, 1).terrain for x in range(Board.SIZE)])

    def test_local_number_correction_never_moves_elements(self):
        board = Board()
        board.load_demo()
        before_elements = {
            (cell.x, cell.y): cell.terrain for cell in board.zone_cells("Z11")
        }
        result = SudokuCorrectionEngine(7).apply(
            board, "Z11", CorrectionOperation.ROTATE_ROW_LEFT,
            allow_locked=True,
        )
        self.assertTrue(result.applied)
        self.assertEqual(
            before_elements,
            {(cell.x, cell.y): cell.terrain for cell in board.zone_cells("Z11")},
        )

    def test_captured_zone_is_excluded_from_number_cycles(self):
        board = Board()
        board.load_demo()
        board.capture_zone("Z11", TerrainOwner.WHITE)
        with self.assertRaisesRegex(ValueError, "capturée"):
            LayerCycleEngine().rotate_continuous(
                board, "Z11", MobileLayer.TERRAIN_NUMBER, CycleAxis.ROW, 1, 1
            )
        result = SudokuCorrectionEngine(7).apply(
            board, "Z11", CorrectionOperation.ROTATE_ROW_LEFT,
            allow_locked=True,
        )
        self.assertFalse(result.applied)
        self.assertIn("exclus", result.reason)

    def test_progress_phase_is_observable_and_never_regresses(self):
        evaluator = GameProgressEvaluator({name: 1 for name in GameProgressEvaluator.FEATURE_NAMES})
        rounds = [1, 3, 5, 8, 12, 18, 25, 34]
        snapshots = [
            ProgressSnapshot(1, 0, 0, 144, 32, 0, 0),
            ProgressSnapshot(12, 3, 72, 96, 22, 2, 15),
            ProgressSnapshot(30, 7, 30, 32, 8, 5, 36),
        ]
        limits = evaluator.fit_limits([
            evaluator.score(item, observed_rounds=rounds) for item in snapshots
        ])
        early, middle, late = [
            evaluator.assess(item, observed_rounds=rounds, limits=limits)
            for item in snapshots
        ]
        self.assertEqual(early.phase, GamePhase.EARLY)
        self.assertEqual(middle.phase, GamePhase.MIDDLE)
        self.assertEqual(late.phase, GamePhase.LATE)
        self.assertEqual(
            evaluator.assess(
                ProgressSnapshot(0, 0, 0, 144, 32, 0, 0),
                observed_rounds=rounds, limits=limits,
                previous_phase=GamePhase.LATE,
            ).phase,
            GamePhase.LATE,
        )

    def test_n_plus_four_keeps_baseline_when_permutation_is_not_safe(self):
        baseline = HorizonOutcome("none", 0.4, 0.2, 0.0, 0.1)
        unsafe = HorizonOutcome("rotate", 0.2, 0.8, 0.0, 0.9)
        chosen = NPlusFourSelector.select(
            baseline, [unsafe], preserve_advantage_tolerance=0.1,
            terminal_risk_tolerance=0.1,
        )
        self.assertEqual(chosen.action, "none")


if __name__ == "__main__":
    unittest.main()
