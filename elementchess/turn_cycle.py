from __future__ import annotations

from dataclasses import dataclass

from .domain import TerrainOwner


@dataclass(slots=True)
class RoundCycle:
    """Boucle classique : Blanc, Noir, puis interstice de fin de ronde."""

    round_number: int = 1
    active_owner: TerrainOwner = TerrainOwner.WHITE

    def finish_piece_move(self) -> bool:
        """Passe la main et indique si les deux joueurs ont terminé."""
        if self.active_owner is TerrainOwner.WHITE:
            self.active_owner = TerrainOwner.BLACK
            return False
        self.active_owner = TerrainOwner.WHITE
        self.round_number += 1
        return True
