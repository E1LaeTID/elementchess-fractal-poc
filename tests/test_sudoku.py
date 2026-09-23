import unittest

from elementchess.board import Board
from elementchess.domain import TerrainOwner
from elementchess.events import OpeningEventSystem
from elementchess.sudoku import (
    PlacementError,
    PlacementPhase,
    TerrainSudokuRules,
    TokenPlacementController,
)
from elementchess.time_engine import IncrementalTimeEngine


class TerrainSudokuRulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.board = Board()
        self.board.load_opening(seed=426)

    def test_rejects_chess_and_border_cells(self) -> None:
        with self.assertRaises(PlacementError):
            TerrainSudokuRules.validate(self.board, 1, 1, 1)
        with self.assertRaises(PlacementError):
            TerrainSudokuRules.validate(self.board, 0, 2, 1)

    def test_rejects_duplicate_on_local_row(self) -> None:
        self.board.cell(1, 2).terrain_number = 3
        with self.assertRaises(PlacementError):
            TerrainSudokuRules.validate(self.board, 2, 2, 3)

    def test_rejects_duplicate_on_local_column(self) -> None:
        self.board.cell(2, 1).terrain_number = 4
        with self.assertRaises(PlacementError):
            TerrainSudokuRules.validate(self.board, 2, 2, 4)

    def test_chess_cell_splits_row_constraints(self) -> None:
        # B2 et D2 sont séparées par C2, réservée aux pièces : le même chiffre
        # est donc autorisé dans les deux segments indépendants.
        self.board.cell(2, 1).terrain_number = 3
        self.board.cell(4, 1).terrain_number = None
        TerrainSudokuRules.validate(self.board, 4, 1, 3)

    def test_chess_cell_splits_column_constraints(self) -> None:
        self.board.cell(1, 2).terrain_number = 4
        self.board.cell(1, 4).terrain_number = None
        TerrainSudokuRules.validate(self.board, 1, 4, 4)

    def test_complete_five_cell_line_totals_fifteen(self) -> None:
        for x, value in zip(range(1, 6), (1, 2, 3, 4, 5)):
            TerrainSudokuRules.validate(self.board, x, 2, value)
            self.board.cell(x, 2).terrain_number = value
        self.assertEqual(sum(self.board.cell(x, 2).terrain_number or 0 for x in range(1, 6)), 15)

    def test_players_place_five_tokens_in_sequence(self) -> None:
        event_system = OpeningEventSystem(self.board, IncrementalTimeEngine(), seed=426)
        event_system.prepare()
        event_system.open_first_interstice()
        for row in self.board.rows():
            for cell in row:
                cell.terrain_number = None
        controller = TokenPlacementController(self.board, event_system.player_tokens)

        def place_hand(owner: TerrainOwner) -> None:
            for token in controller.remaining(owner):
                controller.select(token.identifier)
                placed = False
                for row in self.board.rows():
                    for cell in row:
                        try:
                            controller.place_selected(cell.x, cell.y)
                            placed = True
                            break
                        except PlacementError:
                            continue
                    if placed:
                        break
                self.assertTrue(placed)

        place_hand(TerrainOwner.WHITE)
        self.assertEqual(controller.active_owner, TerrainOwner.BLACK)
        self.assertEqual(controller.phase, PlacementPhase.BLACK_TOKENS)

        place_hand(TerrainOwner.BLACK)
        self.assertEqual(controller.phase, PlacementPhase.PIECES_PENDING)

    def test_player_can_keep_every_token_and_pass(self) -> None:
        event_system = OpeningEventSystem(self.board, IncrementalTimeEngine(), seed=426)
        event_system.prepare()
        event_system.open_first_interstice()
        controller = TokenPlacementController(
            self.board, event_system.player_tokens, (TerrainOwner.WHITE,)
        )
        before = controller.remaining(TerrainOwner.WHITE)
        self.assertEqual(controller.pass_tokens(), TerrainOwner.WHITE)
        self.assertEqual(controller.phase, PlacementPhase.PIECES_PENDING)
        self.assertEqual(controller.remaining(TerrainOwner.WHITE), before)

    def test_completed_zone_is_captured_and_locked(self) -> None:
        board = Board()
        board.load_opening(seed=426)
        zone_id = "Z11"
        cells = [cell for cell in board.zone_cells(zone_id) if not cell.is_chess_cell]
        # Une solution latine complète valide, avec majorité blanche.
        board.generate_terrain_numbers(seed=426)
        for index, cell in enumerate(cells):
            cell.terrain_owner = TerrainOwner.WHITE if index < 9 else TerrainOwner.BLACK
        owner = TerrainSudokuRules.capture_if_complete(board, zone_id)
        self.assertEqual(owner, TerrainOwner.WHITE)
        self.assertEqual(board.zone_owner(zone_id), TerrainOwner.WHITE)
        with self.assertRaises(PlacementError):
            TerrainSudokuRules.validate(board, cells[0].x, cells[0].y, 1)

    def test_recycling_is_all_or_nothing_and_respects_capacity(self) -> None:
        event_system = OpeningEventSystem(self.board, IncrementalTimeEngine(), seed=426)
        event_system.prepare()
        event_system.open_first_interstice()
        controller = TokenPlacementController(
            self.board, event_system.player_tokens, (TerrainOwner.WHITE,)
        )
        targets = []
        for token in controller.remaining(TerrainOwner.WHITE):
            controller.select(token.identifier)
            for cell in self.board.zone_cells("Z31"):
                try:
                    controller.place_selected(cell.x, cell.y)
                    targets.append(cell)
                    break
                except PlacementError:
                    continue
            if len(targets) == 2:
                break
        self.assertEqual(len(targets), 2)
        result = controller.recycle_zone_at(targets[0].x, targets[0].y)
        self.assertEqual(result.removed, 2)
        self.assertTrue(all(cell.terrain_owner is not TerrainOwner.WHITE for cell in self.board.zone_cells("Z31")))

    def test_token_requires_a_friendly_piece_inside_the_zone(self) -> None:
        event_system = OpeningEventSystem(self.board, IncrementalTimeEngine(), seed=426)
        event_system.prepare()
        event_system.open_first_interstice()
        controller = TokenPlacementController(
            self.board, event_system.player_tokens, (TerrainOwner.WHITE,)
        )
        target = next(
            cell for cell in self.board.zone_cells("Z11")
            if not cell.is_chess_cell and cell.terrain_number is None
        )
        controller.select(controller.remaining(TerrainOwner.WHITE)[0].identifier)
        with self.assertRaisesRegex(PlacementError, "occupée"):
            controller.place_selected(target.x, target.y)


if __name__ == "__main__":
    unittest.main()
