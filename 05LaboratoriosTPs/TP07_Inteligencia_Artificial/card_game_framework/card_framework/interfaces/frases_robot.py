"""Lo que dice el robot en cada jugada. Lo usan la mesa virtual y la partida real."""

import random
from typing import Optional

from card_framework.core.action import Action, ActionType
from card_framework.games.truco.truco_verses import get_random_verse

# Probabilidad de que el robot cante con un verso en vez de decirlo derecho.
PROB_VERSO = 0.25

NOMBRE_CANTO = {
    "ENVIDO": "Envido", "REAL_ENVIDO": "Real envido", "FALTA_ENVIDO": "Falta envido",
    "TRUCO": "Truco", "RETRUCO": "Retruco", "VALE_CUATRO": "Vale cuatro",
}

# Como canta el robot cuando no recita.
CANTO_ROBOT = {
    "ENVIDO": "Envido.", "REAL_ENVIDO": "¡Real envido!", "FALTA_ENVIDO": "¡Falta envido!",
    "TRUCO": "¡Truco!", "RETRUCO": "¡Quiero retruco!", "VALE_CUATRO": "¡Quiero vale cuatro!",
}


def nombre_carta(carta) -> str:
    """'el ancho de espada', 'el 7 de oro', 'el 3 de copa'."""
    if carta.value == 1 and carta.suit.value in ("Espada", "Basto"):
        return f"el ancho de {carta.suit.value.lower()}"
    return f"el {carta.value} de {carta.suit.value.lower()}"


def frase(accion: Action, anunciar_carta: bool = False) -> Optional[str]:
    """Texto que dice el robot al hacer `accion`, o None si no dice nada.

    anunciar_carta: en la partida real el robot dice que carta tira, porque
    la tira otra persona.
    """
    bid = accion.payload.get("bid")
    respuesta = accion.payload.get("response")
    if bid:
        if random.random() < PROB_VERSO:
            return get_random_verse(bid)
        return CANTO_ROBOT[bid]
    if respuesta:
        return "¡Quiero!" if respuesta.startswith("QUIERO") else "No quiero."
    if accion.action_type == ActionType.FOLD:
        return "Me voy al mazo."
    if accion.action_type == ActionType.PLAY_CARD and anunciar_carta:
        return f"Tiro {nombre_carta(accion.payload['card'])}."
    return None
