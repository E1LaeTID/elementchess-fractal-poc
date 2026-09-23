from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CombatFailureTracker:
    """Jauge 0..3, avec récupération d'un cran après deux coups propres."""

    failures: dict[str, int] = field(default_factory=lambda: {"BLANC": 0, "NOIR": 0})
    clean_turns: dict[str, int] = field(default_factory=lambda: {"BLANC": 0, "NOIR": 0})
    failed_this_turn: set[str] = field(default_factory=set)

    def record_failure(self, owner: str) -> int:
        self.failures[owner] = min(3, self.failures[owner] + 1)
        self.clean_turns[owner] = 0
        self.failed_this_turn.add(owner)
        return self.failures[owner]

    def finish_turn(self, owner: str) -> int:
        if owner in self.failed_this_turn:
            self.failed_this_turn.remove(owner)
            return self.failures[owner]
        self.clean_turns[owner] += 1
        if self.clean_turns[owner] >= 2 and self.failures[owner] > 0:
            self.failures[owner] -= 1
            self.clean_turns[owner] = 0
        return self.failures[owner]

    def defeated(self, owner: str) -> bool:
        return self.failures[owner] >= 3
