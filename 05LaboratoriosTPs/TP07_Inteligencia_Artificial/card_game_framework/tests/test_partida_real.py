"""Partida con cartas reales: el sistema no ve la mano del rival."""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from card_framework.core.action import Action, ActionType
from card_framework.core.card import Card, Suit
from card_framework.games.truco.truco_deck import calculate_envido_points, create_spanish_40_deck, get_truco_rank
from card_framework.interfaces.partida_real import PartidaReal


def carta(palo, valor):
    return Card(palo, valor, get_truco_rank(palo, valor))


def accion(partida, nombre):
    return next(a for a in partida.acciones_rival() if a.name == nombre)


class TestPartidaReal(unittest.TestCase):
    def setUp(self):
        random.seed(3)
        self.p = PartidaReal(objetivo=15, farol=0.0)
        self.robot_cartas = [carta(Suit.ESPADA, 7), carta(Suit.ESPADA, 6), carta(Suit.BASTO, 1)]

    def test_no_arranca_sin_las_cartas_del_robot(self):
        self.assertTrue(self.p.necesita_cartas())
        self.assertEqual(self.p.acciones_rival(), [])

    def test_el_rival_puede_tirar_cualquier_carta_no_vista(self):
        self.p.cargar_cartas_robot(self.robot_cartas)
        jugables = [a.payload["card"] for a in self.p.acciones_rival() if a.action_type == ActionType.PLAY_CARD]
        self.assertEqual(len(jugables), 37)
        for c in self.robot_cartas:
            self.assertNotIn(c, jugables)

    def test_la_carta_del_operador_toma_la_jerarquia_del_motor(self):
        self.p.cargar_cartas_robot(self.robot_cartas)
        # El operador arma la carta sin jerarquia (rank 0): igual tiene que ganar.
        tirada = Action(ActionType.PLAY_CARD, self.p.rival, "Jugar 1 de Espada", {"card": Card(Suit.ESPADA, 1)})
        self.p.aplicar(tirada)
        self.assertEqual(self.p.bazas()[0]["rival"].rank, 14)

    def test_no_se_puede_tirar_una_carta_del_robot(self):
        self.p.cargar_cartas_robot(self.robot_cartas)
        tirada = Action(ActionType.PLAY_CARD, self.p.rival, "Jugar 7 de Espada", {"card": Card(Suit.ESPADA, 7)})
        with self.assertRaises(ValueError):
            self.p.aplicar(tirada)

    def test_envido_querido_pide_declarar_y_resuelve(self):
        self.p.cargar_cartas_robot(self.robot_cartas)   # robot: 33 de envido
        self.p.aplicar(accion(self.p, "Envido"))
        r = self.p.jugar_robot()
        if r.accion.name != "Quiero":          # con 33 puede subir: el rival quiere
            self.p.aplicar(accion(self.p, "Quiero"))
        self.assertTrue(self.p.esperando_declaracion())
        r = self.p.aplicar(accion(self.p, "Tengo 28"))
        self.assertEqual(r.envido["winner_id"], self.p.robot)
        self.assertGreater(self.p.puntos()[self.p.robot], 0)
        self.assertIn("Tengo 33", r.dice or "")

    def test_el_robot_anuncia_la_carta_que_tira(self):
        self.p.cargar_cartas_robot(self.robot_cartas)
        self.p.aplicar(accion(self.p, "Jugar 4 de Copa"))
        r = self.p.jugar_robot()
        if r.accion.action_type == ActionType.PLAY_CARD:
            self.assertTrue(r.dice.startswith("Tiro "))

    def test_detecta_envido_mentido(self):
        self.p.cargar_cartas_robot([carta(Suit.ORO, 4), carta(Suit.COPA, 5), carta(Suit.BASTO, 6)])
        self.p.aplicar(accion(self.p, "Envido"))
        # Robot con 6: con farol 0 y margen en el tanteador no quiere. Forzamos el quiero.
        quiero = next(a for a in self.p.game.get_valid_actions(self.p.state, self.p.robot) if a.name == "Quiero")
        self.p._paso(quiero, de_robot=True)
        self.p.aplicar(accion(self.p, "Tengo 30"))
        # El rival muestra 3 cartas que suman 7, no 30.
        r = None
        for c in (carta(Suit.ORO, 7), carta(Suit.COPA, 2), carta(Suit.ESPADA, 3)):
            while self.p.turno_robot():
                r = self.p.jugar_robot()
            if r and r.mano_terminada:
                break
            r = self.p.aplicar(accion(self.p, f"Jugar {c.name}"))
            if r.mano_terminada:
                break
        while not (r and r.mano_terminada) and self.p.turno_robot():
            r = self.p.jugar_robot()
        if r.mano_terminada and len(r.verificacion_envido or "") and "suman" in r.verificacion_envido:
            self.assertIn("30", r.verificacion_envido)
        else:
            self.assertIsNotNone(r.verificacion_envido)


class TestPartidasRealesCompletas(unittest.TestCase):
    """Cientos de partidas con un rival que tiene cartas de verdad (que el sistema no ve)."""

    def test_partidas_completas(self):
        random.seed(11)
        for n in range(300):
            p = PartidaReal(objetivo=15 if n % 2 else 30, farol=0.5, robot_es_mano=n % 3 == 0)
            pasos = 0
            mano_rival = []
            while not p.terminada:
                pasos += 1
                self.assertLess(pasos, 3000)
                if p.necesita_cartas():
                    mazo = create_spanish_40_deck().cards
                    random.shuffle(mazo)
                    p.cargar_cartas_robot(mazo[:3])
                    mano_rival = mazo[3:6]
                    mano_original = list(mano_rival)
                    continue
                if p.turno_robot():
                    p.jugar_robot()
                    continue
                acciones = p.acciones_rival()
                if p.esperando_declaracion():
                    verdad = calculate_envido_points(mano_original)
                    elegida = next(a for a in acciones if a.payload["envido"] == verdad)
                else:
                    posibles = [a for a in acciones if a.action_type != ActionType.PLAY_CARD
                                or a.payload["card"] in mano_rival]
                    elegida = random.choice(posibles)
                if elegida.action_type == ActionType.PLAY_CARD:
                    mano_rival.remove(elegida.payload["card"])
                r = p.aplicar(elegida)
                if r.mano_terminada:
                    # Con envido declarado honestamente nunca hay aviso de mentira.
                    self.assertFalse(r.verificacion_envido and "suman" in r.verificacion_envido)
            self.assertIsNotNone(p.state.winner_id)


if __name__ == "__main__":
    unittest.main()
