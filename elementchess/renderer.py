from __future__ import annotations

from enum import Enum

from .board import Board
from .domain import Cell, Element


class ViewMode(Enum):
    SUMMARY = "Synthèse"
    TERRAIN = "Terrains"
    ORIENTATION = "Orientations"
    TRANSITION = "Transitions"


class Renderer:
    RESET = "\033[0m"
    INVERT = "\033[7m"

    def __init__(self, colors: bool = True) -> None:
        self.colors = colors

    def render(self, board: Board, mode: ViewMode, cursor: tuple[int, int]) -> str:
        lines = [
            "ELEMENTCHESS — PROTOTYPE CONSOLE 0.23",
            f"Vue : {mode.value}   Plateau : 17×17   Zones : 9 × 5×5",
            "",
            "      " + " ".join(f" {chr(65 + x):^3}" for x in range(Board.SIZE)),
        ]

        for y, row in enumerate(board.rows()):
            tokens = [self._cell_token(cell, mode) for cell in row]
            rendered = []
            for x, token in enumerate(tokens):
                token = self._colorize(token, row[x].terrain)
                if (x, y) == cursor:
                    token = (
                        f"{self.INVERT}{token}{self.RESET}"
                        if self.colors
                        else f"[{token.strip():^3}]"
                    )
                rendered.append(token)
            lines.append(f"{y + 1:>3}  " + " ".join(rendered))

        selected = board.cell(*cursor)
        lines.extend(("", self._details(selected), "", self._help()))
        return "\n".join(lines)

    def _cell_token(self, cell: Cell, mode: ViewMode) -> str:
        if cell.is_border:
            return f" {cell.terrain.code:^3} "
        if mode is ViewMode.TERRAIN:
            return f" {cell.terrain.code:^3} "
        if mode is ViewMode.ORIENTATION:
            value = cell.piece.orientation.code if cell.piece else "--"
            return f" {value:^3} "
        if mode is ViewMode.TRANSITION:
            return f" {cell.transition.symbol:^3} "
        if cell.piece:
            return f"{cell.piece.symbol:^2}{cell.piece.orientation.arrow:^2} "
        return "  ·  "

    def _colorize(self, text: str, element: Element) -> str:
        if not self.colors or element is Element.NONE:
            return text
        return f"\033[{element.ansi_color}m{text}{self.RESET}"

    @staticmethod
    def _details(cell: Cell) -> str:
        piece = cell.piece
        piece_text = "aucune"
        if piece:
            piece_text = (
                f"{piece.identifier} ({piece.owner}), orientation "
                f"{piece.orientation.code}, affinité {piece.affinity.label}"
            )
        location = cell.zone_id or "bordure"
        return (
            f"Cellule {cell.coordinate} | {location} | terrain {cell.terrain.label} | "
            f"pièce {piece_text} | état {cell.transition.label}"
        )

    @staticmethod
    def _help() -> str:
        return (
            "[1] synthèse  [2] terrains  [3] orientations  [4] transitions  "
            "[flèches/ZQSD] curseur  [D] démo  [C] couleurs  [X/Échap] quitter"
        )
