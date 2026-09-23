from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .board import Board
from .balance import ElementMode, ElementSignatureField, RelationLevel
from .domain import Element, TerrainCellState, TerrainOwner
from .orientation_bonus import OrientationTerrainBonus
from .tokens import PlayerToken
from .time_engine import (
    IncrementalTimeEngine,
    WHEEL_EARTH,
    WHEEL_FIRE,
    WHEEL_ICE,
    WHEEL_MAGMAT,
    WHEEL_THUNDER,
    WHEEL_WATER,
    WHEEL_WIND,
    WHEEL_WOOD,
)


ELEMENT_POWER_ORDER = (
    Element.THUNDER,
    Element.MAGMAT,
    Element.ICE,
    Element.EARTH,
    Element.WOOD,
    Element.WIND,
    Element.FIRE,
    Element.WATER,
)

ELEMENT_WHEELS = {
    Element.THUNDER: WHEEL_THUNDER,
    Element.MAGMAT: WHEEL_MAGMAT,
    Element.ICE: WHEEL_ICE,
    Element.EARTH: WHEEL_EARTH,
    Element.WOOD: WHEEL_WOOD,
    Element.WIND: WHEEL_WIND,
    Element.FIRE: WHEEL_FIRE,
    Element.WATER: WHEEL_WATER,
}


class GameEventType(Enum):
    GRID_DISPLAYED = "grille_affichée"
    PIECES_PLACED = "pièces_placées"
    ELEMENTS_ASSIGNED = "éléments_assignés_secrètement"
    NUMBERS_PREPOSITIONED = "numéros_prépositionnés"
    INTERSTICE_OPENED = "interstice_ouvert"
    ELEMENT_DRAWN = "élément_tiré"
    ORIENTATION_BONUS = "bonus_orientation"
    TOKENS_DISTRIBUTED = "jetons_distribués"
    TERRAIN_CAPTURED = "état_terrain_capturé"
    ROTATION_QUEUED = "rotation_planifiée"
    TURN_ANNOUNCED = "tour_annoncé"


@dataclass(frozen=True, slots=True)
class GameEvent:
    type: GameEventType
    message: str
    element: Element = Element.NONE
    owner: TerrainOwner = TerrainOwner.NONE


@dataclass(frozen=True, slots=True)
class RotationCommand:
    element: Element
    wheel_id: str
    increments: int


class TerrainStateCapture:
    """Transforme l'état possédé et numéroté du terrain en commandes de roues."""

    @staticmethod
    def scores(board: Board) -> dict[Element, int]:
        scores = {element: 0 for element in ELEMENT_POWER_ORDER}
        for row in board.rows():
            for cell in row:
                if (
                    cell.terrain not in scores
                    or cell.terrain_number is None
                    or cell.terrain_owner is TerrainOwner.NONE
                    or cell.terrain_state is TerrainCellState.CAPTURED
                ):
                    continue
                base_coefficient = cell.y - 8
                owner_sign = -1 if cell.terrain_owner is TerrainOwner.WHITE else 1
                scores[cell.terrain] += cell.terrain_number * base_coefficient * owner_sign
        return scores

    @classmethod
    def commands(cls, board: Board, selected: tuple[Element, ...]) -> tuple[RotationCommand, ...]:
        scores = cls.scores(board)
        selected_set = set(selected)
        return tuple(
            RotationCommand(element, ELEMENT_WHEELS[element], scores[element])
            for element in ELEMENT_POWER_ORDER
            if element in selected_set
        )


class OpeningEventSystem:
    """Produit l'ouverture jusqu'à l'annonce du premier tour."""

    def __init__(self, board: Board, time_engine: IncrementalTimeEngine, seed: int | None = None) -> None:
        self.board = board
        self.time_engine = time_engine
        self.rng = random.Random(seed)
        self.events: list[GameEvent] = []
        self.drawn_elements: tuple[Element, ...] = ()
        self.rotation_commands: tuple[RotationCommand, ...] = ()
        self.element_signatures = ElementSignatureField()
        self.player_tokens: dict[TerrainOwner, tuple[PlayerToken, ...]] = {
            TerrainOwner.WHITE: (),
            TerrainOwner.BLACK: (),
        }
        self.token_serial = 0

    def prepare(self) -> tuple[GameEvent, ...]:
        self.display_grid()
        self.place_pieces()
        self.assign_elements()
        self.preposition_numbers()
        return tuple(self.events)

    def display_grid(self) -> GameEvent:
        self.board.clear_demo()
        event = GameEvent(GameEventType.GRID_DISPLAYED, "Grille 17×17 affichée")
        self.events = [event]
        return event

    def place_pieces(self) -> GameEvent:
        self.board.place_demo_pieces()
        event = GameEvent(GameEventType.PIECES_PLACED, "Pièces placées")
        self.events.append(event)
        return event

    def assign_elements(self) -> GameEvent:
        self.board.assign_random_elements(self.rng.randrange(2**32))
        event = GameEvent(GameEventType.ELEMENTS_ASSIGNED, "Éléments attribués face cachée")
        self.events.append(event)
        return event

    def preposition_numbers(self) -> GameEvent:
        self.board.preposition_terrain_numbers(self.rng.randrange(2**32))
        event = GameEvent(
            GameEventType.NUMBERS_PREPOSITIONED,
            "5 indices numériques prépositionnés dans chaque parcelle",
        )
        self.events.append(event)
        return event

    def open_first_interstice(self) -> tuple[GameEvent, ...]:
        return self.open_interstice(1, TerrainOwner.WHITE, initial=True)

    def open_interstice(
        self,
        turn_number: int,
        next_owner: TerrainOwner,
        *,
        initial: bool = False,
    ) -> tuple[GameEvent, ...]:
        label = "Interstice initial" if initial else f"Interstice avant le tour {turn_number}"
        batch = [GameEvent(GameEventType.INTERSTICE_OPENED, label)]
        self.drawn_elements = tuple(self.rng.sample(list(ELEMENT_POWER_ORDER), 3))
        batch.extend(
            GameEvent(GameEventType.ELEMENT_DRAWN, f"{element.label} révélé", element)
            for element in self.drawn_elements
        )
        bonuses = OrientationTerrainBonus.apply(self.board, self.drawn_elements)
        batch.extend(
            GameEvent(
                GameEventType.ORIENTATION_BONUS,
                (
                    f"Orientation {bonus.element.label} : {bonus.zone_id} complétée "
                    f"pour {bonus.owner.value} ({bonus.placed_count} case(s))"
                    + (f" · CAPTURÉE PAR {bonus.captured_owner.value}" if bonus.captured_owner is not TerrainOwner.NONE else "")
                ),
                bonus.element,
                bonus.owner,
            )
            for bonus in bonuses
        )
        for owner in (TerrainOwner.WHITE, TerrainOwner.BLACK):
            available_slots = max(0, 21 - len(self.player_tokens[owner]))
            distribution_size = 5 if initial else 2
            values = [self.rng.randint(1, 5) for _ in range(min(distribution_size, available_slots))]
            if set(values) == {1, 2, 3, 4, 5}:
                values[-1] = values[0]
            tokens: list[PlayerToken] = []
            for value in values:
                self.token_serial += 1
                tokens.append(PlayerToken(f"{owner.value.lower()}-{self.token_serial}", owner, value))
            self.player_tokens[owner] = self.player_tokens[owner] + tuple(tokens)
            values_label = " · ".join(str(token.value) for token in tokens) or "réserve pleine (21)"
            batch.append(
                GameEvent(
                    GameEventType.TOKENS_DISTRIBUTED,
                    f"Jetons {owner.value} : {values_label}",
                    owner=owner,
                )
            )
        batch.append(GameEvent(GameEventType.TERRAIN_CAPTURED, "État des cases terrain capturé"))
        self.rotation_commands = TerrainStateCapture.commands(self.board, self.drawn_elements)
        batch.extend(
            GameEvent(
                GameEventType.ROTATION_QUEUED,
                f"{command.element.label} : {command.increments:+d} incrément(s)",
                command.element,
            )
            for command in self.rotation_commands
        )
        batch.append(GameEvent(
            GameEventType.TURN_ANNOUNCED,
            f"TOUR {turn_number} — {next_owner.value}",
            owner=next_owner,
        ))
        self.events.extend(batch)
        return tuple(batch)

    def apply_rotation_commands(self) -> None:
        for command in self.rotation_commands:
            if command.increments == 0:
                self.element_signatures.set(command.element, ElementMode.NEUTRAL, RelationLevel.NEUTRAL)
                continue
            direction = 1 if command.increments > 0 else -1
            self.time_engine.rotate_manual(command.wheel_id, direction, abs(command.increments))
            level = RelationLevel(min(3, max(1, abs(command.increments))))
            mode = ElementMode.ACTIVE if command.increments > 0 else ElementMode.PASSIVE
            self.element_signatures.set(command.element, mode, level)
        # La signature est attachée à l'état logique, indépendamment du rendu.
        self.board.element_signatures = self.element_signatures
