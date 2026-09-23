from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isclose, pi


WHEEL_GAME = "wheel_game"
WHEEL_WATER = "wheel_water"
WHEEL_FIRE = "wheel_fire"
WHEEL_WIND = "wheel_wind"
WHEEL_WOOD = "wheel_wood"
WHEEL_EARTH = "wheel_earth"
WHEEL_ICE = "wheel_ice"
WHEEL_MAGMAT = "wheel_magmat"
WHEEL_THUNDER = "wheel_thunder"


@dataclass(frozen=True, slots=True)
class WheelSpec:
    identifier: str
    label: str
    radius: float | None
    tooth_count: int | None
    tooth_angle: float | None
    controllable: bool = True
    rack_length: float | None = None
    rim_width: float | None = None

    @property
    def is_rack(self) -> bool:
        return self.rack_length is not None

    @property
    def tooth_pitch(self) -> float:
        if self.is_rack:
            return 25 * pi
        if self.radius is None or self.tooth_angle is None:
            raise ValueError(f"Dimensions incomplètes pour {self.identifier}")
        return self.radius * self.tooth_angle


@dataclass(slots=True)
class WheelState:
    spec: WheelSpec
    position: int = 0

    @property
    def angle(self) -> float:
        if self.spec.tooth_angle is None:
            return 0.0
        return self.position * self.spec.tooth_angle


@dataclass(frozen=True, slots=True)
class RotationStep:
    identifier: str
    delta_teeth: int
    position_before: int
    position_after: int


class IncrementalTimeEngine:
    """Propagation discrète d'une impulsion dans le train élémentaire.

    Une impulsion correspond au passage d'une dent commune. Chaque contact
    inverse le sens. Quand la topologie contient plusieurs chemins vers une
    même roue, le premier chemin le plus court fixe la vague et évite de
    compter plusieurs fois la même impulsion.
    """

    COMMON_TOOTH_PITCH = 25 * pi

    def __init__(self) -> None:
        small = (
            (WHEEL_WATER, "Eau"),
            (WHEEL_FIRE, "Feu"),
            (WHEEL_WIND, "Vent"),
            (WHEEL_WOOD, "Bois"),
            (WHEEL_MAGMAT, "Magmat"),
            (WHEEL_THUNDER, "Foudre"),
        )
        specs = [
            WheelSpec(WHEEL_GAME, "Principale", 800, 64, pi / 32, controllable=False),
            *(WheelSpec(identifier, label, 200, 16, pi / 8) for identifier, label in small),
            WheelSpec(WHEEL_EARTH, "Terre", 1200, 96, pi / 48, rim_width=400),
            WheelSpec(WHEEL_ICE, "Glace", None, None, None, rack_length=4800),
        ]
        self.states = {spec.identifier: WheelState(spec) for spec in specs}
        self.contacts = self._create_contacts()
        self.last_wave: tuple[RotationStep, ...] = ()
        self._validate_geometry()

    @staticmethod
    def _create_contacts() -> dict[str, set[str]]:
        pairs = (
            (WHEEL_GAME, WHEEL_WATER),
            (WHEEL_GAME, WHEEL_FIRE),
            (WHEEL_GAME, WHEEL_WIND),
            (WHEEL_GAME, WHEEL_WOOD),
            (WHEEL_WIND, WHEEL_MAGMAT),
            (WHEEL_WOOD, WHEEL_THUNDER),
            (WHEEL_MAGMAT, WHEEL_EARTH),
            (WHEEL_THUNDER, WHEEL_EARTH),
            (WHEEL_EARTH, WHEEL_ICE),
        )
        contacts: dict[str, set[str]] = {}
        for first, second in pairs:
            contacts.setdefault(first, set()).add(second)
            contacts.setdefault(second, set()).add(first)
        return contacts

    def _validate_geometry(self) -> None:
        for state in self.states.values():
            if not isclose(
                state.spec.tooth_pitch,
                self.COMMON_TOOTH_PITCH,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise ValueError(f"Pas de dent incompatible : {state.spec.identifier}")

    @property
    def controllable_identifiers(self) -> tuple[str, ...]:
        return tuple(
            identifier
            for identifier, state in self.states.items()
            if state.spec.controllable
        )

    def rotate_manual(
        self,
        identifier: str,
        direction: int,
        increments: int = 1,
    ) -> tuple[RotationStep, ...]:
        if identifier not in self.states:
            raise KeyError(f"Roue inconnue : {identifier}")
        if not self.states[identifier].spec.controllable:
            raise PermissionError("La roue principale ne possède pas de commande manuelle")
        if direction not in (-1, 1):
            raise ValueError("La direction doit valoir -1 ou +1")
        if increments < 1:
            raise ValueError("Le nombre d'incréments doit être positif")

        deltas = self._propagation_wave(identifier, direction * increments)
        steps: list[RotationStep] = []
        for wheel_id, delta in deltas.items():
            state = self.states[wheel_id]
            before = state.position
            if state.spec.is_rack:
                state.position += delta
            else:
                assert state.spec.tooth_count is not None
                state.position = (state.position + delta) % state.spec.tooth_count
            steps.append(RotationStep(wheel_id, delta, before, state.position))
        self.last_wave = tuple(steps)
        return self.last_wave

    def advance_main(self, increments: int = 1) -> RotationStep:
        """Avance l'horloge principale et propage son cran dans tout le train."""
        if increments < 1:
            raise ValueError("Le nombre d'incréments doit être positif")
        deltas = self._propagation_wave(WHEEL_GAME, increments)
        steps: list[RotationStep] = []
        for identifier, delta in deltas.items():
            state = self.states[identifier]
            before = state.position
            if state.spec.is_rack:
                state.position += delta
            else:
                assert state.spec.tooth_count is not None
                state.position = (state.position + delta) % state.spec.tooth_count
            steps.append(RotationStep(identifier, delta, before, state.position))
        self.last_wave = tuple(steps)
        return next(step for step in self.last_wave if step.identifier == WHEEL_GAME)

    def _propagation_wave(self, source: str, delta: int) -> dict[str, int]:
        deltas = {source: delta}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for neighbor in sorted(self.contacts.get(current, ())):
                if neighbor in deltas:
                    continue
                deltas[neighbor] = -deltas[current]
                queue.append(neighbor)
        return deltas
