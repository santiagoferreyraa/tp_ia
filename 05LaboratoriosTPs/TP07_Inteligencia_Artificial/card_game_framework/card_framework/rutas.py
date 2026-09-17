"""Rutas del proyecto, relativas a este archivo.

Nada de rutas absolutas: el paquete tiene que andar en cualquier computadora
donde se clone el repo o se copie la carpeta del TP.
"""

from pathlib import Path
from typing import Optional

# card_framework -> card_game_framework -> TP07_Inteligencia_Artificial
PAQUETE = Path(__file__).resolve().parent
FRAMEWORK = PAQUETE.parent
TP07 = FRAMEWORK.parent

# Carpeta del alumno con robot.py (conexion al simulador de Unitree).
MI_DESARROLLO = TP07 / "mi_desarrollo"


def _buscar_truco() -> Optional[Path]:
    """Busca la carpeta `truco/` (cartas y frases) subiendo desde el paquete.

    Asi funciona tanto si los materiales se copian dentro del TP como si
    quedan en la raiz del repositorio.
    """
    for carpeta in (FRAMEWORK, *FRAMEWORK.parents):
        candidata = carpeta / "truco"
        if (candidata / "cartas").is_dir():
            return candidata
    return None


TRUCO = _buscar_truco()
CARTAS = TRUCO / "cartas" if TRUCO else None
FRASES = TRUCO / "frases" / "frases.md" if TRUCO else None
