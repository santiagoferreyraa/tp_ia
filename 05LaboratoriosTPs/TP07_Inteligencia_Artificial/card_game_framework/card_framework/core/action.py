"""Modelo de Acciones posibles en cualquier juego de cartas."""

from enum import Enum, auto
from typing import Any, Dict, Optional


class ActionType(Enum):
    """Tipos genéricos de acciones en juegos de cartas."""
    PLAY_CARD = auto()
    BID = auto()          # Envite (Envido, Truco, Bet, Raise)
    RESPONSE = auto()     # Respuesta (Quiero, No Quiero, Fold, Call)
    PASS = auto()         # Pasar turno
    FOLD = auto()         # Irse al mazo
    DECLARE = auto()      # Declarar un valor que el sistema no puede ver (ej. puntos de envido)


class Action:
    """Representa una acción ejecutada por un jugador en su turno."""

    def __init__(self, action_type: ActionType, player_id: str, name: str, payload: Optional[Dict[str, Any]] = None):
        self.action_type = action_type
        self.player_id = player_id
        self.name = name
        self.payload = payload or {}

    def __repr__(self) -> str:
        return f"Action(player='{self.player_id}', type={self.action_type.name}, name='{self.name}', payload={self.payload})"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Action):
            return False
        return (self.action_type == other.action_type and
                self.player_id == other.player_id and
                self.name == other.name and
                self.payload == other.payload)
