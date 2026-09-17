"""El anotador de papel con palitos: cada cuadrado cerrado con su diagonal son 5 puntos."""

import pygame

from card_framework.interfaces.mesa.recursos import COLOR
from card_framework.interfaces.mesa.widgets import texto

LADO = 26       # lado de cada cuadrado de 5 puntos
SEPARACION = 9  # espacio vertical entre cuadrados


def _cuadrado(destino: pygame.Surface, x: int, y: int, puntos: int) -> None:
    """Dibuja hasta 5 trazos: izquierda, arriba, derecha, abajo y la diagonal."""
    tinta = COLOR["tinta"]
    a, b, c, d = (x, y), (x + LADO, y), (x + LADO, y + LADO), (x, y + LADO)
    trazos = [(a, d), (a, b), (b, c), (d, c), (d, b)]
    for inicio, fin in trazos[:puntos]:
        pygame.draw.line(destino, tinta, inicio, fin, 3)


def alto_necesario(objetivo: int) -> int:
    cuadrados = objetivo // 5
    extra = 18 if objetivo == 30 else 0
    return 62 + cuadrados * (LADO + SEPARACION) + extra + 30


def dibujar(destino: pygame.Surface, rec, rect: pygame.Rect, nombres, puntos, objetivo: int) -> None:
    # Papel con sombra.
    sombra = pygame.Surface((rect.w + 16, rect.h + 16), pygame.SRCALPHA)
    pygame.draw.rect(sombra, (0, 0, 0, 90), sombra.get_rect().inflate(-6, -6).move(3, 7), border_radius=6)
    destino.blit(sombra, (rect.x - 8, rect.y - 8))
    pygame.draw.rect(destino, COLOR["crema"], rect, border_radius=4)

    tinta = COLOR["tinta"]
    medio = rect.centerx
    f = rec.fuente(22, negrita=True, serif=True)
    texto(destino, nombres[0], f, tinta, (rect.x + rect.w * 0.27, rect.y + 24))
    texto(destino, nombres[1], f, tinta, (rect.x + rect.w * 0.73, rect.y + 24))

    y_linea = rect.y + 44
    pygame.draw.line(destino, tinta, (rect.x + 12, y_linea), (rect.right - 12, y_linea), 2)
    pygame.draw.line(destino, tinta, (medio, y_linea - 30), (medio, rect.bottom - 34), 2)

    y0 = y_linea + 14
    cuadrados = objetivo // 5
    for col, pts in enumerate(puntos):
        cx = rect.x + rect.w * (0.27 if col == 0 else 0.73)
        x = int(cx - LADO / 2)
        y = y0
        restantes = min(pts, objetivo)
        for i in range(cuadrados):
            if objetivo == 30 and i == 3:
                y += 18  # hueco para la linea de malas y buenas
            if restantes > 0:
                _cuadrado(destino, x, y, min(5, restantes))
                restantes -= 5
            y += LADO + SEPARACION

    if objetivo == 30:
        # Linea de malas y buenas, con el rotulo sobre el palo del medio.
        y_buenas = y0 + 3 * (LADO + SEPARACION) + 4
        pygame.draw.line(destino, (150, 120, 100), (rect.x + 12, y_buenas), (rect.right - 12, y_buenas), 1)
        f_chica = rec.fuente(11, serif=True)
        for rotulo, dy in (("malas", -9), ("buenas", 9)):
            img = f_chica.render(rotulo, True, (130, 110, 92))
            caja = img.get_rect(center=(medio, y_buenas + dy)).inflate(4, 0)
            pygame.draw.rect(destino, COLOR["crema"], caja)
            destino.blit(img, img.get_rect(center=caja.center))

    f_num = rec.fuente(17, negrita=True)
    texto(destino, f"{puntos[0]}", f_num, tinta, (rect.x + rect.w * 0.27, rect.bottom - 17))
    texto(destino, f"{puntos[1]}", f_num, tinta, (rect.x + rect.w * 0.73, rect.bottom - 17))
    texto(destino, f"a {objetivo}", rec.fuente(12), (130, 110, 92), (medio, rect.bottom - 16))
