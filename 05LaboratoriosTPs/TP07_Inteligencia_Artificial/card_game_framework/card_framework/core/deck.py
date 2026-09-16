"""Modelo base de Mazo de Cartas con funciones de mezclado y reparto."""

import random
from typing import List, Optional
from card_framework.core.card import Card


class Deck:
    """Clase genérica para gestionar un mazo de cartas."""

    def __init__(self, cards: Optional[List[Card]] = None):
        self.cards: List[Card] = cards[:] if cards else []
        self._initial_cards: List[Card] = cards[:] if cards else []

    def shuffle(self) -> None:
        """Mezcla aleatoriamente las cartas presentes en el mazo."""
        random.shuffle(self.cards)

    def draw(self) -> Optional[Card]:
        """Roba una carta de la cima del mazo."""
        if not self.cards:
            return None
        return self.cards.pop()

    def deal(self, num_cards: int) -> List[Card]:
        """Reparte una cantidad determinada de cartas."""
        dealt = []
        for _ in range(num_cards):
            card = self.draw()
            if card:
                dealt.append(card)
        return dealt

    def reset(self) -> None:
        """Restablece el mazo a su estado inicial y lo vuelve a guardar."""
        self.cards = self._initial_cards[:]

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        return f"Deck({len(self.cards)} cartas)"
