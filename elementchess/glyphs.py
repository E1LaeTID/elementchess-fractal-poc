from __future__ import annotations

from dataclasses import dataclass

from .domain import Element, Orientation, Piece


GLYPH_SIZE = 5


@dataclass(frozen=True, slots=True)
class GlyphToken:
    column: int
    row: int
    text: str
    role: str

    def __post_init__(self) -> None:
        if not (0 <= self.column < GLYPH_SIZE and 0 <= self.row < GLYPH_SIZE):
            raise ValueError("Un symbole de cellule doit rester dans la matrice 5×5")


ORIENTATION_SLOT = {
    Orientation.NORTH: (2, 0),
    Orientation.NORTH_EAST: (4, 0),
    Orientation.EAST: (4, 2),
    Orientation.SOUTH_EAST: (4, 4),
    Orientation.SOUTH: (2, 4),
    Orientation.SOUTH_WEST: (0, 4),
    Orientation.WEST: (0, 2),
    Orientation.NORTH_WEST: (0, 0),
}


PIECE_SYMBOLS = {
    "white-king": "♔",
    "white-queen": "♕",
    "white-rook": "♖",
    "white-bishop": "♗",
    "white-knight": "♘",
    "white-pawn": "♙",
    "black-king": "♚",
    "black-queen": "♛",
    "black-rook": "♜",
    "black-bishop": "♝",
    "black-knight": "♞",
    "black-pawn": "♟",
}


ELEMENT_SYMBOLS = {
    Element.NONE: "·",
    Element.WATER: "≈",
    Element.FIRE: "△",
    Element.WIND: "↝",
    Element.WOOD: "♧",
    Element.EARTH: "◆",
    Element.ICE: "✧",
    Element.MAGMAT: "◈",
    Element.THUNDER: "ϟ",
}


def chess_glyph(piece: Piece) -> tuple[GlyphToken, ...]:
    arrow_column, arrow_row = ORIENTATION_SLOT[piece.orientation]
    player_role = "white" if piece.owner == "BLANC" else "black"
    return (
        GlyphToken(2, 2, PIECE_SYMBOLS.get(piece.identifier, piece.symbol), f"piece_{player_role}"),
        GlyphToken(arrow_column, arrow_row, piece.orientation.arrow, f"orientation_{player_role}"),
    )


def terrain_glyph(element: Element, number: int | None) -> tuple[GlyphToken, ...]:
    """Place le nombre au centre et la signature élémentaire dans l'angle.

    La matrice logique 5×5 reste inchangée : seule sa représentation évolue.
    """
    tokens = [GlyphToken(0, 0, ELEMENT_SYMBOLS[element], "element_corner")]
    if number is not None:
        tokens.append(GlyphToken(2, 2, str(number), f"number_center_{element.name.lower()}"))
    return tuple(tokens)
