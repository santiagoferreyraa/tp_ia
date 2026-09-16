"""Interfaz Abstracta que define el contrato de cualquier juego de cartas en el Framework."""

from abc import ABC, abstractmethod
from typing import List, Tuple
from card_framework.core.action import Action
from card_framework.core.game_state import GameState


class AbstractGame(ABC):
    """Clase base abstracta para cualquier juego de cartas (Truco, Poker, Uno, etc.)."""

    @abstractmethod
    def reset(self) -> GameState:
        """Inicializa el mazo, reparte cartas y devuelve el estado inicial del juego."""
        pass

    @abstractmethod
    def get_valid_actions(self, state: GameState, player_id: str) -> List[Action]:
        """Devuelve la lista de acciones válidas para el jugador en el estado actual."""
        pass

    @abstractmethod
    def step(self, state: GameState, action: Action) -> Tuple[GameState, float, bool]:
        """Aplica una acción al estado de juego actual.

        Devuelve:
            (nuevo_estado, recompensa, es_terminal)
        """
        pass

    @abstractmethod
    def is_terminal(self, state: GameState) -> bool:
        """Devuelve True si el partido o la mano ha finalizado."""
        pass

    @abstractmethod
    def get_player_observation(self, state: GameState, player_id: str) -> GameState:
        """Devuelve la observación privada del estado para el jugador especificado."""
        pass
