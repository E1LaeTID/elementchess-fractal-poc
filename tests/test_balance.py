import unittest

from elementchess.balance import (
    BalanceCombatCalculator,
    BalanceConfig,
    ConfrontationGeometry,
    ElementMode,
    ElementSignatureField,
    RelationLevel,
)
from elementchess.board import Board
from elementchess.domain import ChessCellState, Element, Orientation, Piece
from elementchess.movement import PieceMove
from elementchess.power_effects import PowerEffectLedger


class BalanceTest(unittest.TestCase):
    def _report(self, start, destination):
        board = Board()
        board.clear_demo()
        board.assign_random_elements(12)
        attacker = Piece("white-rook", "R", "BLANC", Orientation.NORTH)
        defender = Piece("black-rook", "r", "NOIR", Orientation.SOUTH)
        board.cell(*start).piece = attacker
        board.cell(*start).chess_state = ChessCellState.OCCUPIED
        board.cell(*destination).piece = defender
        board.cell(*destination).chess_state = ChessCellState.OCCUPIED
        signatures = ElementSignatureField()
        signatures.set(Element.FIRE, ElementMode.ACTIVE, RelationLevel.DOUBLE)
        move = PieceMove(start, destination, (), defender)
        return board, BalanceCombatCalculator(signatures=signatures).calculate(board, move)

    def test_line_anchor_spans_zero_to_four_hundred_with_offset(self):
        config = BalanceConfig()
        self.assertEqual(config.line_coefficient(8), 0)
        self.assertEqual(config.line_coefficient(0), 400)
        self.assertEqual(config.line_power(8), 100)
        self.assertEqual(config.line_power(16), 500)

    def test_three_geometries_are_distinguished(self):
        cases = (
            ((7, 9), (7, 7), ConfrontationGeometry.FORWARD),
            ((7, 7), (9, 7), ConfrontationGeometry.HORIZONTAL),
            ((7, 7), (9, 9), ConfrontationGeometry.DIAGONAL),
        )
        for start, destination, expected in cases:
            _, report = self._report(start, destination)
            self.assertEqual(report.geometry, expected)
            self.assertGreaterEqual(report.attack.total, 100)
            self.assertGreaterEqual(report.defense.total, 100)

    def test_equal_power_is_anchored_at_one_third_defense(self):
        _, report = self._report((7, 7), (9, 7))
        equal_report = type(report)(report.geometry, report.attack, report.attack, report.config)
        self.assertAlmostEqual(equal_report.defense_win_probability, 1 / 3)
        self.assertAlmostEqual(equal_report.attack_win_probability, 2 / 3)

    def test_combat_probability_is_bounded_and_favors_power_advantage(self):
        _, report = self._report((7, 7), (9, 7))
        stronger_defense = type(report)(report.geometry, report.attack, report.defense, report.config)
        probability = stronger_defense.defense_win_probability
        self.assertGreaterEqual(probability, report.config.defense_probability_minimum)
        self.assertLessEqual(probability, report.config.defense_probability_maximum)

    def test_noncombat_effect_starts_at_next_round_and_expires(self):
        board = Board()
        board.clear_demo()
        board.assign_random_elements(9)
        board.cell(7, 7).piece = Piece("white-pawn", "P", "BLANC")
        field = ElementSignatureField()
        for cell in board.neighbors8(7, 7):
            field.set(cell.terrain, ElementMode.ACTIVE, RelationLevel.SIMPLE)
        ledger = PowerEffectLedger()
        effect = ledger.schedule_from_adjacency(board, (7, 7), field, 3)
        self.assertEqual(ledger.modifiers(effect.piece_id, 3), (0, 0))
        self.assertNotEqual(ledger.modifiers(effect.piece_id, 4), (0, 0))
        ledger.expire(4)
        self.assertEqual(ledger.modifiers(effect.piece_id, 5), (0, 0))

    def test_position_estimate_is_bounded_and_uses_adjacency(self):
        board = Board()
        board.clear_demo()
        board.assign_random_elements(21)
        estimate = BalanceCombatCalculator().estimate_position(board, (7, 7))
        self.assertGreaterEqual(estimate.minimum, 100)
        self.assertGreater(estimate.maximum, estimate.minimum)
        self.assertEqual(estimate.adjacent_elements, 8)
        self.assertEqual(estimate.uncertain_elements, 8)

    def test_known_signatures_narrow_position_estimate(self):
        board = Board()
        board.clear_demo()
        board.assign_random_elements(21)
        signatures = ElementSignatureField()
        for cell in board.neighbors8(7, 7):
            signatures.set(cell.terrain, ElementMode.ACTIVE, RelationLevel.SIMPLE)
        estimate = BalanceCombatCalculator(signatures=signatures).estimate_position(board, (7, 7))
        self.assertEqual(estimate.uncertain_elements, 0)

    def test_move_forecast_uses_selected_piece_and_keeps_two_ranges(self):
        board = Board()
        board.clear_demo()
        board.assign_random_elements(31)
        piece = Piece("white-rook", "R", "BLANC", Orientation.NORTH)
        board.cell(7, 9).piece = piece
        board.cell(7, 9).chess_state = ChessCellState.OCCUPIED
        move = PieceMove((7, 9), (7, 7), ((7, 8),))
        forecast = BalanceCombatCalculator().estimate_move(board, move)
        self.assertGreaterEqual(forecast.attack.minimum, 100)
        self.assertGreaterEqual(forecast.defense.minimum, 100)
        self.assertGreaterEqual(forecast.attack.maximum, forecast.attack.minimum)
        self.assertGreaterEqual(forecast.defense.maximum, forecast.defense.minimum)

    def test_move_forecast_requires_a_piece_at_start(self):
        board = Board()
        board.clear_demo()
        board.assign_random_elements(31)
        with self.assertRaises(ValueError):
            BalanceCombatCalculator().estimate_move(
                board, PieceMove((7, 9), (7, 7), ((7, 8),))
            )


if __name__ == "__main__":
    unittest.main()
