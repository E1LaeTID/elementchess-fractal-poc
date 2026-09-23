from __future__ import annotations

from dataclasses import dataclass

from .domain import TerrainOwner


@dataclass(frozen=True, slots=True)
class PlayerToken:
    identifier: str
    owner: TerrainOwner
    value: int
