"""Interfaz base abstracta para cualquier agente de Inteligencia Artificial en el Framework."""

from abc import ABC, abstractmethod
from typing import List
from card_framework.core.action import Action
from card_framework.core.game_state import GameState


class AbstractAgent(ABC):
    """Clase base para todos los agentes de Inteligencia Artificial."""

    def __init__(self, name: str = "AIAgent"):
        self.name = name

    @abstractmethod
    def select_action(self, observation: GameState, valid_actions: List[Action]) -> Action:
        """Selecciona una acción válida dada la observación privada del estado del juego."""
        pass
