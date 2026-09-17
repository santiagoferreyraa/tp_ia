"""Piezas de interfaz reutilizables: texto, botones, globos de dialogo y animacion."""

from typing import Callable, List, Optional, Tuple

import pygame

from card_framework.interfaces.mesa.recursos import COLOR


# ---------- animacion ----------
def suavizar(p: float) -> float:
    """Ease-in-out cubico, p en [0, 1]."""
    p = max(0.0, min(1.0, p))
    return 4 * p * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def salir(p: float) -> float:
    """Ease-out cubico: arranca rapido y frena al llegar."""
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def mezclar(a: float, b: float, p: float) -> float:
    return a + (b - a) * p


# ---------- texto ----------
def texto(destino: pygame.Surface, contenido: str, fuente: pygame.font.Font,
          color: Tuple[int, int, int], pos: Tuple[float, float], ancla: str = "center",
          alfa: int = 255) -> pygame.Rect:
    img = fuente.render(contenido, True, color)
    if alfa < 255:
        img.set_alpha(alfa)
    rect = img.get_rect(**{ancla: (round(pos[0]), round(pos[1]))})
    destino.blit(img, rect)
    return rect


def envolver(contenido: str, fuente: pygame.font.Font, ancho: int) -> List[str]:
    """Parte el texto en lineas que entran en `ancho`. Respeta los saltos de linea."""
    lineas: List[str] = []
    for parrafo in contenido.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            prueba = f"{actual} {palabra}".strip()
            if fuente.size(prueba)[0] <= ancho or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        lineas.append(actual)
    return lineas


def parrafo(destino: pygame.Surface, contenido: str, fuente: pygame.font.Font,
            color, x: int, y: int, ancho: int, interlineado: float = 1.3) -> int:
    """Dibuja texto envuelto desde (x, y). Devuelve la y donde termino."""
    alto = int(fuente.get_height() * interlineado)
    for linea in envolver(contenido, fuente, ancho):
        if linea:
            destino.blit(fuente.render(linea, True, color), (x, y))
        y += alto
    return y


_PANELES = {}


def panel(destino: pygame.Surface, rect: pygame.Rect, color=None, borde=None,
          radio: int = 18, alfa: int = 235, sombra: bool = True) -> None:
    """Caja redondeada semitransparente con sombra. Se cachea por forma."""
    color = color or COLOR["panel"]
    clave = (rect.size, color, borde, radio, alfa, sombra)
    img = _PANELES.get(clave)
    if img is None:
        img = pygame.Surface((rect.w + 24, rect.h + 24), pygame.SRCALPHA)
        if sombra:
            pygame.draw.rect(img, (0, 0, 0, 70), img.get_rect().inflate(-8, -8).move(4, 8), border_radius=radio + 6)
        caja = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(caja, (*color, alfa), caja.get_rect(), border_radius=radio)
        if borde:
            pygame.draw.rect(caja, borde, caja.get_rect(), width=2, border_radius=radio)
        img.blit(caja, (12, 12))
        _PANELES[clave] = img
    destino.blit(img, (rect.x - 12, rect.y - 12))


# ---------- botones ----------
ESTILOS = {
    # fondo, fondo con hover, texto
    "claro": (COLOR["boton"], COLOR["boton_hover"], COLOR["boton_texto"]),
    "medio": ((150, 138, 120), (174, 162, 142), COLOR["boton_texto"]),
    "oscuro": (COLOR["oscuro"], (58, 54, 50), COLOR["texto"]),
    "dorado": (COLOR["dorado"], (242, 206, 124), COLOR["boton_texto"]),
    "quiero": (COLOR["quiero"], (92, 172, 108), (250, 250, 245)),
    "no_quiero": (COLOR["no_quiero"], (200, 86, 76), (250, 250, 245)),
}


class Boton:
    def __init__(self, rect, etiqueta: str, al_click: Optional[Callable[[], None]] = None,
                 estilo: str = "claro", tam: int = 20, radio: int = 8):
        self.rect = pygame.Rect(rect)
        self.etiqueta = etiqueta
        self.al_click = al_click
        self.estilo = estilo
        self.tam = tam
        self.radio = radio
        self.habilitado = True
        self.visible = True
        self.activo = False      # resaltado fijo (ej. pestana elegida)
        self._hover = False

    def evento(self, e: pygame.event.Event) -> bool:
        if not (self.visible and self.habilitado):
            self._hover = False
            return False
        if e.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            if self.al_click:
                self.al_click()
            return True
        return False

    def dibujar(self, destino: pygame.Surface, rec) -> None:
        if not self.visible:
            return
        fondo, fondo_hover, color_texto = ESTILOS[self.estilo]
        r = self.rect
        if not self.habilitado:
            fondo, color_texto = COLOR["deshabilitado"], (130, 122, 112)
        elif self._hover or self.activo:
            fondo = fondo_hover
            r = r.move(0, -2)
        if self.habilitado:
            pygame.draw.rect(destino, (0, 0, 0), r.move(0, 4), border_radius=self.radio)
        pygame.draw.rect(destino, fondo, r, border_radius=self.radio)
        if self.activo:
            pygame.draw.rect(destino, COLOR["dorado"], r, width=3, border_radius=self.radio)
        texto(destino, self.etiqueta, rec.fuente(self.tam, negrita=True), color_texto, r.center)


# ---------- globo de dialogo ----------
class Globo:
    """Lo que dice un jugador. Se desvanece solo."""

    def __init__(self, contenido: str, ahora: float, duracion: Optional[float] = None):
        self.contenido = contenido
        self.inicio = ahora
        self.duracion = duracion or max(2.4, 1.2 + len(contenido) * 0.055)

    def vivo(self, ahora: float) -> bool:
        return ahora - self.inicio < self.duracion

    def dibujar(self, destino: pygame.Surface, rec, ancla: Tuple[int, int], ancho: int,
                ahora: float, cola: str = "izquierda") -> None:
        t = ahora - self.inicio
        alfa = min(1.0, t / 0.18, (self.duracion - t) / 0.4)
        if alfa <= 0:
            return
        crecer = 0.9 + 0.1 * salir(min(1.0, t / 0.2))

        fuente = rec.fuente(19, serif=True)
        lineas = envolver(self.contenido, fuente, ancho - 36)
        alto_linea = int(fuente.get_height() * 1.2)
        w, h = ancho, 26 + alto_linea * len(lineas)

        s = pygame.Surface((w + 20, h + 20), pygame.SRCALPHA)
        caja = pygame.Rect(10, 10, w, h)
        pygame.draw.rect(s, (0, 0, 0, 60), caja.move(3, 5), border_radius=16)
        pygame.draw.rect(s, COLOR["crema"], caja, border_radius=16)
        if cola == "izquierda":
            punta = [(caja.left + 2, caja.top + 22), (caja.left - 10, caja.top + 34), (caja.left + 2, caja.top + 40)]
        else:
            punta = [(caja.right - 2, caja.top + 22), (caja.right + 10, caja.top + 34), (caja.right - 2, caja.top + 40)]
        pygame.draw.polygon(s, COLOR["crema"], punta)
        y = caja.top + 13
        for linea in lineas:
            s.blit(fuente.render(linea, True, COLOR["tinta"]), (caja.left + 18, y))
            y += alto_linea

        if crecer != 1.0:
            s = pygame.transform.smoothscale(s, (int(s.get_width() * crecer), int(s.get_height() * crecer)))
        s.set_alpha(int(255 * alfa))
        x, y = ancla
        if cola == "izquierda":
            destino.blit(s, (x - 10, y - 10))
        else:
            destino.blit(s, (x - s.get_width() + 10, y - 10))
