"""Menu principal: Nueva partida (a 15 o a 30), Reglas y Salir."""

import pygame

from card_framework.core.card import Card, Suit
from card_framework.interfaces.mesa.recursos import ALTO, ANCHO, COLOR
from card_framework.interfaces.mesa.widgets import Boton, panel, parrafo, texto

PANEL = pygame.Rect(440, 110, 780, 520)

REGLAS = {
    "Cómo se juega": (
        "Mano a mano contra el robot, sin flor. Se reparten 3 cartas y se juegan "
        "hasta 3 bazas: gana la mano quien gane 2.\n"
        "Si una baza sale parda, define la siguiente. Si la primera la ganó alguien "
        "y después hay parda, gana quien ganó la primera. Todo pardas: gana el mano.\n"
        "Una partida se juega a 15 o a 30 puntos. A 30, los primeros 15 son las "
        "malas y los siguientes, las buenas."
    ),
    "Envido": (
        "Se canta en la primera baza, antes de tirar tu carta. Dos cartas del mismo "
        "palo suman 20 más sus valores (10, 11 y 12 valen 0). Sin palo repetido, "
        "vale tu carta más alta.\n"
        "Envido 2 · Real envido 3 · Falta envido: lo que le falta al que va ganando. "
        "A 30, si el que va ganando está en malas, la falta es el partido.\n"
        "No querido: 1 punto, o lo que ya estaba querido en la cadena. Empate: gana el mano.\n"
        "El envido está primero: a un truco en primera le podés contestar con envido."
    ),
    "Truco": (
        "Truco 2 · Retruco 3 · Vale cuatro 4.\n"
        "No querido: se cobra lo anterior (1, 2 o 3 puntos). Subir es querer: "
        "\"Quiero retruco\" ya acepta el truco.\n"
        "Sólo puede subir quien aceptó el último canto.\n"
        "Irse al mazo le da al rival lo que valga la mano. Si te vas en primera "
        "sin que se haya jugado el envido, el rival suma uno más."
    ),
    "Cartas": None,   # la jerarquia se dibuja con las imagenes
}

# De mayor a menor. Cada escalon: (carta que se muestra, rotulo).
JERARQUIA = [
    (Card(Suit.ESPADA, 1), "1 espada"), (Card(Suit.BASTO, 1), "1 basto"),
    (Card(Suit.ESPADA, 7), "7 espada"), (Card(Suit.ORO, 7), "7 oro"),
    (Card(Suit.COPA, 3), "los 3"), (Card(Suit.ORO, 2), "los 2"),
    (Card(Suit.COPA, 1), "1 copa y oro"),
    (Card(Suit.BASTO, 12), "los 12"), (Card(Suit.ESPADA, 11), "los 11"),
    (Card(Suit.COPA, 10), "los 10"), (Card(Suit.COPA, 7), "7 copa y basto"),
    (Card(Suit.ORO, 6), "los 6"), (Card(Suit.BASTO, 5), "los 5"),
    (Card(Suit.ESPADA, 4), "los 4"),
]


class EscenaMenu:
    def __init__(self, app):
        self.app = app
        self.rec = app.recursos
        self.modo = "nueva"
        self.pestana = "Cómo se juega"
        self.objetivo = app.ultimo_objetivo

        x, w, h = 90, 300, 62
        self.btn_nueva = Boton((x, 300, w, h), "NUEVA PARTIDA", lambda: self._modo("nueva"), "medio", 22, 4)
        self.btn_reglas = Boton((x, 390, w, h), "REGLAS", lambda: self._modo("reglas"), "claro", 22, 4)
        self.btn_salir = Boton((x, 480, w, h), "SALIR", app.salir, "oscuro", 22, 4)

        self.btn_15 = Boton((PANEL.x + 120, PANEL.y + 170, 250, 150), "15", lambda: self._objetivo(15), "claro", 64, 14)
        self.btn_30 = Boton((PANEL.right - 370, PANEL.y + 170, 250, 150), "30", lambda: self._objetivo(30), "claro", 64, 14)
        self.btn_empezar = Boton((PANEL.centerx - 130, PANEL.bottom - 110, 260, 60), "EMPEZAR",
                                 lambda: app.nueva_partida(self.objetivo), "dorado", 24, 8)

        self.tabs = []
        tx = PANEL.x + 40
        for nombre in REGLAS:
            w_tab = self.rec.fuente(17, negrita=True).size(nombre)[0] + 34
            self.tabs.append(Boton((tx, PANEL.y + 78, w_tab, 38), nombre,
                                   lambda n=nombre: self._pestana(n), "medio", 17, 19))
            tx += w_tab + 10
        self._refrescar()

    def _modo(self, modo):
        self.modo = modo
        self._refrescar()

    def _objetivo(self, objetivo):
        self.objetivo = objetivo
        self._refrescar()

    def _pestana(self, nombre):
        self.pestana = nombre
        self._refrescar()

    def _refrescar(self):
        self.btn_nueva.activo = self.modo == "nueva"
        self.btn_reglas.activo = self.modo == "reglas"
        for b in (self.btn_15, self.btn_30, self.btn_empezar):
            b.visible = self.modo == "nueva"
        self.btn_15.activo = self.objetivo == 15
        self.btn_30.activo = self.objetivo == 30
        for t in self.tabs:
            t.visible = self.modo == "reglas"
            t.activo = t.etiqueta == self.pestana

    def _botones(self):
        return [self.btn_nueva, self.btn_reglas, self.btn_salir,
                self.btn_15, self.btn_30, self.btn_empezar, *self.tabs]

    # ---------- ciclo ----------
    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.app.salir()
            elif e.key == pygame.K_RETURN and self.modo == "nueva":
                self.app.nueva_partida(self.objetivo)
        for b in self._botones():
            if b.evento(e):
                break

    def actualizar(self, ahora):
        pass

    def dibujar(self, pantalla, ahora):
        rec = self.rec
        pantalla.blit(rec.fondo(), (0, 0))

        # Abanico decorativo que asoma abajo a la izquierda.
        for i, (carta, ang) in enumerate(((Card(Suit.ORO, 7), 28), (Card(Suit.ESPADA, 7), 14),
                                          (Card(Suit.BASTO, 1), 0), (Card(Suit.ESPADA, 1), -14))):
            rec.dibujar_carta(pantalla, carta, 150 + i * 70, ALTO - 40 + abs(i - 1.5) * 12, 0.72, ang)

        texto(pantalla, "TRUCO", rec.fuente(84, negrita=True, serif=True), COLOR["dorado"], (240, 150))
        texto(pantalla, "mano a mano contra el Unitree G1", rec.fuente(19, serif=True),
              COLOR["texto_suave"], (240, 214))

        panel(pantalla, PANEL, borde=COLOR["panel_borde"], radio=34)
        if self.modo == "nueva":
            self._dibujar_nueva(pantalla)
        else:
            self._dibujar_reglas(pantalla)

        for b in self._botones():
            b.dibujar(pantalla, rec)

        texto(pantalla, "TP07 · Inteligencia Artificial · UADE", rec.fuente(14),
              COLOR["texto_suave"], (ANCHO - 30, ALTO - 24), ancla="midright")

    def _dibujar_nueva(self, pantalla):
        rec = self.rec
        texto(pantalla, "Nueva partida", rec.fuente(34, negrita=True, serif=True), COLOR["texto"],
              (PANEL.centerx, PANEL.y + 52))
        texto(pantalla, "¿A cuántos puntos?", rec.fuente(20), COLOR["texto_suave"], (PANEL.centerx, PANEL.y + 130))
        texto(pantalla, "partida corta", rec.fuente(16), COLOR["texto_suave"],
              (self.btn_15.rect.centerx, self.btn_15.rect.bottom + 22))
        texto(pantalla, "con malas y buenas", rec.fuente(16), COLOR["texto_suave"],
              (self.btn_30.rect.centerx, self.btn_30.rect.bottom + 22))
        texto(pantalla, "Sin flor · envido y truco completos", rec.fuente(15), COLOR["texto_suave"],
              (PANEL.centerx, PANEL.bottom - 28))

    def _dibujar_reglas(self, pantalla):
        rec = self.rec
        texto(pantalla, "Reglas", rec.fuente(34, negrita=True, serif=True), COLOR["texto"],
              (PANEL.centerx, PANEL.y + 44))
        contenido = REGLAS[self.pestana]
        x, y = PANEL.x + 50, PANEL.y + 146
        if contenido:
            parrafo(pantalla, contenido, rec.fuente(20), COLOR["texto"], x, y, PANEL.w - 100, 1.4)
            return

        texto(pantalla, "De la más fuerte a la más débil:", rec.fuente(20), COLOR["texto"], (x, y), ancla="topleft")
        paso, escala = 96, 0.46
        for i, (carta, rotulo) in enumerate(JERARQUIA):
            fila, col = divmod(i, 7)
            cx = x + 36 + col * paso
            cy = y + 110 + fila * 172
            rec.dibujar_carta(pantalla, carta, cx, cy, escala)
            texto(pantalla, rotulo, rec.fuente(13), COLOR["texto_suave"], (cx, cy + 66))
            if col < 6 and i < len(JERARQUIA) - 1:
                texto(pantalla, ">", rec.fuente(24, negrita=True), COLOR["dorado"], (cx + paso / 2, cy))
