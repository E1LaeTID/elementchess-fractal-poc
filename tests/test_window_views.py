import unittest

from elementchess.movement import PieceMove
from elementchess.window import ElementChessWindow, WindowView


class WindowViewTest(unittest.TestCase):
    def test_number_view_is_removed_from_public_navigation(self):
        self.assertEqual(
            {view.name for view in WindowView},
            {"TERRAIN", "CHESS", "TIME"},
        )

    def test_hover_detection_only_accepts_legal_destinations(self):
        window = ElementChessWindow.__new__(ElementChessWindow)
        window.view = WindowView.CHESS
        window.legal_piece_moves = {
            (3, 5): PieceMove((3, 7), (3, 5), ((3, 6),)),
        }
        window._layout = lambda: (10.0, 20.0, 170.0)
        self.assertEqual(window._legal_destination_at(45.0, 75.0), (3, 5))
        self.assertIsNone(window._legal_destination_at(35.0, 75.0))
        self.assertIsNone(window._legal_destination_at(500.0, 500.0))


if __name__ == "__main__":
    unittest.main()
