"""Conexion opcional con el simulador 3D de Unitree (MuJoCo).

Si el simulador del TP07 esta abierto, el G1 gesticula cuando canta. Si no,
la mesa se juega igual: la conexion nunca bloquea ni rompe la partida.
"""

import sys
import threading

from card_framework import rutas


class RobotSimulado:
    def __init__(self):
        self.robot = None
        self.conectado = False
        self._ocupado = threading.Lock()

    def conectar_en_segundo_plano(self) -> None:
        threading.Thread(target=self._conectar, daemon=True).start()

    def _conectar(self) -> None:
        try:
            if str(rutas.MI_DESARROLLO) not in sys.path:
                sys.path.insert(0, str(rutas.MI_DESARROLLO))
            from robot import Robot  # noqa: WPS433 - import perezoso a proposito

            robot = Robot()
            robot.conectar()
            self.robot, self.conectado = robot, True
            print("[Truco] Conectado al simulador del G1.")
        except Exception:
            self.robot, self.conectado = None, False
            print("[Truco] Sin simulador 3D: se juega solo en la mesa.")

    def gesto(self, tipo: str) -> None:
        """tipo: 'canto' (saluda) o 'mazo' (se da vuelta).

        Tirar una carta no mueve al robot: con un paso por carta, a lo largo
        de una partida terminaria caminando fuera de la mesa.
        """
        if not self.conectado:
            return

        def _hacer():
            # Un gesto por vez: si esta ocupado, se descarta.
            if not self._ocupado.acquire(blocking=False):
                return
            try:
                if tipo == "canto":
                    self.robot.saludar()
                elif tipo == "mazo":
                    self.robot.girar(velocidad=0.3, tiempo=0.6)
            except Exception:
                pass
            finally:
                self._ocupado.release()

        threading.Thread(target=_hacer, daemon=True).start()

    def desconectar(self) -> None:
        if self.conectado and self.robot:
            try:
                self.robot.detenerse()
                self.robot.desconectar()
            except Exception:
                pass
        self.conectado = False
