"""Modelo base para Naipes (Cartas) en cualquier juego de baraja."""

from enum import Enum
from typing import Any, Optional


class Suit(Enum):
    """Palos estándar para barajas Española y Francesa."""

    # Baraja Española
    ESPADA = "Espada"
    BASTO = "Basto"
    ORO = "Oro"
    COPA = "Copa"

    # Baraja Francesa / Pocker
    CORAZON = "Corazón"
    DIAMANTE = "Diamante"
    TREBOL = "Trébol"
    PICA = "Pica"


class Card:
    """Representa una carta individual en cualquier juego de cartas.

    Atributos:
        suit: Palo de la carta (Suit enum o string).
        value: Valor numérico o cara (1..12, 'A', 'K', etc.).
        rank: Jerarquía numérica utilizada para comparar poder relativo en juegos específicos.
    """

    def __init__(self, suit: Suit, value: int, rank: int = 0, name: Optional[str] = None):
        self.suit = suit
        self.value = value
        self.rank = rank
        self.name = name or f"{value} de {suit.value}"

    def __repr__(self) -> str:
        return f"Card({self.name}, rank={self.rank})"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.value == other.value

    def __hash__(self) -> int:
        return hash((self.suit, self.value))
