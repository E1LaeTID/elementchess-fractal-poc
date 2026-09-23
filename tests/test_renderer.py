import unittest

from elementchess.board import Board
from elementchess.renderer import Renderer, ViewMode


class RendererTest(unittest.TestCase):
    def setUp(self) -> None:
        self.board = Board()
        self.board.load_demo()
        self.renderer = Renderer(colors=False)

    def test_each_view_renders_selected_cell_details(self) -> None:
        for mode in ViewMode:
            with self.subTest(mode=mode):
                output = self.renderer.render(self.board, mode, (8, 8))
                self.assertIn("Cellule I9", output)
                self.assertIn(mode.value, output)

    def test_transition_view_contains_transition_markers(self) -> None:
        output = self.renderer.render(self.board, ViewMode.TRANSITION, (0, 0))
        self.assertIn(" * ", output)
        self.assertIn(" # ", output)


if __name__ == "__main__":
    unittest.main()
