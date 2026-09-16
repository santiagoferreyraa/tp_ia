"""Pruebas unitarias para validar las reglas del Truco, el cálculo de Envido y la extensibilidad del Framework."""

import unittest
from card_framework.core.card import Card, Suit
from card_framework.games.truco.truco_deck import get_truco_rank, calculate_envido_points, create_spanish_40_deck
from card_framework.games.truco.truco_game import TrucoGame
from card_framework.agents.heuristic_truco_agent import HeuristicTrucoAgent
from card_framework.agents.random_agent import RandomAgent
from card_framework.games.base_game import AbstractGame
from card_framework.core.game_state import GameState
from card_framework.core.action import Action, ActionType


class TestTrucoDeck(unittest.TestCase):
    """Pruebas para la jerarquía de cartas y el cálculo de Envido."""

    def test_truco_rankings(self):
        self.assertEqual(get_truco_rank(Suit.ESPADA, 1), 14)  # Ancho de espada
        self.assertEqual(get_truco_rank(Suit.BASTO, 1), 13)   # Ancho de basto
        self.assertEqual(get_truco_rank(Suit.ESPADA, 7), 12)   # 7 de espada
        self.assertEqual(get_truco_rank(Suit.ORO, 7), 11)      # 7 de oro
        self.assertEqual(get_truco_rank(Suit.COPA, 3), 10)     # 3
        self.assertEqual(get_truco_rank(Suit.ORO, 4), 1)       # 4 de oro

    def test_envido_calculation(self):
        # Caso 1: Mismo palo (7 de espada y 6 de espada) -> 20 + 7 + 6 = 33
        hand1 = [
            Card(Suit.ESPADA, 7, 12),
            Card(Suit.ESPADA, 6, 3),
            Card(Suit.ORO, 1, 8)
        ]
        self.assertEqual(calculate_envido_points(hand1), 33)

        # Caso 2: Con figura (12 de oro y 7 de oro) -> 20 + 0 + 7 = 27
        hand2 = [
            Card(Suit.ORO, 12, 7),
            Card(Suit.ORO, 7, 11),
            Card(Suit.COPA, 4, 1)
        ]
        self.assertEqual(calculate_envido_points(hand2), 27)

        # Caso 3: Tres palos distintos -> máximo valor individual
        hand3 = [
            Card(Suit.ESPADA, 5, 2),
            Card(Suit.ORO, 6, 3),
            Card(Suit.COPA, 12, 7)
        ]
        self.assertEqual(calculate_envido_points(hand3), 6)


class TestTrucoSimulation(unittest.TestCase):
    """Prueba de simulación completa de partidas de Truco entre Agentes IA."""

    def test_ai_vs_ai_game(self):
        game = TrucoGame(target_score=15)
        bot1 = HeuristicTrucoAgent("BotPro")
        bot2 = RandomAgent("BotRandom")

        state = game.reset()
        step_count = 0
        max_steps = 500  # Evitar bucles infinitos

        while not state.is_terminal and step_count < max_steps:
            curr_id = state.current_player_id
            actions = game.get_valid_actions(state, curr_id)
            self.assertTrue(len(actions) > 0, "Debe haber al menos una acción válida")

            if curr_id == game.p1_id:
                obs = game.get_player_observation(state, game.p1_id)
                action = bot1.select_action(obs, actions)
            else:
                obs = game.get_player_observation(state, game.p2_id)
                action = bot2.select_action(obs, actions)

            state, reward, is_term = game.step(state, action)
            step_count += 1

        self.assertTrue(state.is_terminal, "El juego debe finalizar normalmente")
        self.assertIsNotNone(state.winner_id, "Debe haber un ganador al finalizar")


class MinimalBlackjackGame(AbstractGame):
    """Prototipo de segundo juego de cartas para demostrar la extensibilidad del Framework."""

    def reset(self) -> GameState:
        players = {"p1": None, "p2": None}  # Stub
        return GameState("p1", players)

    def get_valid_actions(self, state: GameState, player_id: str):
        return [Action(ActionType.PLAY_CARD, player_id, "Pedir Carta")]

    def step(self, state: GameState, action: Action):
        state.is_terminal = True
        return state, 1.0, True

    def is_terminal(self, state: GameState) -> bool:
        return state.is_terminal

    def get_player_observation(self, state: GameState, player_id: str) -> GameState:
        return state


class TestExtensibility(unittest.TestCase):
    """Verifica que el Framework permita extender a otros juegos consumiendo la misma interfaz."""

    def test_framework_extensibility(self):
        bj_game = MinimalBlackjackGame()
        state = bj_game.reset()
        actions = bj_game.get_valid_actions(state, "p1")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].name, "Pedir Carta")


if __name__ == "__main__":
    unittest.main()
