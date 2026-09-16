"""Agente Baseline que selecciona acciones aleatorias válidas."""

import random
from typing import List
from card_framework.agents.base_agent import AbstractAgent
from card_framework.core.action import Action
from card_framework.core.game_state import GameState


class RandomAgent(AbstractAgent):
    """Agente simple de referencia para pruebas y benchmarking."""

    def __init__(self, name: str = "RandomBot"):
        super().__init__(name=name)

    def select_action(self, observation: GameState, valid_actions: List[Action]) -> Action:
        if not valid_actions:
            raise ValueError("No hay acciones válidas para seleccionar.")
        return random.choice(valid_actions)
