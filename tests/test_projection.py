import unittest

from elementchess.projection import ChessPosition, ChessProjection


class ChessProjectionTest(unittest.TestCase):
    def test_corner_positions_map_inside_17_by_17_terrain(self) -> None:
        self.assertEqual(ChessProjection.terrain_anchor(ChessPosition(0, 0)), (1, 1))
        self.assertEqual(ChessProjection.terrain_anchor(ChessPosition(7, 7)), (15, 15))

    def test_adjacent_positions_leave_one_shared_environment_cell(self) -> None:
        first = ChessProjection.terrain_anchor(ChessPosition(2, 4))
        second = ChessProjection.terrain_anchor(ChessPosition(3, 4))
        self.assertEqual(second[0] - first[0], 2)
        self.assertEqual(first[0] + 1, 6)

    def test_only_odd_terrain_coordinates_are_piece_anchors(self) -> None:
        self.assertEqual(ChessProjection.from_terrain(7, 9), ChessPosition(3, 4))
        self.assertIsNone(ChessProjection.from_terrain(8, 9))


if __name__ == "__main__":
    unittest.main()
