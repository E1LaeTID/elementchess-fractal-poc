from __future__ import annotations

from dataclasses import dataclass

from .board import Board
from .domain import ChessCellState, Element, Orientation, Piece, TerrainOwner
from .events import PlayerToken


@dataclass(frozen=True, slots=True)
class SimulationPage:
    title: str
    objective: str
    instructions: str
    scenario: str | None = None


@dataclass(frozen=True, slots=True)
class SimulationSetup:
    active_owner: TerrainOwner
    hands: dict[TerrainOwner, tuple[PlayerToken, ...]]
    phase: str
    message: str
    forced_orientation: Orientation | None = None
    orientation_position: tuple[int, int] | None = None
    orientation_effect: tuple[Element, tuple[tuple[int, int, int], ...]] | None = None
    failure_count: int = 0


SIMULATION_PAGES = (
    SimulationPage(
        "Gagner par les terrains",
        "Compléter la troisième parcelle blanche et former un alignement de trois terrains.",
        "Deux parcelles de la rangée supérieure appartiennent déjà à Blanc. "
        "Sélectionnez l'unique jeton, puis posez-le sur la seule case vide du troisième terrain.",
        "terrain_victory",
    ),
    SimulationPage(
        "Orientation et influence",
        "Observer comment l'orientation d'une pièce complète la ligne et la colonne qu'elle vise.",
        "La dernière pièce est déjà placée. Orientez-la vers l'Est (→), verrouillez puis confirmez. "
        "Le jeton imposé apparaît alors sur la case terrain visée.",
        "orientation_effect",
    ),
    SimulationPage(
        "Attaque insuffisante",
        "Déclencher une troisième attaque repoussée et constater la défaite immédiate.",
        "La jauge blanche est préchargée à 2/3. Sélectionnez la tour blanche puis attaquez "
        "la dame noire : la résolution est automatique et la jauge atteint 3/3.",
        "failed_attack",
    ),
    SimulationPage(
        "Lire la notice",
        "Retrouver les règles complètes sans quitter la partie.",
        "Fermez ce livret puis appuyez sur F1 ou G. Choisissez un chapitre à gauche, utilisez "
        "les boutons de page en bas, puis Échap pour revenir au plateau.",
    ),
)


def _solution(board: Board, seed: int) -> dict[tuple[int, int], int]:
    board.generate_terrain_numbers(seed)
    values = {
        (cell.x, cell.y): int(cell.terrain_number)
        for row in board.rows() for cell in row
        if cell.terrain_number is not None
    }
    for row in board.rows():
        for cell in row:
            cell.terrain_number = None
            cell.terrain_owner = TerrainOwner.NONE
    return values


def load_simulation(board: Board, scenario: str) -> SimulationSetup:
    board.clear_demo()
    board.assign_random_elements(8241)
    values = _solution(board, 907)
    empty_hands = {TerrainOwner.WHITE: (), TerrainOwner.BLACK: ()}

    if scenario == "terrain_victory":
        for zone_id in ("Z11", "Z12"):
            for cell in board.zone_cells(zone_id):
                if not cell.is_chess_cell:
                    cell.terrain_number = values[(cell.x, cell.y)]
                    cell.terrain_owner = TerrainOwner.WHITE
            board.capture_zone(zone_id, TerrainOwner.WHITE)
        target = next(cell for cell in reversed(board.zone_cells("Z13")) if not cell.is_chess_cell)
        for cell in board.zone_cells("Z13"):
            if not cell.is_chess_cell and cell is not target:
                cell.terrain_number = values[(cell.x, cell.y)]
                cell.terrain_owner = TerrainOwner.WHITE
        # La règle normale exige qu'une pièce blanche occupe la parcelle ciblée.
        anchor = board.cell(11, 1)
        anchor.piece = Piece("white-rook", "R", "BLANC", Orientation.EAST, Element.NONE)
        anchor.chess_state = ChessCellState.OCCUPIED
        token = PlayerToken("simulation-victoire", TerrainOwner.WHITE, values[(target.x, target.y)])
        return SimulationSetup(
            TerrainOwner.WHITE,
            {TerrainOwner.WHITE: (token,), TerrainOwner.BLACK: ()},
            "tokens",
            f"Posez le jeton {token.value} sur {target.coordinate} pour gagner.",
        )

    if scenario == "orientation_effect":
        position = (7, 7)
        piece = Piece("white-queen", "Q", "BLANC", Orientation.NORTH, Element.NONE)
        board.cell(*position).piece = piece
        board.cell(*position).chess_state = ChessCellState.OCCUPIED
        target = (8, 7)
        pointed_element = Element.THUNDER
        board.assign_element(*target, pointed_element)
        cross = {
            (x, 7) for x in range(6, 11) if not board.cell(x, 7).is_chess_cell
        } | {
            (8, y) for y in range(6, 11) if not board.cell(8, y).is_chess_cell
        }
        effect = tuple((x, y, values[(x, y)]) for x, y in sorted(cross))
        return SimulationSetup(
            TerrainOwner.WHITE, empty_hands, "pieces",
            "Orientation imposée : Est (→). Verrouillez-la pour compléter la croix.",
            Orientation.EAST, position, (pointed_element, effect),
        )

    if scenario == "failed_attack":
        white = Piece("white-rook", "R", "BLANC", Orientation.NORTH, Element.NONE)
        black = Piece("black-queen", "q", "NOIR", Orientation.SOUTH, Element.NONE)
        for position, piece in (((1, 13), white), ((1, 5), black)):
            board.cell(*position).piece = piece
            board.cell(*position).chess_state = ChessCellState.OCCUPIED
        return SimulationSetup(
            TerrainOwner.WHITE, empty_hands, "pieces",
            "Jauge BLANC 2/3 : attaquez la dame noire avec la tour blanche.",
            failure_count=2,
        )
    raise KeyError(f"Simulation inconnue : {scenario}")
