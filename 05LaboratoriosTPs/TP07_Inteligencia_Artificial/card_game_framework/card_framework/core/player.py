"""Representación de Jugadores (Humanos o IA) en el Framework."""

from typing import List
from card_framework.core.card import Card


class Player:
    """Clase para representar a un jugador en cualquier juego de cartas."""

    def __init__(self, player_id: str, name: str, is_ai: bool = False):
        self.player_id = player_id
        self.name = name
        self.is_ai = is_ai
        self.hand: List[Card] = []
        self.score: int = 0

    def receive_cards(self, cards: List[Card]) -> None:
        """Agrega cartas a la mano del jugador."""
        self.hand.extend(cards)

    def play_card(self, card: Card) -> Card:
        """Remueve y devuelve la carta jugada de la mano."""
        if card in self.hand:
            self.hand.remove(card)
            return card
        raise ValueError(f"La carta {card} no está en la mano de {self.name}")

    def clear_hand(self) -> None:
        """Limpia las cartas en mano."""
        self.hand.clear()

    def __repr__(self) -> str:
        return f"Player(id='{self.player_id}', name='{self.name}', score={self.score}, hand_size={len(self.hand)})"
