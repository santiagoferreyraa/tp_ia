"""Mazo Español de 40 cartas y reglas de puntuación del Truco Argentino (Jerarquía y Envido)."""

from typing import List, Dict
from card_framework.core.card import Card, Suit
from card_framework.core.deck import Deck


def get_truco_rank(suit: Suit, value: int) -> int:
    """Devuelve la jerarquía (poder) de la carta en el Truco Argentino.

    Rango de 1 (más débil) a 14 (más fuerte).
    """
    if value == 1 and suit == Suit.ESPADA:
        return 14  # Ancho de Espada
    if value == 1 and suit == Suit.BASTO:
        return 13  # Ancho de Basto
    if value == 7 and suit == Suit.ESPADA:
        return 12  # 7 de Espada
    if value == 7 and suit == Suit.ORO:
        return 11  # 7 de Oro
    if value == 3:
        return 10
    if value == 2:
        return 9
    if value == 1:
        return 8  # 1 de Oro o 1 de Copa (Falsos)
    if value == 12:
        return 7
    if value == 11:
        return 6
    if value == 10:
        return 5
    if value == 7:
        return 4  # 7 de Basto o 7 de Copa (Falsos)
    if value == 6:
        return 3
    if value == 5:
        return 2
    if value == 4:
        return 1
    return 0


def create_spanish_40_deck() -> Deck:
    """Crea un mazo de 40 cartas españolas (sin 8s ni 9s) asignando jerarquía de Truco."""
    cards = []
    suits = [Suit.ESPADA, Suit.BASTO, Suit.ORO, Suit.COPA]
    valid_values = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]

    for suit in suits:
        for val in valid_values:
            rank = get_truco_rank(suit, val)
            cards.append(Card(suit=suit, value=val, rank=rank))
    return Deck(cards)


def calculate_envido_points(hand: List[Card]) -> int:
    """Calcula los puntos de Envido para una mano dada (hasta 3 cartas).

    Fórmula:
    - 2 cartas del mismo palo: 20 + val1 + val2 (donde 10, 11, 12 valen 0).
    - Cartas de distinto palo: el valor máximo individual (donde 10, 11, 12 valen 0).
    """
    if not hand:
        return 0

    def card_envido_val(card: Card) -> int:
        return card.value if card.value <= 7 else 0

    by_suit: Dict[Suit, List[Card]] = {}
    for c in hand:
        by_suit.setdefault(c.suit, []).append(c)

    max_points = 0
    same_suit_found = False

    for suit, cards in by_suit.items():
        if len(cards) >= 2:
            same_suit_found = True
            # Tomar los 2 valores más altos del mismo palo
            vals = sorted([card_envido_val(c) for c in cards], reverse=True)
            points = 20 + vals[0] + vals[1]
            if points > max_points:
                max_points = points

    if not same_suit_found:
        max_points = max(card_envido_val(c) for c in hand)

    return max_points
