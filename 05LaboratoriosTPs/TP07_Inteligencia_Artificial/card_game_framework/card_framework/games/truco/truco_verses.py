"""Módulo para gestionar y recitar los versos tradicionales del Truco Argentino."""

import random
from pathlib import Path
from typing import Dict, List

from card_framework import rutas

FRASES_PATH = rutas.FRASES or Path()

DEFAULT_VERSES: Dict[str, List[str]] = {
    "ENVIDO": [
        "Cuando vine de La Isla traiba un lazo retorcido; con él enlacé dos cartas y con dos le digo Envido.",
        "Envido le digo hermano, con la fuerza de mi mano."
    ],
    "REAL_ENVIDO": [
        "No piense en un descuido... si no es pa' tanto la cosa, yo le digo Real envido que es lo mesmo que olorosa.",
        "Con su boquita de grana y su pelo renegrido, no envidia a la mañana este hermoso Real envido."
    ],
    "FALTA_ENVIDO": [
        "Una vez una paloma ofreció darme su nido, y yo creyendo una broma no le eché la Falta envido.",
        "No se ponga tan contento por el envite que ha echao, porque escuchará al momento: Falta envido, cuñao."
    ],
    "TRUCO": [
        "Los gauchos del General peleaban con trabuco, yo peleo con tres cartas porque estoy jugando al Truco.",
        "Una carrera corrieron el sapo y la comadreja, y el sapo al aventajarla le dijo Truco en la oreja.",
        "Aquí me presento yo en mi tordillo pazuco, pa contarle los primores que puede tener el Truco."
    ],
    "RETRUCO": [
        "Con las cartas que yo tengo tampoco me asusta el cuco, y si es que no me detengo le digo Quiero y retruco.",
        "Quiero y Retruco te canto en la cara."
    ],
    # frases.md no trae verso de vale cuatro: se canta derecho.
    "VALE_CUATRO": [
        "¡Quiero vale cuatro!"
    ]
}


def _guardar(verses: Dict[str, List[str]], section, buffer: List[str]) -> None:
    """Guarda un verso conservando sus renglones."""
    if not section or not buffer:
        return
    verso = "\n".join(buffer)
    # "...le digo Quiero y retruco" esta bajo Truco, pero es un verso de retruco.
    if section == "TRUCO" and "retruco" in verso.lower():
        section = "RETRUCO"
    verses[section].append(verso)


def load_verses_from_markdown() -> Dict[str, List[str]]:
    """Carga los versos gauchos del archivo frases.md."""
    verses: Dict[str, List[str]] = {
        "ENVIDO": [],
        "REAL_ENVIDO": [],
        "FALTA_ENVIDO": [],
        "TRUCO": [],
        "RETRUCO": [],
        "VALE_CUATRO": []
    }

    if not FRASES_PATH.exists():
        return DEFAULT_VERSES

    try:
        content = FRASES_PATH.read_text(encoding="utf-8")
        current_section = None
        buffer = []

        for line in content.splitlines():
            line_str = line.strip()
            if not line_str:
                _guardar(verses, current_section, buffer)
                buffer = []
                continue

            lower_line = line_str.lower()
            if lower_line == "envido":
                current_section = "ENVIDO"
            elif lower_line == "real envido":
                current_section = "REAL_ENVIDO"
            elif lower_line == "falta envido":
                current_section = "FALTA_ENVIDO"
            elif lower_line == "truco":
                current_section = "TRUCO"
            elif lower_line in ("envido y truco", "falta envido y truco"):
                # Son cantos dobles que el juego no tiene: esos versos no se usan.
                current_section = None
            elif not line_str.startswith("#"):
                buffer.append(line_str)

        _guardar(verses, current_section, buffer)

        # Completar con defaults si alguna categoría quedó vacía
        for k, v in DEFAULT_VERSES.items():
            if not verses.get(k):
                verses[k] = v

        return verses
    except Exception:
        return DEFAULT_VERSES


VERSES_DB = load_verses_from_markdown()


def get_random_verse(bid_type: str) -> str:
    """Devuelve un verso gaucho aleatorio correspondiente al tipo de cante."""
    key = bid_type.upper().replace(" ", "_")
    if key in VERSES_DB and VERSES_DB[key]:
        return random.choice(VERSES_DB[key])
    return f"¡{bid_type}!"
