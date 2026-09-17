"""El interprete de lo que dice el rival: clasificador, extractor y validador."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from card_framework.core.card import Card, Suit
from card_framework.games.truco.truco_deck import get_truco_rank
from card_framework.interfaces.interprete_truco import ClasificadorTruco, InterpreteTruco
from card_framework.interfaces.partida_real import PartidaReal


def carta(palo, valor):
    return Card(palo, valor, get_truco_rank(palo, valor))


class TestClasificador(unittest.TestCase):
    CASOS = [
        ("Envido", "ENVIDO"), ("real envido", "REAL_ENVIDO"), ("FALTA ENVIDO!", "FALTA_ENVIDO"),
        ("truco", "TRUCO"), ("quiero retruco", "RETRUCO"), ("quiero vale cuatro", "VALE_CUATRO"),
        ("quiero", "QUIERO"), ("no quiero", "NO_QUIERO"), ("me voy al mazo", "MAZO"),
        ("tiro el ancho de espada", "TIRAR_CARTA"), ("el 7 de oros", "TIRAR_CARTA"),
        ("tengo 27", "DECLARAR_ENVIDO"), ("tengo veintisiete", "DECLARAR_ENVIDO"),
        ("son buenas", "DECLARAR_ENVIDO"), ("hola que tal", "DESCONOCIDO"),
    ]

    def test_casos(self):
        c = ClasificadorTruco()
        for texto, esperado in self.CASOS:
            with self.subTest(texto=texto):
                self.assertEqual(c.clasificar(texto), esperado)


class TestInterpreteEnPartida(unittest.TestCase):
    def setUp(self):
        self.p = PartidaReal(objetivo=15, farol=0.0)
        self.p.cargar_cartas_robot([carta(Suit.ESPADA, 7), carta(Suit.ESPADA, 6), carta(Suit.BASTO, 1)])
        self.i = InterpreteTruco()

    def _interpretar(self, texto):
        return self.i.interpretar(texto, self.p.acciones_rival())

    def test_tirar_carta_con_palabras(self):
        r = self._interpretar("tiro el ancho de espada")
        self.assertTrue(r.aceptada)
        self.assertEqual(r.accion.payload["card"], Card(Suit.ESPADA, 1))

    def test_rechaza_carta_que_tiene_el_robot(self):
        r = self._interpretar("el siete de espada")
        self.assertFalse(r.aceptada)
        self.assertIn("ya se vio", r.mensaje)

    def test_rechaza_ocho_y_nueve(self):
        self.assertIn("8 ni 9", self._interpretar("tiro el 8 de copa").mensaje)

    def test_validador_rechaza_quiero_sin_canto(self):
        r = self._interpretar("quiero")
        self.assertFalse(r.aceptada)
        self.assertIn("Ahora no se puede", r.mensaje)

    def test_canto_valido(self):
        r = self._interpretar("envido")
        self.assertTrue(r.aceptada)
        self.assertEqual(r.accion.payload["bid"], "ENVIDO")

    def test_declarar_tantos(self):
        self.p.aplicar(self._interpretar("envido").accion)
        while self.p.turno_robot():
            accion = self.p.jugar_robot().accion
            if self.p.turno_rival() and not self.p.esperando_declaracion():
                self.p.aplicar(self._interpretar("quiero").accion)
        self.assertTrue(self.p.esperando_declaracion())
        self.assertEqual(self._interpretar("tengo treinta y uno").accion.payload["envido"], 31)
        self.assertEqual(self._interpretar("tengo 27").accion.payload["envido"], 27)
        self.assertFalse(self._interpretar("tengo 15").aceptada)
        self.assertEqual(self._interpretar("son buenas").accion.payload["envido"], 0)


if __name__ == "__main__":
    unittest.main()
