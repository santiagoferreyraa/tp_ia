"""Pruebas unitarias para validar las reglas del Truco, el cálculo de Envido y la extensibilidad del Framework."""

import sys
import unittest
from pathlib import Path

# Permite correrlo directo: python tests/test_truco.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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



class TestAgenteLeeElTanteador(unittest.TestCase):
    """El robot no regala la partida con un "no quiero"."""

    def _situacion(self, puntos_rival, objetivo=15):
        game = TrucoGame(target_score=objetivo)
        state = game.reset()
        state.players[game.p1_id].score = puntos_rival
        # Mano sin envido ni cartas: con estas, sin el tanteador, no querria nunca.
        state.players[game.p2_id].clear_hand()
        state.players[game.p2_id].receive_cards([
            Card(Suit.ORO, 4, get_truco_rank(Suit.ORO, 4)),
            Card(Suit.COPA, 5, get_truco_rank(Suit.COPA, 5)),
            Card(Suit.BASTO, 12, get_truco_rank(Suit.BASTO, 12)),
        ])
        return game, state

    def _responde(self, game, state, canto, veces=200):
        accion = next(a for a in game.get_valid_actions(state, game.p1_id) if a.name == canto)
        state, _, _ = game.step(state, accion)
        bot = HeuristicTrucoAgent(bluff_frequency=0.0)
        obs = game.get_player_observation(state, game.p2_id)
        acciones = game.get_valid_actions(state, game.p2_id)
        return {bot.select_action(obs, acciones).name for _ in range(veces)}

    def test_quiere_la_falta_si_no_querer_pierde_la_partida(self):
        game, state = self._situacion(14)
        self.assertEqual(self._responde(game, state, "Falta Envido"), {"Quiero"})

    def test_quiere_el_truco_si_no_querer_pierde_la_partida(self):
        game, state = self._situacion(14)
        respuestas = self._responde(game, state, "Truco")
        self.assertNotIn("No Quiero", respuestas)

    def test_con_margen_sigue_sin_querer_con_mano_mala(self):
        game, state = self._situacion(5)
        self.assertEqual(self._responde(game, state, "Falta Envido"), {"No Quiero"})


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


# ---------------------------------------------------------------------------
#  Reglas: envido y truco completos (1v1, sin flor)
# ---------------------------------------------------------------------------
def _carta(palo, valor):
    return Card(palo, valor, get_truco_rank(palo, valor))


class TestReglas(unittest.TestCase):
    """Cada test arma una situacion concreta y verifica la regla."""

    def setUp(self):
        self.game = TrucoGame(target_score=15)
        self.state = self.game.reset()
        self.p1, self.p2 = self.game.p1_id, self.game.p2_id
        # p1 es mano: 33 de envido y cartas bravas. p2: 21 de envido.
        self._manos(
            [_carta(Suit.ESPADA, 7), _carta(Suit.ESPADA, 6), _carta(Suit.BASTO, 1)],
            [_carta(Suit.COPA, 1), _carta(Suit.ORO, 12), _carta(Suit.COPA, 4)],
        )

    def _manos(self, m1, m2):
        for pid, mano in ((self.p1, m1), (self.p2, m2)):
            self.state.players[pid].clear_hand()
            self.state.players[pid].receive_cards(mano)

    def _hacer(self, pid, nombre):
        acciones = self.game.get_valid_actions(self.state, pid)
        accion = next((a for a in acciones if a.name == nombre), None)
        self.assertIsNotNone(accion, f"{nombre!r} no es valida para {pid}: {[a.name for a in acciones]}")
        self.state, _, _ = self.game.step(self.state, accion)

    def _nombres(self, pid):
        return [a.name for a in self.game.get_valid_actions(self.state, pid)]

    def _puntos(self):
        return self.state.players[self.p1].score, self.state.players[self.p2].score

    # ---------- envido ----------
    def test_envido_envido_no_querido_vale_2(self):
        self._hacer(self.p1, "Envido")
        self._hacer(self.p2, "Envido")
        self._hacer(self.p1, "No Quiero")
        self.assertEqual(self._puntos(), (0, 2))

    def test_envido_real_envido_no_querido_vale_2(self):
        self._hacer(self.p1, "Envido")
        self._hacer(self.p2, "Real Envido")
        self._hacer(self.p1, "No Quiero")
        self.assertEqual(self._puntos(), (0, 2))

    def test_envido_envido_real_no_querido_vale_4(self):
        self._hacer(self.p1, "Envido")
        self._hacer(self.p2, "Envido")
        self._hacer(self.p1, "Real Envido")
        self._hacer(self.p2, "No Quiero")
        self.assertEqual(self._puntos(), (4, 0))

    def test_no_hay_tercer_envido(self):
        self._hacer(self.p1, "Envido")
        self._hacer(self.p2, "Envido")
        self.assertNotIn("Envido", self._nombres(self.p1))
        self.assertIn("Real Envido", self._nombres(self.p1))

    def test_envido_querido_suma_la_cadena(self):
        self._hacer(self.p1, "Envido")
        self._hacer(self.p2, "Real Envido")
        self._hacer(self.p1, "Quiero")
        self.assertEqual(self._puntos(), (5, 0))

    def test_falta_envido_querida_da_lo_que_falta(self):
        self.state.players[self.p2].score = 10
        self._hacer(self.p1, "Falta Envido")
        self._hacer(self.p2, "Quiero")
        self.assertEqual(self._puntos(), (5, 10))

    def test_tras_el_envido_vuelve_el_turno_a_quien_estaba_jugando(self):
        # p1 abre, p2 sube: al resolverse le toca tirar a p1 (era su turno).
        self._hacer(self.p1, "Envido")
        self._hacer(self.p2, "Real Envido")
        self._hacer(self.p1, "Quiero")
        self.assertEqual(self.state.current_player_id, self.p1)

    def test_no_se_canta_envido_con_el_truco_ya_querido(self):
        self._hacer(self.p1, "Truco")
        self._hacer(self.p2, "Quiero")
        self.assertNotIn("Envido", self._nombres(self.p1))

    def test_el_envido_esta_primero(self):
        self._hacer(self.p1, "Truco")
        self.assertIn("Envido", self._nombres(self.p2))
        self._hacer(self.p2, "Envido")
        self._hacer(self.p1, "Quiero")
        self.assertEqual(self._puntos(), (2, 0))
        # Resuelto el envido, p2 todavia debe contestar el truco.
        self.assertEqual(self.state.current_player_id, self.p2)
        self.assertIn("Quiero", self._nombres(self.p2))
        self.assertNotIn("Envido", self._nombres(self.p2))

    # ---------- truco ----------
    def test_truco_no_querido_vale_1(self):
        self._hacer(self.p1, "Truco")
        self._hacer(self.p2, "No Quiero")
        self.assertEqual(self._puntos(), (1, 0))

    def test_retruco_no_querido_vale_2(self):
        self._hacer(self.p1, "Truco")
        self._hacer(self.p2, "Retruco")
        self._hacer(self.p1, "No Quiero")
        self.assertEqual(self._puntos(), (0, 2))

    def test_vale_cuatro_no_querido_vale_3(self):
        self._hacer(self.p1, "Truco")
        self._hacer(self.p2, "Retruco")
        self._hacer(self.p1, "Vale Cuatro")
        self._hacer(self.p2, "No Quiero")
        self.assertEqual(self._puntos(), (3, 0))

    def test_truco_querido_devuelve_el_turno_a_quien_jugaba(self):
        self._hacer(self.p1, "Truco")
        self._hacer(self.p2, "Retruco")
        self._hacer(self.p1, "Quiero")
        self.assertEqual(self.state.game_data["truco_value"], 3)
        self.assertEqual(self.state.current_player_id, self.p1)

    def test_solo_sube_quien_quiso(self):
        self._hacer(self.p1, "Truco")
        self._hacer(self.p2, "Quiero")
        self.assertNotIn("Retruco", self._nombres(self.p1))
        self._hacer(self.p1, "Jugar 1 de Basto")
        self.assertIn("Retruco", self._nombres(self.p2))

    def test_irse_al_mazo_con_truco_querido_da_2(self):
        self._hacer(self.p1, "Truco")
        self._hacer(self.p2, "Quiero")
        self._hacer(self.p1, "Me voy al mazo")
        self.assertEqual(self._puntos(), (0, 2))

    def test_falta_envido_en_malas_es_el_partido(self):
        self.game.target_score = 30
        self.state.players[self.p1].score = 4
        self.state.players[self.p2].score = 12
        self._hacer(self.p1, "Falta Envido")
        self._hacer(self.p2, "Quiero")
        self.assertEqual(self._puntos(), (30, 12))
        self.assertTrue(self.state.is_terminal)

    def test_falta_envido_en_buenas_da_lo_que_le_falta_al_que_va_ganando(self):
        self.game.target_score = 30
        self.state.players[self.p1].score = 10
        self.state.players[self.p2].score = 21
        self._hacer(self.p1, "Falta Envido")
        self._hacer(self.p2, "Quiero")
        self.assertEqual(self._puntos(), (19, 21))

    def test_falta_envido_no_querida_cobra_lo_anterior(self):
        self.game.target_score = 30
        self._hacer(self.p1, "Envido")
        self._hacer(self.p2, "Falta Envido")
        self._hacer(self.p1, "No Quiero")
        self.assertEqual(self._puntos(), (0, 2))

    # ---------- irse al mazo ----------
    def test_mazo_en_primera_sin_envido_da_2(self):
        self._hacer(self.p1, "Me voy al mazo")
        self.assertEqual(self._puntos(), (0, 2))

    def test_mazo_en_primera_con_el_envido_jugado_da_1(self):
        self._hacer(self.p1, "Envido")
        self._hacer(self.p2, "No Quiero")
        self._hacer(self.p1, "Me voy al mazo")
        self.assertEqual(self._puntos(), (1, 1))

    def test_mazo_despues_de_tirar_en_primera_tambien_cobra_el_envido(self):
        # p2 todavia podia cantar envido: el punto se cobra igual.
        self._hacer(self.p1, "Jugar 1 de Basto")
        self._hacer(self.p2, "Me voy al mazo")
        self.assertEqual(self._puntos(), (2, 0))

    def test_mazo_en_segunda_da_1(self):
        self._hacer(self.p1, "Jugar 1 de Basto")
        self._hacer(self.p2, "Jugar 4 de Copa")
        self._hacer(self.p1, "Me voy al mazo")
        self.assertEqual(self._puntos(), (0, 1))

    # ---------- bazas ----------
    def test_parda_arranca_quien_tiro_primero(self):
        # Mano p2 (no mano p1): parda en primera -> vuelve a tirar p2.
        self.state.game_data["mano_player_id"] = self.p2
        self.state.current_player_id = self.p2
        self._manos(
            [_carta(Suit.ORO, 3), _carta(Suit.ORO, 4), _carta(Suit.ORO, 5)],
            [_carta(Suit.COPA, 3), _carta(Suit.COPA, 4), _carta(Suit.COPA, 5)],
        )
        self._hacer(self.p2, "Jugar 3 de Copa")
        self._hacer(self.p1, "Jugar 3 de Oro")
        self.assertEqual(self.state.current_player_id, self.p2)

    def test_gana_la_mano_quien_gana_dos_bazas(self):
        self._hacer(self.p1, "Jugar 1 de Basto")
        self._hacer(self.p2, "Jugar 4 de Copa")
        self._hacer(self.p1, "Jugar 7 de Espada")
        self._hacer(self.p2, "Jugar 12 de Oro")
        self.assertEqual(self._puntos(), (1, 0))


if __name__ == "__main__":
    unittest.main()
