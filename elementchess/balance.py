from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import ceil
from typing import Iterable, Mapping

from .board import Board
from .domain import Element, Piece, TerrainOwner
from .movement import PieceMove


class ConfrontationGeometry(Enum):
    FORWARD = "avance"
    HORIZONTAL = "horizontale"
    DIAGONAL = "diagonale"


class ElementMode(Enum):
    NEUTRAL = 0
    ACTIVE = 1
    PASSIVE = -1


class RelationLevel(Enum):
    NEUTRAL = 0
    SIMPLE = 1
    DOUBLE = 2
    TRIPLE = 3


@dataclass(frozen=True, slots=True)
class BalanceConfig:
    """Paramètres calibrables, séparés des identifiants du jeu.

    Les numéros de terrain (1..5), indices d'éléments, coefficients de ligne,
    puissances de pièces et niveaux de relation ne partagent aucun domaine.
    """

    minimum_power: int = 100
    line_step: int = 50
    relation_step: int = 50
    piece_scale: int = 20
    orientation_bonus: int = 25
    token_support_scale: int = 5
    defense_probability_anchor: float = 1 / 3
    combat_probability_scale: int = 900
    defense_probability_minimum: float = 0.12
    defense_probability_maximum: float = 0.65

    def __post_init__(self) -> None:
        if self.minimum_power < 100:
            raise ValueError("La puissance minimale doit être au moins 100")
        if min(self.line_step, self.relation_step, self.piece_scale) <= 0:
            raise ValueError("Les granularités doivent être strictement positives")
        if self.combat_probability_scale <= 0:
            raise ValueError("L'échelle probabiliste doit être strictement positive")
        if not 0 <= self.defense_probability_minimum <= self.defense_probability_maximum <= 1:
            raise ValueError("Les bornes probabilistes doivent appartenir à [0, 1]")

    def line_coefficient(self, row: int) -> int:
        if not 0 <= row <= 16:
            raise ValueError("Une ligne du plateau doit être comprise entre 0 et 16")
        return abs(row - 8) * self.line_step

    def line_power(self, row: int) -> int:
        return self.minimum_power + self.line_coefficient(row)


@dataclass(frozen=True, slots=True)
class ElementSignature:
    mode: ElementMode = ElementMode.NEUTRAL
    level: RelationLevel = RelationLevel.NEUTRAL


@dataclass(slots=True)
class ElementSignatureField:
    """Signature propagée à toutes les cellules portant le même élément."""

    signatures: dict[Element, ElementSignature] = field(default_factory=dict)

    def signature(self, element: Element) -> ElementSignature:
        return self.signatures.get(element, ElementSignature())

    def set(self, element: Element, mode: ElementMode, level: RelationLevel) -> None:
        if element is Element.NONE:
            raise ValueError("NONE ne peut pas recevoir de signature")
        self.signatures[element] = ElementSignature(mode, level)


@dataclass(frozen=True, slots=True)
class LineEvaluation:
    name: str
    coordinates: tuple[tuple[int, int], ...]
    base_power: int
    elemental_delta: int

    @property
    def total(self) -> int:
        return max(100, self.base_power + self.elemental_delta)


@dataclass(frozen=True, slots=True)
class BalancedPower:
    piece: int
    orientation: int
    terrain_support: int
    lines: tuple[LineEvaluation, ...]

    @property
    def affinity(self) -> int:
        return sum(line.elemental_delta for line in self.lines)

    @property
    def line_power(self) -> int:
        if not self.lines:
            return 100
        return ceil(sum(line.total for line in self.lines) / len(self.lines))

    @property
    def total(self) -> int:
        return max(100, self.line_power + self.piece + self.orientation + self.terrain_support)


@dataclass(frozen=True, slots=True)
class BalancedCombatReport:
    geometry: ConfrontationGeometry
    attack: BalancedPower
    defense: BalancedPower
    config: BalanceConfig = field(default_factory=BalanceConfig)

    @property
    def defense_win_probability(self) -> float:
        """Chance bornée de repousser l'assaut, centrée sur un tiers.

        Les puissances restent déterminantes sans rendre le résultat certain :
        à forces égales la défense gagne une fois sur trois, puis l'écart de
        puissance déplace progressivement cette probabilité.
        """
        delta = self.defense.total - self.attack.total
        raw = self.config.defense_probability_anchor + delta / self.config.combat_probability_scale
        return min(self.config.defense_probability_maximum, max(self.config.defense_probability_minimum, raw))

    @property
    def attack_win_probability(self) -> float:
        return 1.0 - self.defense_win_probability

    @property
    def attacker_wins(self) -> bool:
        """Comparaison de diagnostic conservée pour les outils historiques."""
        return self.attack.total >= self.defense.total


@dataclass(frozen=True, slots=True)
class PotentialPowerEstimate:
    """Intervalle prudent avant qu'une pièce précise ne soit choisie."""

    minimum: int
    maximum: int
    adjacent_elements: int
    uncertain_elements: int


@dataclass(frozen=True, slots=True)
class MovePowerForecast:
    """Fourchettes illustratives pour une destination légale déjà calculée."""

    attack: PotentialPowerEstimate
    defense: PotentialPowerEstimate


class BalanceCombatCalculator:
    PIECE_VALUES = {"pawn": 1, "knight": 3, "bishop": 3, "rook": 5, "queen": 9, "king": 10}

    def __init__(
        self,
        config: BalanceConfig | None = None,
        signatures: ElementSignatureField | None = None,
    ) -> None:
        self.config = config or BalanceConfig()
        self.signatures = signatures or ElementSignatureField()

    @staticmethod
    def _kind(piece: Piece) -> str:
        return piece.identifier.split("-", 1)[1]

    @staticmethod
    def geometry(piece: Piece, move: PieceMove) -> ConfrontationGeometry:
        dx = move.destination[0] - move.start[0]
        dy = move.destination[1] - move.start[1]
        if dx and dy:
            return ConfrontationGeometry.DIAGONAL
        if dx:
            return ConfrontationGeometry.HORIZONTAL
        forward = -1 if piece.owner == TerrainOwner.WHITE.value else 1
        return ConfrontationGeometry.FORWARD if dy * forward > 0 else ConfrontationGeometry.HORIZONTAL

    @staticmethod
    def _inside(x: int, y: int) -> bool:
        return 0 <= x <= 16 and 0 <= y <= 16

    @classmethod
    def _line(cls, center: tuple[int, int], direction: tuple[int, int]) -> tuple[tuple[int, int], ...]:
        """Trois cellules du voisinage faisant face à l'autre pièce."""
        x, y = center
        dx, dy = direction
        perpendicular = (-dy, dx)
        result = []
        for offset in (-1, 0, 1):
            point = (x + dx + perpendicular[0] * offset, y + dy + perpendicular[1] * offset)
            if cls._inside(*point):
                result.append(point)
        return tuple(result)

    @classmethod
    def _side_lines(cls, center: tuple[int, int], direction: tuple[int, int]) -> tuple[tuple[tuple[int, int], ...], ...]:
        x, y = center
        dx, dy = direction
        right = (-dy, dx)
        groups = []
        for depth in (-1, 0, 1):
            group = []
            for lateral in (-1, 0, 1):
                if depth == lateral == 0:
                    continue
                point = (x + dx * depth + right[0] * lateral, y + dy * depth + right[1] * lateral)
                if cls._inside(*point):
                    group.append(point)
            if group:
                groups.append(tuple(group))
        return tuple(groups)

    def _element_delta(self, board: Board, coordinates: Iterable[tuple[int, int]]) -> int:
        deltas = []
        for x, y in coordinates:
            element = board.cell(x, y).terrain
            signature = self.signatures.signature(element)
            deltas.append(signature.mode.value * signature.level.value * self.config.relation_step)
        active = [delta for delta in deltas if delta]
        return 0 if not active else ceil(sum(active) / len(active))

    def estimate_position(
        self,
        board: Board,
        position: tuple[int, int],
    ) -> PotentialPowerEstimate:
        """Borne la puissance locale à partir des huit cellules adjacentes.

        Une signature connue contribue avec sa valeur actuelle. Une signature
        neutre est traitée comme encore indéterminée, entre relation passive et
        active triple. La fourchette inclut la plus petite et la plus grande
        valeur de pièce ; elle ne révèle donc aucune issue de combat.
        """
        x, y = position
        neighbors = tuple(
            cell for cell in board.neighbors8(x, y)
            if cell.terrain is not Element.NONE
        )
        deltas_min: list[int] = []
        deltas_max: list[int] = []
        uncertain = 0
        extreme = RelationLevel.TRIPLE.value * self.config.relation_step
        for cell in neighbors:
            signature = self.signatures.signature(cell.terrain)
            if signature.mode is ElementMode.NEUTRAL or signature.level is RelationLevel.NEUTRAL:
                deltas_min.append(-extreme)
                deltas_max.append(extreme)
                uncertain += 1
            else:
                delta = signature.mode.value * signature.level.value * self.config.relation_step
                deltas_min.append(delta)
                deltas_max.append(delta)
        elemental_min = ceil(sum(deltas_min) / len(deltas_min)) if deltas_min else 0
        elemental_max = ceil(sum(deltas_max) / len(deltas_max)) if deltas_max else 0
        base = self.config.line_power(y)
        smallest_piece = min(self.PIECE_VALUES.values()) * self.config.piece_scale
        largest_piece = max(self.PIECE_VALUES.values()) * self.config.piece_scale
        return PotentialPowerEstimate(
            minimum=max(self.config.minimum_power, base + elemental_min + smallest_piece),
            maximum=max(
                self.config.minimum_power,
                base + elemental_max + largest_piece + self.config.orientation_bonus,
            ),
            adjacent_elements=len(neighbors),
            uncertain_elements=uncertain,
        )

    def estimate_move(self, board: Board, move: PieceMove) -> MovePowerForecast:
        """Projette attaque et défense sans résoudre ni annoncer un combat.

        La pièce doit encore se trouver au départ et la destination doit avoir
        été validée par le moteur de déplacement. Les signatures neutres
        restent des bornes : le résultat sert à illustrer le concept, jamais à
        promettre une puissance finale.
        """
        piece = board.cell(*move.start).piece
        if piece is None:
            raise ValueError("La prévision exige une pièce au départ")
        local = self.estimate_position(board, move.destination)
        piece_power = self.PIECE_VALUES[self._kind(piece)] * self.config.piece_scale
        generic_min_piece = min(self.PIECE_VALUES.values()) * self.config.piece_scale
        generic_max_piece = max(self.PIECE_VALUES.values()) * self.config.piece_scale
        local_floor = local.minimum - generic_min_piece
        local_ceiling = local.maximum - generic_max_piece - self.config.orientation_bonus
        path_support = self._support(board, move.path, piece.owner, self.config.token_support_scale)
        neighbors = tuple((cell.x, cell.y) for cell in board.neighbors8(*move.destination))
        defense_support = self._support(board, neighbors, piece.owner, self.config.token_support_scale)
        attack = PotentialPowerEstimate(
            minimum=max(self.config.minimum_power, local_floor + piece_power + path_support),
            maximum=max(
                self.config.minimum_power,
                local_ceiling + piece_power + path_support + self.config.orientation_bonus,
            ),
            adjacent_elements=local.adjacent_elements,
            uncertain_elements=local.uncertain_elements,
        )
        defense = PotentialPowerEstimate(
            minimum=max(self.config.minimum_power, local_floor + piece_power + defense_support),
            maximum=max(
                self.config.minimum_power,
                local_ceiling + piece_power + defense_support + self.config.orientation_bonus,
            ),
            adjacent_elements=local.adjacent_elements,
            uncertain_elements=local.uncertain_elements,
        )
        return MovePowerForecast(attack=attack, defense=defense)

    def _evaluate_lines(
        self,
        board: Board,
        named_lines: Iterable[tuple[str, tuple[tuple[int, int], ...]]],
    ) -> tuple[LineEvaluation, ...]:
        result = []
        for name, coordinates in named_lines:
            if not coordinates:
                continue
            base = ceil(sum(self.config.line_power(y) for _, y in coordinates) / len(coordinates))
            result.append(LineEvaluation(name, coordinates, base, self._element_delta(board, coordinates)))
        return tuple(result)

    @staticmethod
    def _support(board: Board, coordinates: Iterable[tuple[int, int]], owner: str, scale: int) -> int:
        expected = TerrainOwner.WHITE if owner == TerrainOwner.WHITE.value else TerrainOwner.BLACK
        values = [
            board.cell(x, y).terrain_number or 0
            for x, y in coordinates
            if board.cell(x, y).terrain_owner is expected
            and board.zone_owner(board.cell(x, y).zone_id) is TerrainOwner.NONE
        ]
        return 0 if not values else scale * ceil(sum(values) / len(values))

    def calculate(self, board: Board, move: PieceMove) -> BalancedCombatReport:
        attacker = board.cell(*move.start).piece
        defender = board.cell(*move.destination).piece
        if attacker is None or defender is None:
            raise ValueError("Le calcul exige une pièce attaquante et une pièce défensive")
        dx = (move.destination[0] > move.start[0]) - (move.destination[0] < move.start[0])
        dy = (move.destination[1] > move.start[1]) - (move.destination[1] < move.start[1])
        direction = (dx, dy)
        geometry = self.geometry(attacker, move)

        attack_front = self._line(move.start, direction)
        defense_front = self._line(move.destination, (-dx, -dy))
        if geometry is ConfrontationGeometry.FORWARD:
            attack_groups = (("complément_attaquant", attack_front),)
            defense_groups = (("ligne_commune", defense_front),)
        elif geometry is ConfrontationGeometry.HORIZONTAL:
            attack_groups = tuple(
                (f"attaque_ligne_{index + 1}", line)
                for index, line in enumerate(self._side_lines(move.start, direction))
            )
            defense_groups = tuple(
                (f"défense_ligne_{index + 1}", line)
                for index, line in enumerate(self._side_lines(move.destination, (-dx, -dy)))
            )
        else:
            start_neighbors = {(cell.x, cell.y) for cell in board.neighbors8(*move.start)}
            destination_neighbors = {(cell.x, cell.y) for cell in board.neighbors8(*move.destination)}
            common = tuple(sorted(start_neighbors & destination_neighbors, key=lambda point: (point[1], point[0]))) or defense_front[:1]
            excluded_elements = {board.cell(x, y).terrain for x, y in common}
            attack_only = tuple(
                coordinate for coordinate in attack_front
                if board.cell(*coordinate).terrain not in excluded_elements
            )
            attack_groups = (("diagonale_sans_commun", attack_only or attack_front),)
            defense_groups = (("élément_commun", common), ("voisins_défense", defense_front))

        attack_lines = self._evaluate_lines(board, attack_groups)
        defense_lines = self._evaluate_lines(board, defense_groups)
        attack = BalancedPower(
            piece=self.PIECE_VALUES[self._kind(attacker)] * self.config.piece_scale,
            orientation=self.config.orientation_bonus if attacker.orientation.code in self._direction_codes(dx, dy) else 0,
            terrain_support=self._support(board, move.path, attacker.owner, self.config.token_support_scale),
            lines=attack_lines,
        )
        defense_neighbors = tuple((cell.x, cell.y) for cell in board.neighbors8(*move.destination))
        defense = BalancedPower(
            piece=self.PIECE_VALUES[self._kind(defender)] * self.config.piece_scale,
            orientation=self.config.orientation_bonus if defender.orientation.code in self._direction_codes(-dx, -dy) else 0,
            terrain_support=self._support(board, defense_neighbors, defender.owner, self.config.token_support_scale),
            lines=defense_lines,
        )
        return BalancedCombatReport(geometry, attack, defense, self.config)

    @staticmethod
    def _direction_codes(dx: int, dy: int) -> tuple[str, ...]:
        horizontal = "E" if dx > 0 else "O" if dx < 0 else ""
        vertical = "S" if dy > 0 else "N" if dy < 0 else ""
        code = vertical + horizontal
        return (code,)
