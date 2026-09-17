"""Ventana del Truco: arranca pygame y alterna entre el menu y la partida."""

import os
import time

import pygame

from card_framework import rutas
from card_framework.core.card import Card, Suit
from card_framework.interfaces.mesa.escena_menu import EscenaMenu
from card_framework.interfaces.mesa.escena_partida import EscenaPartida
from card_framework.interfaces.mesa.recursos import ALTO, ANCHO, Recursos
from card_framework.interfaces.mesa.robot_sim import RobotSimulado
from card_framework.interfaces.mesa.voz import Voz


class App:
    def __init__(self, conectar_robot: bool = True):
        pygame.init()
        pygame.display.set_caption("Truco · Unitree G1")
        # SCALED: se dibuja siempre en 1280x720 y pygame escala a la ventana.
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.SCALED | pygame.RESIZABLE)
        self.reloj = pygame.time.Clock()
        self.recursos = Recursos()
        pygame.display.set_icon(self.recursos.carta(Card(Suit.ESPADA, 1), 0.2))

        if not rutas.CARTAS:
            print("[Truco] No encuentro la carpeta truco/cartas: se dibujan cartas sin imagen.")

        self.voz = Voz()
        self.robot_sim = RobotSimulado()
        if conectar_robot:
            self.robot_sim.conectar_en_segundo_plano()

        self.ultimo_objetivo = 15
        self.escena = EscenaMenu(self)
        self._corriendo = True
        self._inicio = time.perf_counter()

    # ---------- navegacion ----------
    def nueva_partida(self, objetivo: int) -> None:
        self.ultimo_objetivo = objetivo
        self.escena = EscenaPartida(self, objetivo)
        self.escena.actualizar(self.ahora())

    def ir_al_menu(self) -> None:
        self.voz.callar()
        self.escena = EscenaMenu(self)

    def salir(self) -> None:
        self._corriendo = False

    def ahora(self) -> float:
        return time.perf_counter() - self._inicio

    # ---------- bucle ----------
    def correr(self) -> None:
        try:
            while self._corriendo:
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        self._corriendo = False
                    else:
                        self.escena.evento(e)
                ahora = self.ahora()
                self.escena.actualizar(ahora)
                self.escena.dibujar(self.pantalla, ahora)
                pygame.display.flip()
                self.reloj.tick(60)
        finally:
            self.voz.callar()
            self.robot_sim.desconectar()
            pygame.quit()


def main() -> None:
    App(conectar_robot=os.environ.get("TRUCO_SIN_ROBOT") != "1").correr()


if __name__ == "__main__":
    main()
