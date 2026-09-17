"""Imagenes, fuentes, colores y dibujo de cartas para la mesa en pygame."""

import math
from typing import Dict, Optional, Tuple

import pygame

from card_framework import rutas
from card_framework.core.card import Card, Suit

# Lienzo logico. La ventana se escala sola (pygame.SCALED).
ANCHO, ALTO = 1280, 720

# Tamano base de una carta; todo lo demas es una escala de este.
CARTA_W, CARTA_H = 150, 229

COLOR = {
    "fondo": (24, 19, 16),
    "luz": (120, 86, 52),
    "pano": (46, 92, 62),
    "pano_claro": (62, 116, 80),
    "pano_oscuro": (30, 64, 43),
    "madera": (92, 58, 32),
    "madera_oscura": (54, 33, 18),
    "hueco": (120, 170, 128),
    "crema": (239, 230, 210),
    "tinta": (42, 38, 34),
    "dorado": (226, 184, 92),
    "texto": (240, 234, 222),
    "texto_suave": (186, 174, 156),
    "panel": (34, 28, 24),
    "panel_borde": (88, 72, 56),
    "boton": (214, 200, 176),
    "boton_hover": (236, 224, 200),
    "boton_texto": (34, 28, 24),
    "deshabilitado": (78, 70, 62),
    "quiero": (72, 148, 88),
    "no_quiero": (176, 64, 56),
    "oscuro": (30, 30, 30),
}

_PALO_ARCHIVO = {
    Suit.ESPADA: "espadas",
    Suit.BASTO: "bastos",
    Suit.ORO: "oros",
    Suit.COPA: "copas",
}

_FUENTES_SERIF = "georgia,constantia,timesnewroman,dejavuserif"
_FUENTES_SANS = "segoeui,helveticaneue,helvetica,arial,dejavusans"


def rotar_punto(x: float, y: float, grados: float) -> Tuple[float, float]:
    """Rota (x, y) como lo hace pygame.transform.rotate (antihorario en pantalla)."""
    a = math.radians(grados)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def esquinas(cx: float, cy: float, w: float, h: float, grados: float):
    """Las cuatro esquinas de un rectangulo rotado, en orden."""
    puntos = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        dx, dy = rotar_punto(sx * w / 2, sy * h / 2, grados)
        puntos.append((cx + dx, cy + dy))
    return puntos


class Recursos:
    """Carga perezosa y cache de todo lo que se dibuja."""

    def __init__(self):
        self._fuentes: Dict[tuple, pygame.font.Font] = {}
        self._bases: Dict[str, pygame.Surface] = {}
        self._cache: Dict[tuple, pygame.Surface] = {}

    # ---------- fuentes ----------
    def fuente(self, tam: int, negrita: bool = False, serif: bool = False) -> pygame.font.Font:
        clave = (tam, negrita, serif)
        if clave not in self._fuentes:
            nombres = _FUENTES_SERIF if serif else _FUENTES_SANS
            self._fuentes[clave] = pygame.font.SysFont(nombres, tam, bold=negrita)
        return self._fuentes[clave]

    # ---------- cartas ----------
    @staticmethod
    def clave_carta(carta: Optional[Card]) -> str:
        if carta is None:
            return "reverso"
        return f"{carta.value:02d}_{_PALO_ARCHIVO[carta.suit]}"

    def _base(self, clave: str) -> pygame.Surface:
        if clave in self._bases:
            return self._bases[clave]

        base = pygame.Surface((CARTA_W, CARTA_H), pygame.SRCALPHA)
        ruta = None
        if rutas.CARTAS:
            if clave == "reverso":
                ruta = rutas.CARTAS / "reverso.png"
            elif (rutas.CARTAS / "hd" / f"{clave}.png").exists():
                ruta = rutas.CARTAS / "hd" / f"{clave}.png"
            else:
                ruta = rutas.CARTAS / "x4" / f"{clave}.png"

        if ruta and ruta.exists() and ruta.parent.name != "x4":
            # El reverso y las cartas hd ya traen su borde y las esquinas transparentes.
            img = pygame.image.load(str(ruta)).convert_alpha()
            base.blit(pygame.transform.smoothscale(img, (CARTA_W, CARTA_H)), (0, 0))
        else:
            pygame.draw.rect(base, (250, 247, 240), base.get_rect(), border_radius=11)
            if ruta and ruta.exists():
                img = pygame.image.load(str(ruta)).convert_alpha()
                # Recorte de unos pixeles: los PNG traen el borde sucio.
                w, h = img.get_size()
                img = img.subsurface(pygame.Rect(4, 4, w - 8, h - 8))
                img = pygame.transform.smoothscale(img, (CARTA_W - 10, CARTA_H - 10))
                base.blit(img, (5, 5))
            else:
                self._dibujar_carta_sin_imagen(base, clave)
            pygame.draw.rect(base, (150, 140, 124), base.get_rect(), width=2, border_radius=11)

        self._bases[clave] = base
        return base

    def _dibujar_carta_sin_imagen(self, base: pygame.Surface, clave: str) -> None:
        valor, palo = clave.split("_")
        f = self.fuente(40, negrita=True, serif=True)
        t = f.render(str(int(valor)), True, COLOR["tinta"])
        base.blit(t, t.get_rect(center=(CARTA_W // 2, CARTA_H // 2 - 16)))
        t = self.fuente(20).render(palo, True, COLOR["tinta"])
        base.blit(t, t.get_rect(center=(CARTA_W // 2, CARTA_H // 2 + 24)))

    def _forma(self, tipo: str) -> pygame.Surface:
        """Siluetas con la forma de la carta: sombra y velo oscuro."""
        if tipo not in self._bases:
            s = pygame.Surface((CARTA_W, CARTA_H), pygame.SRCALPHA)
            alfa = 70 if tipo == "sombra" else 125
            pygame.draw.rect(s, (0, 0, 0, alfa), s.get_rect(), border_radius=11)
            self._bases[tipo] = s
        return self._bases[tipo]

    def _transformar(self, clave: str, base: pygame.Surface, escala: float, angulo: float,
                     aplastar: float, ancho_giro: float) -> pygame.Surface:
        # Se cuantiza para que las animaciones no llenen el cache.
        escala = round(escala * 50) / 50
        angulo = round(angulo / 2) * 2
        aplastar = round(aplastar, 2)
        ancho_giro = round(ancho_giro, 2)
        k = (clave, escala, angulo, aplastar, ancho_giro)
        if k in self._cache:
            return self._cache[k]
        if len(self._cache) > 900:
            self._cache.clear()

        if aplastar == 1.0 and ancho_giro == 1.0:
            # Escala uniforme: rotozoom escala y rota en una sola pasada.
            img = pygame.transform.rotozoom(base, angulo, escala)
        else:
            w = max(2, round(CARTA_W * escala * ancho_giro))
            h = max(2, round(CARTA_H * escala * aplastar))
            img = pygame.transform.smoothscale(base, (w, h))
            if angulo:
                img = pygame.transform.rotozoom(img, angulo, 1.0)
        self._cache[k] = img
        return img

    def carta(self, carta: Optional[Card], escala: float, angulo: float = 0.0,
              aplastar: float = 1.0, ancho_giro: float = 1.0) -> pygame.Surface:
        clave = self.clave_carta(carta)
        return self._transformar(clave, self._base(clave), escala, angulo, aplastar, ancho_giro)

    def forma(self, tipo: str, escala: float, angulo: float = 0.0,
              aplastar: float = 1.0, ancho_giro: float = 1.0) -> pygame.Surface:
        return self._transformar(tipo, self._forma(tipo), escala, angulo, aplastar, ancho_giro)

    def dibujar_carta(self, destino: pygame.Surface, carta: Optional[Card], x: float, y: float,
                      escala: float, angulo: float = 0.0, aplastar: float = 1.0,
                      ancho_giro: float = 1.0, sombra: bool = True, velo: bool = False) -> None:
        if sombra:
            s = self.forma("sombra", escala, angulo, aplastar, ancho_giro)
            destino.blit(s, s.get_rect(center=(x + 5 * escala, y + 9 * escala)))
        img = self.carta(carta, escala, angulo, aplastar, ancho_giro)
        destino.blit(img, img.get_rect(center=(x, y)))
        if velo:
            v = self.forma("velo", escala, angulo, aplastar, ancho_giro)
            destino.blit(v, v.get_rect(center=(x, y)))

    # ---------- fondos ----------
    def fondo(self) -> pygame.Surface:
        """Ambiente de bodegon: oscuro, con una luz calida sobre la mesa."""
        if "fondo" not in self._bases:
            s = pygame.Surface((ANCHO, ALTO))
            s.fill(COLOR["fondo"])
            luz = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            cx, cy = ANCHO // 2, int(ALTO * 0.55)
            pasos = 60
            for i in range(pasos):
                p = i / pasos
                rx, ry = int(820 * (1 - p)), int(560 * (1 - p))
                alfa = int(9 * p + 1)
                pygame.draw.ellipse(luz, (*COLOR["luz"], alfa),
                                    pygame.Rect(cx - rx, cy - ry, 2 * rx, 2 * ry))
            s.blit(luz, (0, 0))
            self._bases["fondo"] = s
        return self._bases["fondo"]
