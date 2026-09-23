from __future__ import annotations

import unittest

from elementchess.board import Board
from elementchess.domain import ChessCellState, Element, Orientation, Piece, TerrainOwner
from elementchess.events import GameEventType, OpeningEventSystem
from elementchess.orientation_bonus import OrientationTerrainBonus
from elementchess.time_engine import IncrementalTimeEngine


def place_piece(board: Board, x: int, y: int, owner: str, orientation: Orientation) -> None:
    prefix = "white" if owner == "BLANC" else "black"
    board.cell(x, y).piece = Piece(
        f"{prefix}-rook", "R", owner, orientation, Element.NONE, True
    )
    board.cell(x, y).chess_state = ChessCellState.OCCUPIED


class _ForcedDraw:
    def sample(self, _population, _count):
        return [Element.FIRE, Element.WATER, Element.WIND]

    def randint(self, minimum, _maximum):
        return minimum


class OrientationBonusTests(unittest.TestCase):
    def test_opponent_occupying_target_zone_receives_bonus(self) -> None:
        board = Board()
        place_piece(board, 5, 3, "BLANC", Orientation.EAST)
        place_piece(board, 7, 3, "NOIR", Orientation.WEST)
        board.assign_element(6, 3, Element.FIRE)

        results = OrientationTerrainBonus.apply(board, (Element.FIRE,))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].owner, TerrainOwner.BLACK)
        generated = [
            cell for cell in board.zone_cells("Z12")
            if cell.terrain_owner is TerrainOwner.BLACK and cell.terrain_number is not None
        ]
        self.assertGreater(len(generated), 0)

    def test_equal_piece_count_is_decided_by_existing_token_count(self) -> None:
        board = Board()
        place_piece(board, 7, 7, "BLANC", Orientation.EAST)
        place_piece(board, 9, 9, "NOIR", Orientation.NORTH)
        board.assign_element(8, 7, Element.THUNDER)
        for x, y, owner in (
            (6, 6, TerrainOwner.WHITE),
            (8, 6, TerrainOwner.BLACK),
            (10, 6, TerrainOwner.BLACK),
        ):
            board.cell(x, y).terrain_number = 1
            board.cell(x, y).terrain_owner = owner

        results = OrientationTerrainBonus.apply(board, (Element.THUNDER,))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].owner, TerrainOwner.BLACK)

    def test_perfect_occupation_tie_does_not_assign_arbitrary_bonus(self) -> None:
        board = Board()
        place_piece(board, 7, 7, "BLANC", Orientation.EAST)
        place_piece(board, 9, 9, "NOIR", Orientation.NORTH)
        board.assign_element(8, 7, Element.THUNDER)

        results = OrientationTerrainBonus.apply(board, (Element.THUNDER,))

        self.assertEqual(results, ())
        self.assertTrue(all(
            cell.terrain_number is None for cell in board.zone_cells("Z22")
        ))

    def test_real_interstice_applies_bonus_and_emits_event(self) -> None:
        board = Board()
        place_piece(board, 5, 3, "BLANC", Orientation.EAST)
        place_piece(board, 7, 3, "NOIR", Orientation.WEST)
        board.assign_element(6, 3, Element.FIRE)
        system = OpeningEventSystem(board, IncrementalTimeEngine())
        system.rng = _ForcedDraw()

        events = system.open_interstice(2, TerrainOwner.WHITE)

        bonuses = [event for event in events if event.type is GameEventType.ORIENTATION_BONUS]
        self.assertEqual(len(bonuses), 1)
        self.assertEqual(bonuses[0].owner, TerrainOwner.BLACK)
        self.assertIn("Z12", bonuses[0].message)


if __name__ == "__main__":
    unittest.main()
