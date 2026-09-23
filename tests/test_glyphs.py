import unittest

from elementchess.domain import Element, Orientation, Piece
from elementchess.glyphs import GLYPH_SIZE, ORIENTATION_SLOT, chess_glyph, terrain_glyph


class GlyphTest(unittest.TestCase):
    def test_all_orientation_slots_fit_the_normalized_5_by_5_cell(self) -> None:
        self.assertEqual(len(ORIENTATION_SLOT), 8)
        for column, row in ORIENTATION_SLOT.values():
            self.assertTrue(0 <= column < GLYPH_SIZE)
            self.assertTrue(0 <= row < GLYPH_SIZE)

    def test_piece_is_centered_and_arrow_uses_orientation_slot(self) -> None:
        piece = Piece("white-knight", "N", "BLANC", Orientation.SOUTH_EAST, Element.WIND)
        tokens = chess_glyph(piece)
        piece_token = next(token for token in tokens if token.role == "piece_white")
        arrow_token = next(token for token in tokens if token.role == "orientation_white")
        self.assertEqual((piece_token.column, piece_token.row), (2, 2))
        self.assertEqual((arrow_token.column, arrow_token.row), (4, 4))
        self.assertEqual(piece_token.text, "♘")

    def test_black_and_white_pieces_expose_distinct_render_roles(self) -> None:
        white = Piece("white-king", "K", "BLANC", Orientation.NORTH, Element.NONE)
        black = Piece("black-king", "k", "NOIR", Orientation.SOUTH, Element.NONE)
        white_roles = {token.role for token in chess_glyph(white)}
        black_roles = {token.role for token in chess_glyph(black)}
        self.assertEqual(white_roles, {"piece_white", "orientation_white"})
        self.assertEqual(black_roles, {"piece_black", "orientation_black"})

    def test_terrain_number_and_element_have_distinct_slots(self) -> None:
        tokens = terrain_glyph(Element.WATER, 5)
        number = next(token for token in tokens if token.role.startswith("number_center_"))
        element = next(token for token in tokens if token.role == "element_corner")
        self.assertEqual((number.column, number.row), (2, 2))
        self.assertEqual((element.column, element.row), (0, 0))


if __name__ == "__main__":
    unittest.main()
