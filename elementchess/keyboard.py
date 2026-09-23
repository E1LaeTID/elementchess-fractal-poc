from __future__ import annotations

import os
import sys


def read_key() -> str:
    """Lit une touche sans validation par Entrée, sous Windows et POSIX."""
    if os.name == "nt":
        import msvcrt

        first = msvcrt.getwch()
        if first in ("\x00", "\xe0"):
            return {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}.get(
                msvcrt.getwch(), "UNKNOWN"
            )
        return "ESC" if first == "\x1b" else first

    import termios
    import tty
    import select

    descriptor = sys.stdin.fileno()
    previous = termios.tcgetattr(descriptor)
    try:
        tty.setraw(descriptor)
        first = sys.stdin.read(1)
        if first == "\x1b":
            if not select.select([sys.stdin], [], [], 0.03)[0]:
                return "ESC"
            second = sys.stdin.read(1)
            if second != "[":
                return "ESC"
            if not select.select([sys.stdin], [], [], 0.03)[0]:
                return "ESC"
            return {"A": "UP", "B": "DOWN", "D": "LEFT", "C": "RIGHT"}.get(
                sys.stdin.read(1), "ESC"
            )
        return first
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)
