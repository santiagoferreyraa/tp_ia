"""Conexion opcional con el robot: el simulador 3D de Unitree o el G1 real.

- simulador (por defecto): si el simulador del TP07 esta abierto, el G1
  gesticula cuando canta. Si no, la mesa se juega igual.
- real: el G1 fisico por DDS (solo Linux, con el SDK de Unitree instalado).
  SIN PROBAR EN EL ROBOT: se escribio con la misma API que usa `robot.py`.

Nada de esto puede romper ni trabar la partida: cada orden va en su hilo y
cualquier error se registra y se ignora.

Cada orden que se manda al robot queda registrada con fecha y hora, como pide
la consigna para el robot fisico.
"""

import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from card_framework import rutas

CARPETA_REGISTROS = rutas.TP07 / "registros"


class RobotSimulado:
    def __init__(self, destino: str = "simulador", interfaz: Optional[str] = None,
                 voz_en_robot: bool = False, registrar: bool = False):
        self.destino = destino
        self.interfaz = interfaz
        self.voz_en_robot = voz_en_robot
        self.robot = None
        self.audio = None
        self.conectado = False
        self._ocupado = threading.Lock()
        self._archivo: Optional[Path] = None
        if registrar:
            self.activar_registro()

    # ---------- registro ----------
    def activar_registro(self) -> Optional[Path]:
        """Empieza un archivo de registro nuevo (uno por partida real)."""
        try:
            CARPETA_REGISTROS.mkdir(parents=True, exist_ok=True)
            self._archivo = CARPETA_REGISTROS / f"truco_{datetime.now():%Y%m%d_%H%M%S}.log"
        except OSError:
            self._archivo = None
        return self._archivo

    def registrar(self, texto: str) -> None:
        linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {texto}"
        if self._archivo:
            try:
                with open(self._archivo, "a", encoding="utf-8") as f:
                    f.write(linea + "\n")
            except OSError:
                pass

    # ---------- conexion ----------
    def conectar_en_segundo_plano(self) -> None:
        threading.Thread(target=self._conectar, daemon=True).start()

    def _conectar(self) -> None:
        try:
            if str(rutas.MI_DESARROLLO) not in sys.path:
                sys.path.insert(0, str(rutas.MI_DESARROLLO))
            from robot import Robot  # noqa: WPS433 - import perezoso a proposito

            if self.destino == "real":
                robot = Robot(destino="g1", interfaz=self.interfaz or "", materia="tp07")
            else:
                robot = Robot()
            robot.conectar()
            self.robot, self.conectado = robot, True
            self.registrar(f"CONEXION  {self.destino}")
            print(f"[Truco] Conectado al G1 ({self.destino}).")
        except Exception as exc:
            self.robot, self.conectado = None, False
            self.registrar(f"SIN CONEXION  {self.destino}: {exc}")
            print("[Truco] Sin robot conectado: se juega solo en la pantalla.")
            return

        if self.destino == "real" and self.voz_en_robot:
            self._conectar_audio()

    def _conectar_audio(self) -> None:
        """Parlante del G1 (SDK de Unitree). SIN PROBAR: si falla, habla la notebook."""
        try:
            from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient

            audio = AudioClient()
            audio.SetTimeout(10.0)
            audio.Init()
            self.audio = audio
            self.registrar("AUDIO G1  conectado")
        except Exception as exc:
            self.audio = None
            self.registrar(f"AUDIO G1  no disponible: {exc}")

    # ---------- ordenes ----------
    def habla_el_robot(self) -> bool:
        return self.audio is not None

    def decir(self, texto: str) -> None:
        """Habla por el parlante del G1. Devuelve enseguida; solo si hay audio del robot."""
        self.registrar(f"DICE  {texto!r}")
        if not self.audio:
            return

        def _hablar():
            try:
                self.audio.TtsMaker(texto.replace("\n", ", "), 0)
            except Exception as exc:
                self.registrar(f"AUDIO G1  error: {exc}")

        threading.Thread(target=_hablar, daemon=True).start()

    def gesto(self, tipo: str) -> None:
        """tipo: 'canto' (saluda) o 'mazo' (se da vuelta).

        Tirar una carta no mueve al robot: con un paso por carta, a lo largo
        de una partida terminaria caminando fuera de la mesa. Con el robot
        real tampoco se gira: no se mueve de su lugar.
        """
        if not self.conectado:
            return
        if tipo == "mazo" and self.destino == "real":
            return

        def _hacer():
            # Un gesto por vez: si esta ocupado, se descarta.
            if not self._ocupado.acquire(blocking=False):
                return
            try:
                self.registrar(f"GESTO  {tipo}")
                if tipo == "canto":
                    self.robot.saludar()
                elif tipo == "mazo":
                    self.robot.girar(velocidad=0.3, tiempo=0.6)
            except Exception as exc:
                self.registrar(f"GESTO  error: {exc}")
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
            self.registrar("DESCONEXION")
        self.conectado = False
