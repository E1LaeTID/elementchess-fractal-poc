import unittest

from elementchess.board import Board
from elementchess.domain import BoundaryKind, Element, TerrainCellState


class BoardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.board = Board()
        self.board.load_demo()

    def test_board_contains_17_by_17_cells(self) -> None:
        self.assertEqual(len(self.board.rows()), 17)
        self.assertTrue(all(len(row) == 17 for row in self.board.rows()))

    def test_nine_zones_each_contain_25_cells(self) -> None:
        counts: dict[str, int] = {}
        for row in self.board.rows():
            for cell in row:
                if cell.zone_id:
                    counts[cell.zone_id] = counts.get(cell.zone_id, 0) + 1
        self.assertEqual(len(counts), 9)
        self.assertTrue(all(count == 25 for count in counts.values()))

    def test_one_cell_border_surrounds_compact_15_by_15_zones(self) -> None:
        for index in range(17):
            self.assertTrue(self.board.cell(index, 0).is_border)
            self.assertTrue(self.board.cell(index, 16).is_border)
            self.assertTrue(self.board.cell(0, index).is_border)
            self.assertTrue(self.board.cell(16, index).is_border)
        self.assertEqual(self.board.cell(5, 5).zone_id, "Z11")
        self.assertEqual(self.board.cell(6, 5).zone_id, "Z12")
        self.assertEqual(self.board.cell(15, 15).zone_id, "Z33")

    def test_circumference_has_elements_but_no_numbers(self) -> None:
        circumference = [cell for row in self.board.rows() for cell in row if cell.is_border]
        self.assertEqual(len(circumference), 64)
        self.assertTrue(all(cell.terrain is not Element.NONE for cell in circumference))
        self.assertTrue(all(cell.terrain_number is None for cell in circumference))
        self.assertTrue(all(cell.terrain_state is TerrainCellState.ASSIGNED for cell in circumference))

    def test_circumference_distinguishes_lateral_and_angular_borders(self) -> None:
        angular = [cell for row in self.board.rows() for cell in row if cell.boundary_kind is BoundaryKind.ANGULAR]
        lateral = [cell for row in self.board.rows() for cell in row if cell.boundary_kind is BoundaryKind.LATERAL]
        self.assertEqual(len(angular), 4)
        self.assertEqual(len(lateral), 60)

    def test_every_chess_cell_has_eight_environment_neighbors(self) -> None:
        for row in self.board.rows():
            for cell in row:
                if cell.is_chess_cell:
                    self.assertEqual(len(self.board.neighbors8(cell.x, cell.y)), 8)

    def test_new_grid_is_unassigned_before_generation_pipeline(self) -> None:
        board = Board()
        self.assertTrue(all(cell.terrain is Element.NONE for row in board.rows() for cell in row))
        self.assertTrue(
            all(
                cell.terrain_state is (
                    TerrainCellState.NOT_APPLICABLE if cell.is_chess_cell else TerrainCellState.UNASSIGNED
                )
                for row in board.rows() for cell in row
            )
        )
        self.assertTrue(all(cell.terrain_number is None for row in board.rows() for cell in row))
        self.assertFalse(any(cell.piece for row in board.rows() for cell in row))

    def test_element_assignment_is_reusable(self) -> None:
        board = Board()
        board.assign_element(8, 8, Element.FIRE)
        self.assertEqual(board.cell(8, 8).terrain, Element.FIRE)
        self.assertEqual(board.cell(8, 8).terrain_state, TerrainCellState.ASSIGNED)
        board.assign_element(8, 8, Element.ICE)
        self.assertEqual(board.cell(8, 8).terrain, Element.ICE)

    def test_exactly_64_odd_odd_coordinates_are_chess_cells(self) -> None:
        chess_cells = [cell for row in self.board.rows() for cell in row if cell.is_chess_cell]
        self.assertEqual(len(chess_cells), 64)

    def test_demo_contains_32_pieces_only_on_chess_cells(self) -> None:
        self.board.load_demo()
        occupied = [cell for row in self.board.rows() for cell in row if cell.piece]
        self.assertEqual(len(occupied), 32)
        self.assertTrue(all(cell.is_chess_cell for cell in occupied))

    def test_chess_cells_never_receive_terrain_data(self) -> None:
        chess_cells = [cell for row in self.board.rows() for cell in row if cell.is_chess_cell]
        self.assertTrue(all(cell.terrain is Element.NONE for cell in chess_cells))
        self.assertTrue(all(cell.terrain_number is None for cell in chess_cells))
        self.assertTrue(all(cell.terrain_state is TerrainCellState.NOT_APPLICABLE for cell in chess_cells))

    def test_element_assignment_rejects_a_chess_cell(self) -> None:
        with self.assertRaises(ValueError):
            self.board.assign_element(1, 1, Element.FIRE)

    def test_coordinates_are_human_readable(self) -> None:
        self.assertEqual(self.board.cell(0, 0).coordinate, "A1")
        self.assertEqual(self.board.cell(16, 16).coordinate, "Q17")


if __name__ == "__main__":
    unittest.main()
