import unittest

from elementchess.board import Board
from elementchess.domain import Orientation, TerrainOwner
from elementchess.simulation import SIMULATION_PAGES, load_simulation
from elementchess.sudoku import TerrainSudokuRules, TokenPlacementController


class SimulationBookTest(unittest.TestCase):
    def test_book_contains_three_playable_scenarios_and_guide_page(self) -> None:
        self.assertEqual(len(SIMULATION_PAGES), 4)
        self.assertEqual(sum(page.scenario is not None for page in SIMULATION_PAGES), 3)

    def test_terrain_scenario_wins_with_its_only_token(self) -> None:
        board = Board()
        setup = load_simulation(board, "terrain_victory")
        self.assertEqual(board.terrain_winner(), TerrainOwner.NONE)
        controller = TokenPlacementController(board, setup.hands, (TerrainOwner.WHITE,))
        token = setup.hands[TerrainOwner.WHITE][0]
        controller.select(token.identifier)
        target = next(
            cell for cell in board.zone_cells("Z13")
            if not cell.is_chess_cell and cell.terrain_number is None
        )
        result = controller.place_selected(target.x, target.y)
        self.assertEqual(result.captured_owner, TerrainOwner.WHITE)
        self.assertEqual(board.terrain_winner(), TerrainOwner.WHITE)

    def test_orientation_scenario_exposes_forced_direction_and_effect(self) -> None:
        board = Board()
        setup = load_simulation(board, "orientation_effect")
        self.assertEqual(setup.forced_orientation, Orientation.EAST)
        self.assertIsNotNone(setup.orientation_position)
        self.assertIsNotNone(setup.orientation_effect)
        element, placements = setup.orientation_effect or (None, ())
        self.assertIsNotNone(element)
        self.assertGreater(len(placements), 1)
        for x, y, value in placements:
            self.assertIsNone(board.cell(x, y).terrain_number)
            self.assertIn(value, range(1, 6))

    def test_failed_attack_scenario_starts_at_two_failures(self) -> None:
        board = Board()
        setup = load_simulation(board, "failed_attack")
        self.assertEqual(setup.failure_count, 2)
        self.assertEqual(board.cell(1, 13).piece.owner, "BLANC")
        self.assertEqual(board.cell(1, 5).piece.owner, "NOIR")

    def test_terrain_winner_accepts_rows_columns_and_diagonals(self) -> None:
        for zones in (("Z11", "Z12", "Z13"), ("Z11", "Z21", "Z31"), ("Z13", "Z22", "Z31")):
            board = Board()
            for zone_id in zones:
                board.capture_zone(zone_id, TerrainOwner.BLACK)
            self.assertEqual(board.terrain_winner(), TerrainOwner.BLACK)


if __name__ == "__main__":
    unittest.main()
