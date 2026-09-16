"""Cargador y gestor de imágenes reales PNG de baraja española para la Mesa Virtual Tkinter."""

import tkinter as tk
from pathlib import Path
from typing import Dict, Optional
from card_framework.core.card import Card, Suit

CARTAS_DIR = Path("C:/Users/santi/Documents/GitHub/UadeRobotLab/truco/cartas/original")

# Caché para no recargar las imágenes de disco en cada actualización de UI
_IMAGE_CACHE: Dict[str, tk.PhotoImage] = {}


def get_card_image_path(card: Card) -> Optional[Path]:
    """Devuelve la ruta absoluta al archivo PNG de la carta especificada."""
    suit_str = {
        Suit.ESPADA: "espadas",
        Suit.BASTO: "bastos",
        Suit.ORO: "oros",
        Suit.COPA: "copas"
    }.get(card.suit)

    if not suit_str:
        return None

    filename = f"{card.value:02d}_{suit_str}.png"
    img_path = CARTAS_DIR / filename
    if img_path.exists():
        return img_path
    return None


def get_card_photo_image(card: Card) -> Optional[tk.PhotoImage]:
    """Carga y devuelve un objeto PhotoImage de Tkinter para la carta dada."""
    cache_key = f"{card.suit.value}_{card.value}"
    if cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key]

    path = get_card_image_path(card)
    if path:
        try:
            photo = tk.PhotoImage(file=str(path))
            _IMAGE_CACHE[cache_key] = photo
            return photo
        except Exception:
            return None
    return None
