from __future__ import annotations

import os
import sys

from .board import Board
from .keyboard import read_key
from .renderer import Renderer, ViewMode


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def run_terminal() -> None:
    board = Board()
    board.load_demo()
    renderer = Renderer(colors=True)
    mode = ViewMode.SUMMARY
    cursor = [8, 8]
    demo_enabled = True

    while True:
        clear_screen()
        print(renderer.render(board, mode, (cursor[0], cursor[1])))
        key = read_key()
        normalized = key.lower() if len(key) == 1 else key

        if normalized in ("x", "ESC"):
            break
        if key == "D":
            demo_enabled = not demo_enabled
            board.load_demo() if demo_enabled else board.clear_demo()
            continue
        if normalized == "1":
            mode = ViewMode.SUMMARY
        elif normalized == "2":
            mode = ViewMode.TERRAIN
        elif normalized == "3":
            mode = ViewMode.ORIENTATION
        elif normalized == "4":
            mode = ViewMode.TRANSITION
        elif normalized in ("UP", "z"):
            cursor[1] = max(0, cursor[1] - 1)
        elif normalized in ("DOWN", "s"):
            cursor[1] = min(Board.SIZE - 1, cursor[1] + 1)
        elif normalized in ("LEFT", "q"):
            cursor[0] = max(0, cursor[0] - 1)
        elif normalized in ("RIGHT", "d"):
            cursor[0] = min(Board.SIZE - 1, cursor[0] + 1)
        elif normalized == "c":
            renderer.colors = not renderer.colors
    clear_screen()
    print("ElementChess fermé proprement.")


def main() -> None:
    if "--terminal" in sys.argv:
        run_terminal()
        return

    from .window import run_window

    run_window()
