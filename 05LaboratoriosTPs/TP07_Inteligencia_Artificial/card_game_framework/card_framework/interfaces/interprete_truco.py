"""Interprete de lo que dice el rival en la mesa real. Mismo pipeline que el TP07.

    texto -> Clasificador -> Extractor -> Validador -> accion del motor (o rechazo)

El operador escribe lo que dijo el rival ("quiero retruco", "tiro el ancho de
espada", "tengo 27") y el interprete lo traduce a una jugada. Como en el TP07,
el VALIDADOR es independiente: aunque el clasificador entienda, si esa jugada
no es legal en este momento de la partida, se rechaza con el motivo.

El dia que haya microfono, el texto sale del reconocimiento de voz y el resto
del pipeline no cambia.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional

from card_framework.core.action import Action, ActionType
from card_framework.core.card import Suit

INTENCIONES = ("NO_QUIERO", "QUIERO", "ENVIDO", "REAL_ENVIDO", "FALTA_ENVIDO", "TRUCO", "RETRUCO",
               "VALE_CUATRO", "MAZO", "TIRAR_CARTA", "DECLARAR_ENVIDO", "DESCONOCIDO")

NUMEROS = {
    "cero": 0, "uno": 1, "un": 1, "ancho": 1, "as": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "sota": 10, "once": 11, "caballo": 11, "doce": 12, "rey": 12,
    "veinte": 20, "veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28,
    "veintinueve": 29, "treinta": 30,
}
PALOS = {"espada": Suit.ESPADA, "basto": Suit.BASTO, "oro": Suit.ORO, "copa": Suit.COPA}


def normalizar(texto: str) -> str:
    """Minusculas, sin tildes ni signos: 'Quiero Retrucó!' -> 'quiero retruco'."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


# ---------------------------------------------------------------------------
#  Etapa 1: clasificador (reglas, en orden: lo mas especifico primero)
# ---------------------------------------------------------------------------
REGLAS = [
    ("NO_QUIERO", r"\bno (lo )?quiero\b|\bno quiero nada\b"),
    ("DECLARAR_ENVIDO", r"\btengo\b.*\b(\d+|veint\w*|treinta\w*|cero|nada)\b|\bson buenas\b|\bson mejores\b"),
    ("VALE_CUATRO", r"\bvale (cuatro|4)\b"),
    ("RETRUCO", r"\bretruco\b"),
    ("FALTA_ENVIDO", r"\bfalta envido\b|\bla falta\b"),
    ("REAL_ENVIDO", r"\breal envido\b"),
    ("ENVIDO", r"\benvido\b"),
    ("TRUCO", r"\btruco\b"),
    ("MAZO", r"\bmazo\b|\bme voy\b|\bme retiro\b"),
    ("TIRAR_CARTA", r"\b(espada|basto|oro|copa)s?\b"),
    ("QUIERO", r"\bquiero\b|\bacepto\b|\bdale\b|\bva\b"),
]


class ClasificadorTruco:
    def clasificar(self, texto: str) -> str:
        t = normalizar(texto)
        for intencion, patron in REGLAS:
            if re.search(patron, t):
                return intencion
        return "DESCONOCIDO"


# ---------------------------------------------------------------------------
#  Etapa 2: extractor de parametros
# ---------------------------------------------------------------------------
class ExtractorTruco:
    def extraer(self, texto: str, intencion: str) -> dict:
        t = normalizar(texto)
        params = {}
        if intencion == "TIRAR_CARTA":
            palo = re.search(r"\b(espada|basto|oro|copa)s?\b", t)
            if palo:
                params["palo"] = PALOS[palo.group(1)]
            valor = self._numero(t)
            if valor is not None:
                params["valor"] = valor
        elif intencion == "DECLARAR_ENVIDO":
            if re.search(r"\bson buenas\b", t):
                params["son_buenas"] = True
            else:
                n = self._tantos(t)
                if n is not None:
                    params["envido"] = n
        return params

    @staticmethod
    def _numero(t: str) -> Optional[int]:
        m = re.search(r"\b(1[0-2]|[1-9])\b", t)
        if m:
            return int(m.group(1))
        for palabra in t.split():
            if palabra in NUMEROS and NUMEROS[palabra] <= 12:
                return NUMEROS[palabra]
        return None

    @staticmethod
    def _tantos(t: str) -> Optional[int]:
        m = re.search(r"\b(\d{1,2})\b", t)
        if m:
            return int(m.group(1))
        if re.search(r"\bnada\b", t):
            return 0
        # "treinta y tres", "veinte y siete" o "veintisiete"
        m = re.search(r"\b(veinte|treinta)( y (\w+))?\b", t)
        if m:
            base = NUMEROS[m.group(1)]
            extra = NUMEROS.get(m.group(3) or "", 0)
            return base + (extra if extra <= 9 else 0)
        for palabra in t.split():
            if palabra in NUMEROS:
                return NUMEROS[palabra]
        return None


# ---------------------------------------------------------------------------
#  Etapa 3: validador (independiente del clasificador)
# ---------------------------------------------------------------------------
@dataclass
class Interpretacion:
    intencion: str
    parametros: dict
    accion: Optional[Action]
    mensaje: str

    @property
    def aceptada(self) -> bool:
        return self.accion is not None


class ValidadorTruco:
    """Decide si lo entendido es una jugada legal AHORA. Si no, explica por que."""

    def validar(self, intencion: str, params: dict, validas: List[Action]) -> Interpretacion:
        def resultado(accion, mensaje):
            return Interpretacion(intencion, params, accion, mensaje)

        if intencion == "DESCONOCIDO":
            return resultado(None, "No entendí. Probá: 'envido', 'quiero', 'tiro el 7 de oro', 'tengo 27'.")
        if not validas:
            return resultado(None, "Ahora no le toca al rival.")

        if intencion == "TIRAR_CARTA":
            if "palo" not in params or "valor" not in params:
                return resultado(None, "Falta el número o el palo de la carta.")
            if params["valor"] in (8, 9):
                return resultado(None, "En el truco no hay 8 ni 9.")
            accion = next((a for a in validas if a.action_type == ActionType.PLAY_CARD
                           and a.payload["card"].suit == params["palo"]
                           and a.payload["card"].value == params["valor"]), None)
            if accion:
                return resultado(accion, accion.name)
            if any(a.action_type == ActionType.PLAY_CARD for a in validas):
                return resultado(None, "Esa carta ya se vio en esta mano.")
            return resultado(None, "Ahora no se puede tirar: primero hay que contestar el canto.")

        if intencion == "DECLARAR_ENVIDO":
            if not any(a.action_type == ActionType.DECLARE for a in validas):
                return resultado(None, "Ahora no se están declarando tantos.")
            if params.get("son_buenas"):
                # "Son buenas" es aceptar que pierde: se declara el minimo.
                return resultado(next(a for a in validas if a.payload["envido"] == 0), "Son buenas (pierde el envido)")
            if "envido" not in params:
                return resultado(None, "¿Cuántos tantos dijo?")
            accion = next((a for a in validas if a.payload.get("envido") == params["envido"]), None)
            if accion is None:
                return resultado(None, f"{params['envido']} no es un envido posible (0 a 7, o 20 a 33).")
            return resultado(accion, accion.name)

        buscar = {
            "QUIERO": lambda a: (a.payload.get("response") or "").startswith("QUIERO"),
            "NO_QUIERO": lambda a: (a.payload.get("response") or "").startswith("NO_QUIERO"),
            "MAZO": lambda a: a.action_type == ActionType.FOLD,
        }.get(intencion, lambda a: a.payload.get("bid") == intencion)
        accion = next((a for a in validas if buscar(a)), None)
        if accion is None:
            return resultado(None, f"Ahora no se puede: {intencion.replace('_', ' ').lower()}.")
        return resultado(accion, accion.name)


class InterpreteTruco:
    """El pipeline completo."""

    def __init__(self):
        self.clasificador = ClasificadorTruco()
        self.extractor = ExtractorTruco()
        self.validador = ValidadorTruco()

    def interpretar(self, texto: str, acciones_validas: List[Action]) -> Interpretacion:
        intencion = self.clasificador.clasificar(texto)
        params = self.extractor.extraer(texto, intencion)
        return self.validador.validar(intencion, params, acciones_validas)
