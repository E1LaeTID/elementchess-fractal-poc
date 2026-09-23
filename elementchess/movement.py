from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from dataclasses import replace
from math import gcd

from .board import Board
from .domain import ChessCellState, Piece


@dataclass(frozen=True, slots=True)
class PieceMove:
    start: tuple[int, int]
    destination: tuple[int, int]
    path: tuple[tuple[int, int], ...]
    captured_piece: Piece | None = None

    @property
    def is_attack(self) -> bool:
        return self.captured_piece is not None


@dataclass(frozen=True, slots=True)
class MoveTransaction:
    move: PieceMove
    start_piece: Piece
    destination_piece: Piece | None
    start_state: ChessCellState
    destination_state: ChessCellState

    @classmethod
    def apply(cls, board: Board, move: PieceMove) -> "MoveTransaction":
        start_cell = board.cell(*move.start)
        destination_cell = board.cell(*move.destination)
        if start_cell.piece is None:
            raise ValueError("Aucune pièce à déplacer")
        transaction = cls(
            move=move,
            start_piece=start_cell.piece,
            destination_piece=destination_cell.piece,
            start_state=start_cell.chess_state,
            destination_state=destination_cell.chess_state,
        )
        start_cell.piece = None
        start_cell.chess_state = ChessCellState.EMPTY
        destination_cell.piece = MovementEngine.promote_if_needed(
            transaction.start_piece, move.destination
        )
        destination_cell.chess_state = ChessCellState.OCCUPIED
        return transaction

    def rollback(self, board: Board) -> None:
        start_cell = board.cell(*self.move.start)
        destination_cell = board.cell(*self.move.destination)
        start_cell.piece = self.start_piece
        start_cell.chess_state = self.start_state
        destination_cell.piece = self.destination_piece
        destination_cell.chess_state = self.destination_state


@dataclass(frozen=True, slots=True)
class DefensiveMoveTransaction:
    """Transaction atomique du déplacement défensif roi-tour d'ElementChess."""

    move: PieceMove
    snapshots: tuple[tuple[tuple[int, int], Piece | None, ChessCellState], ...]
    king_destination: tuple[int, int]
    rook_destination: tuple[int, int]

    @classmethod
    def apply(
        cls,
        board: Board,
        king_start: tuple[int, int],
        rook_start: tuple[int, int],
        king_destination: tuple[int, int],
        rook_destination: tuple[int, int],
    ) -> "DefensiveMoveTransaction":
        king = board.cell(*king_start).piece
        rook = board.cell(*rook_start).piece
        if king is None or rook is None:
            raise ValueError("Le roi et la tour doivent être présents")
        coordinates = tuple(dict.fromkeys(
            (king_start, rook_start, king_destination, rook_destination)
        ))
        snapshots = tuple(
            (coordinate, board.cell(*coordinate).piece, board.cell(*coordinate).chess_state)
            for coordinate in coordinates
        )
        for coordinate in (king_start, rook_start):
            board.cell(*coordinate).piece = None
            board.cell(*coordinate).chess_state = ChessCellState.EMPTY
        board.cell(*rook_destination).piece = rook
        board.cell(*rook_destination).chess_state = ChessCellState.OCCUPIED
        board.cell(*king_destination).piece = king
        board.cell(*king_destination).chess_state = ChessCellState.OCCUPIED
        return cls(
            PieceMove(king_start, king_destination, ()), snapshots,
            king_destination, rook_destination,
        )

    def rollback(self, board: Board) -> None:
        for coordinate, piece, state in self.snapshots:
            cell = board.cell(*coordinate)
            cell.piece = piece
            cell.chess_state = state


class MovementEngine:
    """Déplacements d'échecs projetés case par case sur le terrain 17×17."""

    @staticmethod
    def _owner_at(board: Board, file: int, rank: int) -> str | None:
        piece = board.cell(file * 2 + 1, rank * 2 + 1).piece
        return piece.owner if piece else None

    @staticmethod
    def _piece_at(board: Board, file: int, rank: int) -> Piece | None:
        return board.cell(file * 2 + 1, rank * 2 + 1).piece

    @staticmethod
    def _terrain_anchor(file: int, rank: int) -> tuple[int, int]:
        return file * 2 + 1, rank * 2 + 1

    @classmethod
    def legal_moves(cls, board: Board, x: int, y: int) -> tuple[PieceMove, ...]:
        """Coups qui laissent obligatoirement le roi du joueur hors échec."""
        cell = board.cell(x, y)
        if cell.piece is None:
            return ()
        owner = cell.piece.owner
        opponent = "NOIR" if owner == "BLANC" else "BLANC"
        legal: list[PieceMove] = []
        for move in cls._pseudo_legal_moves(board, x, y):
            if move.captured_piece and move.captured_piece.identifier.endswith("-king"):
                continue
            transaction = MoveTransaction.apply(board, move)
            king = cls.king_position(board, owner)
            safe = king is None or not cls.is_square_attacked(board, king, opponent)
            transaction.rollback(board)
            if safe:
                legal.append(move)
        return tuple(legal)

    @classmethod
    def defensive_pair_geometry(
        cls,
        board: Board,
        first: tuple[int, int],
        second: tuple[int, int],
    ) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
        """Valide une sélection Alt roi-tour et retourne départs puis arrivées.

        La tour avance de deux cases d'échecs depuis son bord. Le roi se place
        contre elle, du côté de ce même bord.
        """
        first_piece = board.cell(*first).piece
        second_piece = board.cell(*second).piece
        if first_piece is None or second_piece is None:
            raise ValueError("Sélectionnez un roi et une tour")
        pieces = ((first, first_piece), (second, second_piece))
        kings = [item for item in pieces if item[1].identifier.endswith("-king")]
        rooks = [item for item in pieces if item[1].identifier.endswith("-rook")]
        if len(kings) != 1 or len(rooks) != 1:
            raise ValueError("La sélection défensive exige exactement un roi et une tour")
        king_start, king = kings[0]
        rook_start, rook = rooks[0]
        if king.owner != rook.owner:
            raise ValueError("Le roi et la tour doivent appartenir au même camp")
        if king_start[1] != rook_start[1]:
            raise ValueError("Le roi et la tour doivent être sur la même ligne")
        rook_file = (rook_start[0] - 1) // 2
        king_file = (king_start[0] - 1) // 2
        rank = (king_start[1] - 1) // 2
        if rook_file not in (0, 7):
            raise ValueError("La tour doit se trouver sur un bord latéral")
        if not min(rook_file, king_file) < max(rook_file, king_file):
            raise ValueError("Position roi-tour invalide")
        step = 1 if king_file > rook_file else -1
        for file in range(rook_file + step, king_file, step):
            if cls._piece_at(board, file, rank) is not None:
                raise ValueError("Une pièce bloque le déplacement défensif")
        rook_target_file = 2 if rook_file == 0 else 5
        king_target_file = 1 if rook_file == 0 else 6
        king_destination = cls._terrain_anchor(king_target_file, rank)
        rook_destination = cls._terrain_anchor(rook_target_file, rank)
        selected = {king_start, rook_start}
        for destination in (king_destination, rook_destination):
            if destination not in selected and board.cell(*destination).piece is not None:
                raise ValueError("La destination défensive est occupée")
        transaction = DefensiveMoveTransaction.apply(
            board, king_start, rook_start, king_destination, rook_destination
        )
        opponent = "NOIR" if king.owner == "BLANC" else "BLANC"
        safe = not cls.is_square_attacked(board, king_destination, opponent)
        transaction.rollback(board)
        if not safe:
            raise ValueError("Le roi resterait en échec après ce déplacement")
        return king_start, rook_start, king_destination, rook_destination

    @classmethod
    def _pseudo_legal_moves(cls, board: Board, x: int, y: int) -> tuple[PieceMove, ...]:
        cell = board.cell(x, y)
        if not cell.is_chess_cell or cell.piece is None:
            return ()
        piece = cell.piece
        file, rank = (x - 1) // 2, (y - 1) // 2
        kind = piece.identifier.split("-", 1)[1]
        targets: list[tuple[int, int]] = []

        if kind == "pawn":
            direction = -1 if piece.owner == "BLANC" else 1
            start_rank = 6 if piece.owner == "BLANC" else 1
            next_rank = rank + direction
            if 0 <= next_rank < 8 and cls._piece_at(board, file, next_rank) is None:
                targets.append((file, next_rank))
                two_rank = rank + 2 * direction
                if rank == start_rank and cls._piece_at(board, file, two_rank) is None:
                    targets.append((file, two_rank))
            for delta_file in (-1, 1):
                target_file = file + delta_file
                if 0 <= target_file < 8 and 0 <= next_rank < 8:
                    target = cls._piece_at(board, target_file, next_rank)
                    if target and target.owner != piece.owner:
                        targets.append((target_file, next_rank))
        elif kind == "knight":
            for df, dr in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)):
                target_file, target_rank = file + df, rank + dr
                if 0 <= target_file < 8 and 0 <= target_rank < 8:
                    owner = cls._owner_at(board, target_file, target_rank)
                    if owner != piece.owner:
                        targets.append((target_file, target_rank))
        else:
            directions = {
                "rook": ((1, 0), (-1, 0), (0, 1), (0, -1)),
                "bishop": ((1, 1), (1, -1), (-1, 1), (-1, -1)),
                "queen": ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)),
                "king": ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)),
            }[kind]
            maximum = 1 if kind == "king" else 7
            for df, dr in directions:
                for distance in range(1, maximum + 1):
                    target_file, target_rank = file + df * distance, rank + dr * distance
                    if not (0 <= target_file < 8 and 0 <= target_rank < 8):
                        break
                    owner = cls._owner_at(board, target_file, target_rank)
                    if owner == piece.owner:
                        break
                    targets.append((target_file, target_rank))
                    if owner is not None:
                        break

        moves = []
        start = (x, y)
        for target_file, target_rank in targets:
            destination = cls._terrain_anchor(target_file, target_rank)
            path = (
                cls._knight_path(board, start, destination)
                if kind == "knight"
                else cls._straight_path(start, destination)
            )
            moves.append(PieceMove(start, destination, path, board.cell(*destination).piece))
        return tuple(moves)

    @staticmethod
    def promote_if_needed(piece: Piece, destination: tuple[int, int]) -> Piece:
        """Promeut automatiquement un pion arrivé sur la ligne opposée."""
        if not piece.identifier.endswith("-pawn"):
            return piece
        promotion_y = 1 if piece.owner == "BLANC" else 15
        if destination[1] != promotion_y:
            return piece
        return replace(
            piece,
            identifier=f"{'white' if piece.owner == 'BLANC' else 'black'}-queen",
            symbol="Q" if piece.owner == "BLANC" else "q",
        )

    @staticmethod
    def failed_attack_destination(board: Board, move: PieceMove) -> tuple[int, int]:
        """Dernière case d'échiquier libre du parcours avant le défenseur."""
        for coordinate in reversed(move.path):
            cell = board.cell(*coordinate)
            if cell.is_chess_cell and cell.piece is None:
                return coordinate
        return move.start

    @classmethod
    def king_position(cls, board: Board, owner: str) -> tuple[int, int] | None:
        for row in board.rows():
            for cell in row:
                if (
                    cell.piece is not None
                    and cell.piece.owner == owner
                    and cell.piece.identifier.endswith("-king")
                ):
                    return cell.x, cell.y
        return None

    @classmethod
    def is_square_attacked(cls, board: Board, target: tuple[int, int], by_owner: str) -> bool:
        target_file, target_rank = (target[0] - 1) // 2, (target[1] - 1) // 2
        for rank in range(8):
            for file in range(8):
                piece = cls._piece_at(board, file, rank)
                if piece is None or piece.owner != by_owner:
                    continue
                kind = piece.identifier.split("-", 1)[1]
                df, dr = target_file - file, target_rank - rank
                if kind == "pawn":
                    direction = -1 if piece.owner == "BLANC" else 1
                    if dr == direction and abs(df) == 1:
                        return True
                elif kind == "knight" and (abs(df), abs(dr)) in ((1, 2), (2, 1)):
                    return True
                elif kind == "king" and max(abs(df), abs(dr)) == 1:
                    return True
                elif kind in ("rook", "bishop", "queen"):
                    straight = df == 0 or dr == 0
                    diagonal = abs(df) == abs(dr)
                    if not (
                        (kind == "rook" and straight)
                        or (kind == "bishop" and diagonal)
                        or (kind == "queen" and (straight or diagonal))
                    ):
                        continue
                    steps = max(abs(df), abs(dr))
                    step_file = 0 if df == 0 else (1 if df > 0 else -1)
                    step_rank = 0 if dr == 0 else (1 if dr > 0 else -1)
                    if all(
                        cls._piece_at(board, file + step_file * distance, rank + step_rank * distance) is None
                        for distance in range(1, steps)
                    ):
                        return True
        return False

    @classmethod
    def checked_kings(cls, board: Board) -> dict[str, tuple[int, int]]:
        checked = {}
        for owner, opponent in (("BLANC", "NOIR"), ("NOIR", "BLANC")):
            position = cls.king_position(board, owner)
            if position is not None and cls.is_square_attacked(board, position, opponent):
                checked[owner] = position
        return checked

    @classmethod
    def has_legal_move(cls, board: Board, owner: str) -> bool:
        return any(
            cls.legal_moves(board, cell.x, cell.y)
            for row in board.rows() for cell in row
            if cell.piece is not None and cell.piece.owner == owner
        )

    @classmethod
    def is_checkmate(cls, board: Board, owner: str) -> bool:
        return owner in cls.checked_kings(board) and not cls.has_legal_move(board, owner)

    @staticmethod
    def _straight_path(start: tuple[int, int], destination: tuple[int, int]) -> tuple[tuple[int, int], ...]:
        dx, dy = destination[0] - start[0], destination[1] - start[1]
        steps = gcd(abs(dx), abs(dy))
        step_x, step_y = dx // steps, dy // steps
        return tuple((start[0] + step_x * index, start[1] + step_y * index) for index in range(1, steps))

    @staticmethod
    def _knight_path(board: Board, start: tuple[int, int], destination: tuple[int, int]) -> tuple[tuple[int, int], ...]:
        blocked = {
            (cell.x, cell.y)
            for row in board.rows() for cell in row
            if cell.piece and (cell.x, cell.y) not in (start, destination)
        }
        queue = deque([(start, ())])
        visited = {start}
        while queue:
            current, path = queue.popleft()
            if current == destination:
                return path[:-1]
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                neighbor = current[0] + dx, current[1] + dy
                if (
                    0 <= neighbor[0] < Board.SIZE
                    and 0 <= neighbor[1] < Board.SIZE
                    and neighbor not in blocked
                    and neighbor not in visited
                ):
                    visited.add(neighbor)
                    queue.append((neighbor, path + (neighbor,)))
        return ()
