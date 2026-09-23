import unittest

from elementchess.board import Board
from elementchess.domain import ChessCellState, Element, Orientation, Piece, TerrainOwner
from elementchess.combat import CombatCalculator
from elementchess.movement import (
    DefensiveMoveTransaction,
    MoveTransaction,
    MovementEngine,
    PieceMove,
)


class MovementEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.board = Board()
        self.board.load_demo()

    def test_pawn_exposes_one_and_two_step_destinations_with_paths(self) -> None:
        moves = MovementEngine.legal_moves(self.board, 1, 13)
        destinations = {move.destination: move for move in moves}
        self.assertIn((1, 11), destinations)
        self.assertIn((1, 9), destinations)
        self.assertEqual(destinations[(1, 11)].path, ((1, 12),))
        self.assertEqual(destinations[(1, 9)].path, ((1, 12), (1, 11), (1, 10)))

    def test_sliding_piece_is_blocked_by_its_own_pawn(self) -> None:
        self.assertEqual(MovementEngine.legal_moves(self.board, 1, 15), ())

    def test_knight_has_a_visible_intermediate_route(self) -> None:
        moves = MovementEngine.legal_moves(self.board, 3, 15)
        self.assertTrue(moves)
        self.assertTrue(all(move.path for move in moves))
        occupied = {
            (cell.x, cell.y)
            for row in self.board.rows() for cell in row
            if cell.piece and (cell.x, cell.y) != (3, 15)
        }
        self.assertTrue(all(not occupied.intersection(move.path) for move in moves))

    def test_enemy_destination_is_reported_as_an_attack(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(1, 13).piece = Piece("white-rook", "R", "BLANC", Orientation.NORTH, Element.NONE)
        board.cell(1, 13).chess_state = ChessCellState.OCCUPIED
        board.cell(1, 5).piece = Piece("black-pawn", "p", "NOIR", Orientation.SOUTH, Element.NONE)
        board.cell(1, 5).chess_state = ChessCellState.OCCUPIED
        move = next(move for move in MovementEngine.legal_moves(board, 1, 13) if move.destination == (1, 5))
        self.assertTrue(move.is_attack)

    def test_combat_report_includes_piece_orientation_and_terrain_support(self) -> None:
        board = Board()
        board.clear_demo()
        attacker = Piece("white-rook", "R", "BLANC", Orientation.NORTH, Element.FIRE)
        defender = Piece("black-pawn", "p", "NOIR", Orientation.SOUTH, Element.WATER)
        board.cell(1, 13).piece = attacker
        board.cell(1, 13).chess_state = ChessCellState.OCCUPIED
        board.cell(1, 5).piece = defender
        board.cell(1, 5).chess_state = ChessCellState.OCCUPIED
        board.cell(1, 12).terrain_number = 4
        board.cell(1, 12).terrain_owner = TerrainOwner.WHITE
        move = next(move for move in MovementEngine.legal_moves(board, 1, 13) if move.destination == (1, 5))
        report = CombatCalculator.calculate(board, move)
        self.assertEqual(report.attack.piece, 100)
        self.assertEqual(report.attack.orientation, 25)
        self.assertGreaterEqual(report.attack.terrain_support, 20)
        self.assertGreater(report.attack.total, report.defense.total)

    def test_pawn_is_promoted_on_the_opposite_line(self) -> None:
        white = self.board.cell(1, 13).piece
        black = self.board.cell(1, 3).piece
        self.assertIsNotNone(white)
        self.assertIsNotNone(black)
        promoted_white = MovementEngine.promote_if_needed(white, (1, 1))
        promoted_black = MovementEngine.promote_if_needed(black, (1, 15))
        self.assertTrue(promoted_white.identifier.endswith("-queen"))
        self.assertEqual(promoted_white.symbol, "Q")
        self.assertTrue(promoted_black.identifier.endswith("-queen"))
        self.assertEqual(promoted_black.symbol, "q")

    def test_pawn_is_really_promoted_by_the_move_transaction(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(1, 3).piece = Piece("white-pawn", "P", "BLANC")
        board.cell(1, 3).chess_state = ChessCellState.OCCUPIED
        move = next(
            move for move in MovementEngine.legal_moves(board, 1, 3)
            if move.destination == (1, 1)
        )
        MoveTransaction.apply(board, move)
        promoted = board.cell(1, 1).piece
        self.assertEqual(promoted.identifier, "white-queen")
        self.assertEqual(promoted.symbol, "Q")

    def test_defensive_pair_is_order_independent_on_right_edge(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(9, 15).piece = Piece("white-king", "K", "BLANC")
        board.cell(15, 15).piece = Piece("white-rook", "R", "BLANC")
        geometry = MovementEngine.defensive_pair_geometry(
            board, (15, 15), (9, 15)
        )
        self.assertEqual(geometry, ((9, 15), (15, 15), (13, 15), (11, 15)))

    def test_defensive_pair_moves_both_pieces_and_rolls_back(self) -> None:
        board = Board()
        board.clear_demo()
        king = Piece("white-king", "K", "BLANC")
        rook = Piece("white-rook", "R", "BLANC")
        board.cell(9, 15).piece = king
        board.cell(1, 15).piece = rook
        geometry = MovementEngine.defensive_pair_geometry(board, (9, 15), (1, 15))
        transaction = DefensiveMoveTransaction.apply(board, *geometry)
        self.assertIs(board.cell(3, 15).piece, king)
        self.assertIs(board.cell(5, 15).piece, rook)
        transaction.rollback(board)
        self.assertIs(board.cell(9, 15).piece, king)
        self.assertIs(board.cell(1, 15).piece, rook)

    def test_defensive_pair_rejects_a_piece_between_king_and_rook(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(9, 15).piece = Piece("white-king", "K", "BLANC")
        board.cell(15, 15).piece = Piece("white-rook", "R", "BLANC")
        board.cell(11, 15).piece = Piece("white-bishop", "B", "BLANC")
        with self.assertRaisesRegex(ValueError, "bloque"):
            MovementEngine.defensive_pair_geometry(board, (9, 15), (15, 15))

    def test_failed_attack_stops_on_last_free_chess_cell(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(1, 13).piece = Piece("white-rook", "R", "BLANC")
        board.cell(1, 13).chess_state = ChessCellState.OCCUPIED
        board.cell(1, 5).piece = Piece("black-pawn", "p", "NOIR")
        board.cell(1, 5).chess_state = ChessCellState.OCCUPIED
        move = next(
            move for move in MovementEngine.legal_moves(board, 1, 13)
            if move.destination == (1, 5)
        )
        self.assertEqual(MovementEngine.failed_attack_destination(board, move), (1, 7))

    def test_move_transaction_restores_start_and_captured_piece(self) -> None:
        board = Board()
        board.clear_demo()
        attacker = Piece("white-rook", "R", "BLANC")
        defender = Piece("black-pawn", "p", "NOIR")
        board.cell(1, 13).piece = attacker
        board.cell(1, 13).chess_state = ChessCellState.OCCUPIED
        board.cell(1, 5).piece = defender
        board.cell(1, 5).chess_state = ChessCellState.OCCUPIED
        move = PieceMove((1, 13), (1, 5), (), defender)
        transaction = MoveTransaction.apply(board, move)
        self.assertIs(board.cell(1, 5).piece, attacker)
        transaction.rollback(board)
        self.assertIs(board.cell(1, 13).piece, attacker)
        self.assertIs(board.cell(1, 5).piece, defender)

    def test_checked_king_is_detected_for_rook_and_pawn(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(7, 7).piece = Piece("white-king", "K", "BLANC")
        board.cell(7, 1).piece = Piece("black-rook", "r", "NOIR")
        self.assertEqual(MovementEngine.checked_kings(board), {"BLANC": (7, 7)})

        board.cell(7, 1).piece = None
        board.cell(5, 5).piece = Piece("black-pawn", "p", "NOIR", Orientation.SOUTH)
        self.assertEqual(MovementEngine.checked_kings(board), {"BLANC": (7, 7)})

    def test_check_forbids_an_unrelated_piece_move(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(7, 15).piece = Piece("white-king", "K", "BLANC")
        board.cell(7, 1).piece = Piece("black-rook", "r", "NOIR")
        board.cell(1, 15).piece = Piece("white-knight", "N", "BLANC")
        self.assertEqual(MovementEngine.legal_moves(board, 1, 15), ())

    def test_check_allows_a_piece_to_interpose(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(7, 15).piece = Piece("white-king", "K", "BLANC")
        board.cell(7, 1).piece = Piece("black-rook", "r", "NOIR")
        board.cell(3, 13).piece = Piece("white-bishop", "B", "BLANC")
        destinations = {
            move.destination for move in MovementEngine.legal_moves(board, 3, 13)
        }
        self.assertEqual(destinations, {(7, 9)})

    def test_king_cannot_move_to_an_attacked_square(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(7, 15).piece = Piece("white-king", "K", "BLANC")
        board.cell(7, 1).piece = Piece("black-rook", "r", "NOIR")
        destinations = {
            move.destination for move in MovementEngine.legal_moves(board, 7, 15)
        }
        self.assertNotIn((7, 13), destinations)

    def test_black_checkmate_is_detected(self) -> None:
        board = Board()
        board.clear_demo()
        board.cell(1, 1).piece = Piece("black-king", "k", "NOIR")
        board.cell(3, 3).piece = Piece("white-queen", "Q", "BLANC")
        board.cell(5, 5).piece = Piece("white-king", "K", "BLANC")
        self.assertTrue(MovementEngine.is_checkmate(board, "NOIR"))
        self.assertFalse(MovementEngine.has_legal_move(board, "NOIR"))


if __name__ == "__main__":
    unittest.main()
