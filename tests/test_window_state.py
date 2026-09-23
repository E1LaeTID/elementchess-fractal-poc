from __future__ import annotations

import unittest
from unittest.mock import patch

from elementchess.board import Board
from elementchess.window import ElementChessWindow
from elementchess.domain import Piece, TerrainOwner


class _IdleRoot:
    def __init__(self) -> None:
        self.callback = None

    def after_idle(self, callback) -> None:
        self.callback = callback


class WindowStateTests(unittest.TestCase):
    def test_finish_game_records_unambiguous_outcome(self) -> None:
        window = ElementChessWindow.__new__(ElementChessWindow)
        window.game_over_owner = None
        window.action_message = ""
        window.root = _IdleRoot()
        draws: list[bool] = []
        window.draw = lambda: draws.append(True)

        window._finish_game("NOIR", "BLANC", "trois attaques repoussées")

        self.assertEqual(window.game_over_owner, "BLANC")
        self.assertIn("NOIR A GAGNÉ", window.action_message)
        self.assertIn("BLANC A PERDU", window.action_message)
        self.assertIn("trois attaques repoussées", window.action_message)
        self.assertEqual(draws, [True])
        self.assertIsNotNone(window.root.callback)

    def test_failed_defensive_attack_ends_game_before_turn_changes(self) -> None:
        window = ElementChessWindow.__new__(ElementChessWindow)
        window.board = Board()
        window.pending_orientation_position = (3, 3)
        window.pending_orientation_queue = [(5, 3)]
        window.pending_move_transaction = object()
        window.pending_move_can_rollback = True
        window.selected_piece_position = (7, 15)
        window.legal_piece_moves = {(7, 13): object()}
        outcome: list[tuple[str, str, str]] = []
        window._finish_game = lambda winner, loser, cause: outcome.append((winner, loser, cause))

        with patch(
            "elementchess.window.MovementEngine.checked_kings",
            return_value={"BLANC": (7, 15)},
        ):
            terminal = window._finish_failed_defense_if_checked("BLANC")

        self.assertTrue(terminal)
        self.assertEqual(outcome[0][:2], ("NOIR", "BLANC"))
        self.assertIn("roi toujours en échec", outcome[0][2])
        self.assertIsNone(window.pending_orientation_position)
        self.assertEqual(window.legal_piece_moves, {})

    def test_failed_attack_outside_check_is_not_terminal(self) -> None:
        window = ElementChessWindow.__new__(ElementChessWindow)
        window.board = Board()
        with patch("elementchess.window.MovementEngine.checked_kings", return_value={}):
            self.assertFalse(window._finish_failed_defense_if_checked("BLANC"))

    def test_checkmate_finishes_game_with_winner_and_loser(self) -> None:
        window = ElementChessWindow.__new__(ElementChessWindow)
        window.board = Board()
        window.board.clear_demo()
        window.board.cell(1, 1).piece = Piece("black-king", "k", "NOIR")
        window.board.cell(3, 3).piece = Piece("white-queen", "Q", "BLANC")
        window.board.cell(5, 5).piece = Piece("white-king", "K", "BLANC")
        outcome = []
        window._finish_game = lambda winner, loser, reason: outcome.append((winner, loser, reason))
        self.assertTrue(window._finish_checkmate_if_any())
        self.assertEqual(outcome, [("BLANC", "NOIR", "échec et mat")])

    def test_low_rejection_rate_enables_element_cycle_at_n_plus_four(self) -> None:
        window = ElementChessWindow.__new__(ElementChessWindow)
        window.board = Board()
        window.board.load_demo()
        window.current_turn = 4
        window.blocked_zone_streaks = {
            f"Z{row}{column}": 0 for row in range(1, 4) for column in range(1, 4)
        }
        window.combat_rejections = [False, False, False]
        window.combat_expected_rejections = [1 / 3, 1 / 3, 1 / 3]
        window.action_message = ""
        window.sudoku_correction = None
        record = window._run_balance_cycle()
        self.assertIsNotNone(record)
        self.assertTrue(record.global_scope)
        self.assertEqual(record.indicator_badge, "○")


if __name__ == "__main__":
    unittest.main()
