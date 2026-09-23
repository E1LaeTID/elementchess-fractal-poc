from __future__ import annotations

from dataclasses import dataclass

from .balance import BalanceConfig, ElementSignatureField
from .board import Board


@dataclass(frozen=True, slots=True)
class TimedPowerEffect:
    piece_id: str
    attack_delta: int
    defense_delta: int
    starts_at_round: int
    expires_after_round: int


class PowerEffectLedger:
    """Effets n+1 synchrones : aucun bonus ne s'accumule sans échéance."""

    def __init__(self, config: BalanceConfig | None = None) -> None:
        self.config = config or BalanceConfig()
        self.effects: list[TimedPowerEffect] = []

    def schedule_from_adjacency(
        self,
        board: Board,
        piece_position: tuple[int, int],
        signatures: ElementSignatureField,
        current_round: int,
        duration: int = 1,
    ) -> TimedPowerEffect:
        piece = board.cell(*piece_position).piece
        if piece is None:
            raise ValueError("Aucune pièce à la position indiquée")
        deltas = []
        for cell in board.neighbors8(*piece_position):
            signature = signatures.signature(cell.terrain)
            value = signature.mode.value * signature.level.value * self.config.relation_step
            if value:
                deltas.append(value)
        average = 0 if not deltas else round(sum(deltas) / len(deltas))
        zone = board.cell(*piece_position).zone_id
        inside = sum(
            1 for cell in board.neighbors8(*piece_position)
            if cell.zone_id == zone and signatures.signature(cell.terrain).mode.value
        )
        outside = len(deltas) - inside
        effect = TimedPowerEffect(
            piece_id=piece.identifier,
            defense_delta=average if inside >= outside else 0,
            attack_delta=average if outside > inside else 0,
            starts_at_round=current_round + 1,
            expires_after_round=current_round + max(1, duration),
        )
        self.effects = [item for item in self.effects if item.piece_id != piece.identifier]
        self.effects.append(effect)
        return effect

    def modifiers(self, piece_id: str, round_number: int) -> tuple[int, int]:
        relevant = [
            effect for effect in self.effects
            if effect.piece_id == piece_id
            and effect.starts_at_round <= round_number <= effect.expires_after_round
        ]
        return (
            sum(effect.attack_delta for effect in relevant),
            sum(effect.defense_delta for effect in relevant),
        )

    def expire(self, completed_round: int) -> None:
        self.effects = [
            effect for effect in self.effects
            if effect.expires_after_round > completed_round
        ]
