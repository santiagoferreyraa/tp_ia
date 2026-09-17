"""Pantalla del OPERADOR para jugar contra el G1 con cartas de verdad.

El robot no ve la mesa. Desde esta pantalla el operador:
  1. carga las 3 cartas que le repartieron al G1,
  2. marca lo que hace el rival (que carta tira, que canta, cuantos tantos dice),
     con clicks o escribiendolo (lo traduce el interprete, estilo TP07),
  3. ve en grande la jugada del G1 y confirma cuando el ayudante tiro la carta.

El G1 dice sus jugadas en voz alta (por su parlante si esta disponible, si no
por la notebook) y gesticula si hay un robot conectado. Todo queda registrado
con fecha y hora.
"""

import random
from datetime import datetime
from typing import List, Optional

import pygame

from card_framework.core.action import Action, ActionType
from card_framework.core.card import Card, Suit
from card_framework.games.truco.truco_deck import calculate_envido_points, get_truco_rank
from card_framework.games.truco.truco_game import ENVIDOS_POSIBLES
from card_framework.interfaces.frases_robot import NOMBRE_CANTO, nombre_carta
from card_framework.interfaces.interprete_truco import InterpreteTruco
from card_framework.interfaces.mesa import anotador
from card_framework.interfaces.mesa.recursos import ALTO, ANCHO, CARTA_H, CARTA_W, COLOR
from card_framework.interfaces.mesa.widgets import Boton, envolver, panel, salir, texto
from card_framework.interfaces.partida_real import PartidaReal, Resultado

PALOS_GRILLA = (Suit.ESPADA, Suit.BASTO, Suit.ORO, Suit.COPA)
VALORES_GRILLA = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)
MAZO_COMPLETO = [Card(p, v, get_truco_rank(p, v)) for p in PALOS_GRILLA for v in VALORES_GRILLA]

CENTRO = pygame.Rect(424, 104, 624, 600)   # zona de trabajo del operador
NOMBRE_ROBOT = "G1"


class EscenaOperador:
    def __init__(self, app, objetivo: int, robot_es_mano: bool, farol: float = 0.5):
        self.app = app
        self.rec = app.recursos
        self.objetivo = objetivo
        self.robot_es_mano = robot_es_mano
        self.partida = PartidaReal(objetivo=objetivo, farol=farol, robot_es_mano=robot_es_mano,
                                   nombre_robot=NOMBRE_ROBOT)
        self.interprete = InterpreteTruco()
        self.ahora = 0.0

        self.seleccion: List[Card] = []       # cartas del G1 que marca el operador
        self.pendiente: Optional[Resultado] = None   # carta que el ayudante tiene que tirar
        self.aviso = None                     # (titulo, detalle, inicio, duracion)
        self._cola_avisos: list = []          # avisos encadenados, se muestran de a uno
        self.bloqueado_hasta = 0.0
        self.robot_juega_en: Optional[float] = None
        self.dice: Optional[tuple] = None     # (texto, inicio)
        self.eventos: List[str] = []
        self.numero_mano = 1
        self.confirmar_salida = False

        # Entrada de texto (interprete).
        self.entrada = ""
        self.sugerencia = None                # Interpretacion aceptada, esperando Enter
        self.mensaje_entrada = ""
        pygame.key.start_text_input()

        archivo = app.robot_sim.activar_registro()
        self._evento(f"Partida real a {objetivo}. Es mano: {'G1' if robot_es_mano else 'el rival'}.")
        if archivo:
            self._evento(f"Registro: registros/{archivo.name}")

        self._armar_botones()

    # =================================================================
    #  Botones
    # =================================================================
    def _armar_botones(self):
        self.btn_menu = Boton((24, 18, 110, 38), "Menú", lambda: setattr(self, "confirmar_salida", True), "oscuro", 17, 8)
        self.btn_confirmar_cartas = Boton((CENTRO.centerx - 150, 560, 300, 52), "Confirmar cartas del G1",
                                          self._confirmar_cartas, "dorado", 20)
        self.btn_ya_tiro = Boton((CENTRO.centerx - 150, 560, 300, 58), "Listo, ya la tiró (Enter)",
                                 self._ya_tiro, "dorado", 20)
        self.btn_aplicar = Boton((CENTRO.right - 120, 648, 120, 40), "Aplicar", self._aplicar_sugerencia, "quiero", 18)
        self.btn_si = Boton((ANCHO // 2 - 150, 400, 140, 50), "Abandonar", self.app.ir_al_menu, "no_quiero", 19)
        self.btn_no = Boton((ANCHO // 2 + 10, 400, 140, 50), "Seguir", lambda: setattr(self, "confirmar_salida", False), "claro", 19)
        self.btn_revancha = Boton((ANCHO // 2 - 190, 430, 180, 54), "Otra partida",
                                  lambda: self.app.partida_real(self.objetivo, not self.robot_es_mano), "dorado", 20)
        self.btn_al_menu = Boton((ANCHO // 2 + 10, 430, 180, 54), "Menú", self.app.ir_al_menu, "claro", 22)

    def _botones_rival(self) -> List[Boton]:
        """Cantos y respuestas que el rival puede hacer ahora (solo los validos)."""
        acciones = self.partida.acciones_rival() if not self.partida.esperando_declaracion() else []
        botones, x, y = [], CENTRO.x, CENTRO.y + 56
        for a in acciones:
            if a.action_type == ActionType.PLAY_CARD:
                continue
            estilo = {"Quiero": "quiero", "No Quiero": "no_quiero", "Me voy al mazo": "oscuro"}.get(a.name, "claro")
            etiqueta = "Irse al mazo" if a.action_type == ActionType.FOLD else a.name
            w = self.rec.fuente(17, negrita=True).size(etiqueta)[0] + 30
            if x + w > CENTRO.right:
                x, y = CENTRO.x, y + 48
            botones.append(Boton((x, y, w, 40), etiqueta, lambda a=a: self._aplicar_rival(a), estilo, 17))
            x += w + 10
        return botones

    def _botones_declarar(self) -> List[Boton]:
        botones = []
        filas = [ENVIDOS_POSIBLES[:8], ENVIDOS_POSIBLES[8:15], ENVIDOS_POSIBLES[15:]]
        for f, fila in enumerate(filas):
            for c, n in enumerate(fila):
                botones.append(Boton((CENTRO.x + 20 + c * 72, CENTRO.y + 120 + f * 70, 62, 54), str(n),
                                     lambda n=n: self._declarar(n), "claro", 22))
        botones.append(Boton((CENTRO.x + 20, CENTRO.y + 340, 200, 50), "Son buenas", lambda: self._declarar(0), "oscuro", 19))
        return botones

    # =================================================================
    #  Fases
    # =================================================================
    def _fase(self) -> str:
        p = self.partida
        if p.terminada and not self.aviso and not self._cola_avisos:
            return "FINAL"
        if self.pendiente:
            return "CONFIRMAR"
        if p.necesita_cartas():
            return "REPARTO"
        if p.esperando_declaracion():
            return "DECLARAR"
        if p.turno_rival():
            return "RIVAL"
        if p.turno_robot():
            return "ROBOT"
        return "ESPERA"

    def _libre(self) -> bool:
        return self.ahora >= self.bloqueado_hasta and not self.confirmar_salida

    # =================================================================
    #  Acciones
    # =================================================================
    def _evento(self, texto_evento: str):
        self.eventos.append(f"{datetime.now():%H:%M:%S}  {texto_evento}")
        self.app.robot_sim.registrar(texto_evento)

    def _confirmar_cartas(self):
        if len(self.seleccion) != 3 or not self._libre():
            return
        try:
            self.partida.cargar_cartas_robot(self.seleccion)
        except ValueError as exc:
            self.mensaje_entrada = str(exc)
            return
        self._evento(f"Mano {self.numero_mano}: cartas del G1 {', '.join(c.name for c in self.seleccion)}")
        self.seleccion = []

    def _aplicar_rival(self, accion: Action):
        if not self._libre():
            return
        try:
            r = self.partida.aplicar(accion)
        except ValueError as exc:
            self.mensaje_entrada = str(exc)
            return
        self._evento(f"Rival: {accion.name}")
        self.entrada, self.sugerencia, self.mensaje_entrada = "", None, ""
        self._procesar(r)

    def _declarar(self, n: int):
        accion = next((a for a in self.partida.acciones_rival() if a.payload.get("envido") == n), None)
        if accion:
            self._aplicar_rival(accion)

    def _jugar_robot(self):
        r = self.partida.jugar_robot()
        self._evento(f"G1: {r.accion.name}")
        if r.accion.action_type == ActionType.PLAY_CARD:
            self.pendiente = r
        if r.accion.payload.get("bid") or r.accion.payload.get("response", "").startswith("QUIERO"):
            self.app.robot_sim.gesto("canto")
        self._procesar(r)

    def _ya_tiro(self):
        if self.pendiente:
            self._evento("Ayudante tiró la carta del G1")
            self.pendiente = None

    def _procesar(self, r: Resultado):
        if r.dice:
            self.dice = (r.dice, self.ahora)
            self.app.robot_sim.decir(r.dice)
            if not self.app.robot_sim.habla_el_robot():
                self.app.voz.decir(r.dice)

        demora = 0.0
        if r.envido:
            info = r.envido
            quien = "G1" if info["winner_id"] == self.partida.robot else "el rival"
            if info.get("accepted"):
                titulo = f"Envido: rival {info['p1_pts']} · G1 {info['p2_pts']}"
            else:
                titulo = "Envido no querido"
            self._avisar(titulo, f"Suma {quien}: +{info['points_won']}", 2.6)
            self._evento(f"{titulo} -> {quien} +{info['points_won']}")
            demora = 2.6

        if r.mano_terminada:
            quien = "G1" if r.ganador_mano == self.partida.robot else "el rival"
            n = r.puntos_mano.get(r.ganador_mano, 0)
            detalle = f"+{n} punto{'s' if n != 1 else ''}"
            if r.envido_por_mazo:
                detalle += " (uno por el envido sin jugar)"
            self._avisar(f"Mano para {quien}", detalle, 2.4, retraso=demora)
            self._evento(f"Mano {self.numero_mano} para {quien} {detalle}")
            if r.verificacion_envido:
                self._avisar("Control del envido", r.verificacion_envido, 4.0, retraso=demora + 2.4)
                self._evento(r.verificacion_envido)
            self.numero_mano += 1

        if r.partida_terminada:
            ganador = "G1" if self.partida.state.winner_id == self.partida.robot else "el rival"
            self._evento(f"FIN: gana {ganador} {self.partida.puntos()}")

    def _avisar(self, titulo: str, detalle: str, duracion: float, retraso: float = 0.0):
        inicio = self.ahora + retraso
        # Los avisos se encadenan: se guarda una cola simple.
        self._cola_avisos.append((titulo, detalle, inicio, duracion))
        self.bloqueado_hasta = max(self.bloqueado_hasta, inicio + duracion * 0.6)

    # ---------- entrada de texto ----------
    def _interpretar(self):
        if not self.entrada.strip():
            return
        validas = self.partida.acciones_rival()
        r = self.interprete.interpretar(self.entrada, validas)
        if r.aceptada:
            self.sugerencia = r
            self.mensaje_entrada = f"Entendí: {r.mensaje}. Enter para aplicar, Esc para borrar."
        else:
            self.sugerencia = None
            self.mensaje_entrada = f"[{r.intencion}] {r.mensaje}"
        self._evento(f"Interprete: '{self.entrada}' -> {r.intencion}: {r.mensaje}")

    def _aplicar_sugerencia(self):
        if self.sugerencia:
            self._aplicar_rival(self.sugerencia.accion)

    # =================================================================
    #  Ciclo
    # =================================================================
    def evento(self, e):
        if self.confirmar_salida:
            for b in (self.btn_si, self.btn_no):
                b.evento(e)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.confirmar_salida = False
            return

        fase = self._fase()
        if fase == "FINAL":
            for b in (self.btn_revancha, self.btn_al_menu):
                b.evento(e)
            return

        self.btn_menu.evento(e)
        escribe = fase in ("RIVAL", "DECLARAR")

        if e.type == pygame.TEXTINPUT and escribe:
            self.entrada += e.text
            self.sugerencia = None
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.entrada or self.sugerencia:
                    self.entrada, self.sugerencia, self.mensaje_entrada = "", None, ""
                else:
                    self.confirmar_salida = True
                return
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if fase == "CONFIRMAR":
                    self._ya_tiro()
                elif fase == "REPARTO":
                    self._confirmar_cartas()
                elif escribe:
                    if self.sugerencia:
                        self._aplicar_sugerencia()
                    else:
                        self._interpretar()
                return
            if e.key == pygame.K_BACKSPACE and escribe:
                self.entrada = self.entrada[:-1]
                self.sugerencia = None
                return

        if fase == "REPARTO":
            self.btn_confirmar_cartas.habilitado = len(self.seleccion) == 3
            if not self.btn_confirmar_cartas.evento(e) and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                carta = self._carta_en_grilla(e.pos, *self._geometria_grilla("REPARTO"))
                if carta:
                    if carta in self.seleccion:
                        self.seleccion.remove(carta)
                    elif len(self.seleccion) < 3:
                        self.seleccion.append(carta)
        elif fase == "CONFIRMAR":
            self.btn_ya_tiro.evento(e)
        elif fase == "DECLARAR":
            for b in self._botones_declarar():
                if b.evento(e):
                    return
            self.btn_aplicar.evento(e)
        elif fase == "RIVAL":
            for b in self._botones_rival():
                if b.evento(e):
                    return
            self.btn_aplicar.evento(e)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                carta = self._carta_en_grilla(e.pos, *self._geometria_grilla("RIVAL"))
                if carta:
                    accion = next((a for a in self.partida.acciones_rival()
                                   if a.action_type == ActionType.PLAY_CARD and a.payload["card"] == carta), None)
                    if accion:
                        self._aplicar_rival(accion)

    def actualizar(self, ahora: float):
        self.ahora = ahora
        # Avisos en cola.
        if self.aviso and ahora - self.aviso[2] > self.aviso[3]:
            self.aviso = None
        if not self.aviso and self._cola_avisos and self._cola_avisos[0][2] <= ahora:
            titulo, detalle, _, duracion = self._cola_avisos.pop(0)
            self.aviso = (titulo, detalle, ahora, duracion)

        if self.dice and ahora - self.dice[1] > max(5.0, len(self.dice[0]) * 0.07):
            self.dice = None

        fase = self._fase()
        if fase == "ROBOT" and self._libre() and not self._cola_avisos:
            if self.robot_juega_en is None:
                self.robot_juega_en = ahora + 1.0 + random.random() * 0.5
            elif ahora >= self.robot_juega_en:
                self.robot_juega_en = None
                self._jugar_robot()
        else:
            self.robot_juega_en = None
        self.btn_ya_tiro.habilitado = self._libre()

    # =================================================================
    #  Dibujo
    # =================================================================
    def _geometria_grilla(self, fase: str):
        if fase == "REPARTO":
            return CENTRO.x + 12, CENTRO.y + 82, 0.36, 60, 90
        return CENTRO.x + 12, CENTRO.y + 176, 0.31, 60, 82

    def _carta_en_grilla(self, pos, x0, y0, escala, paso_x, paso_y) -> Optional[Card]:
        w, h = CARTA_W * escala, CARTA_H * escala
        for i, carta in enumerate(MAZO_COMPLETO):
            fila, col = divmod(i, 10)
            cx, cy = x0 + col * paso_x + w / 2, y0 + fila * paso_y + h / 2
            if abs(pos[0] - cx) <= w / 2 and abs(pos[1] - cy) <= h / 2:
                return carta
        return None

    def _dibujar_grilla(self, pantalla, fase, habilitadas, marcadas):
        x0, y0, escala, paso_x, paso_y = self._geometria_grilla(fase)
        w, h = CARTA_W * escala, CARTA_H * escala
        for i, carta in enumerate(MAZO_COMPLETO):
            fila, col = divmod(i, 10)
            cx, cy = x0 + col * paso_x + w / 2, y0 + fila * paso_y + h / 2
            marcada = carta in marcadas
            if marcada:
                cy -= 6
            self.rec.dibujar_carta(pantalla, carta, cx, cy, escala, sombra=False,
                                   velo=carta not in habilitadas)
            if marcada:
                r = pygame.Rect(0, 0, w + 6, h + 6)
                r.center = (cx, cy)
                pygame.draw.rect(pantalla, COLOR["dorado"], r, width=3, border_radius=8)

    def dibujar(self, pantalla, ahora):
        rec = self.rec
        pantalla.blit(rec.fondo(), (0, 0))
        fase = self._fase()

        # ---------- barra superior ----------
        self.btn_menu.dibujar(pantalla, rec)
        texto(pantalla, "CARTAS REALES · pantalla del operador", rec.fuente(22, negrita=True),
              COLOR["texto"], (ANCHO // 2, 30))
        conexion = "G1 conectado" if self.app.robot_sim.conectado else "sin robot conectado"
        texto(pantalla, f"A {self.objetivo} · mano {self.numero_mano} · {conexion}", rec.fuente(15),
              COLOR["texto_suave"], (ANCHO // 2, 56))
        if self.dice:
            linea = self.dice[0].replace("\n", " / ")
            lineas = envolver(f"G1: «{linea}»", rec.fuente(18, serif=True), 900)[:2]
            for k, l in enumerate(lineas):
                texto(pantalla, l, rec.fuente(18, serif=True), COLOR["dorado"], (ANCHO // 2, 80 + k * 22))

        self._dibujar_columna_robot(pantalla)
        self._dibujar_columna_derecha(pantalla)

        # ---------- centro ----------
        panel(pantalla, CENTRO.inflate(24, 16), borde=COLOR["panel_borde"], radio=18, alfa=200, sombra=False)
        titulo_f = rec.fuente(26, negrita=True, serif=True)
        if fase == "REPARTO":
            texto(pantalla, f"Mano {self.numero_mano}: ¿qué cartas le tocaron al G1?", titulo_f,
                  COLOR["texto"], (CENTRO.centerx, CENTRO.y + 22))
            texto(pantalla, f"Tocá sus 3 cartas ({len(self.seleccion)}/3)", rec.fuente(17),
                  COLOR["texto_suave"], (CENTRO.centerx, CENTRO.y + 52))
            self._dibujar_grilla(pantalla, fase, MAZO_COMPLETO, self.seleccion)
            self.btn_confirmar_cartas.habilitado = len(self.seleccion) == 3
            self.btn_confirmar_cartas.dibujar(pantalla, rec)
            mano = "G1" if self.partida.data["mano_player_id"] == self.partida.robot else "el rival"
            texto(pantalla, f"Es mano {mano}", rec.fuente(17), COLOR["texto_suave"], (CENTRO.centerx, 640))
        elif fase == "CONFIRMAR":
            carta = self.pendiente.accion.payload["card"]
            texto(pantalla, "EL G1 TIRA", rec.fuente(34, negrita=True, serif=True), COLOR["dorado"],
                  (CENTRO.centerx, CENTRO.y + 40))
            rec.dibujar_carta(pantalla, carta, CENTRO.centerx, CENTRO.y + 240, 1.2)
            texto(pantalla, nombre_carta(carta).capitalize(), rec.fuente(28, negrita=True), COLOR["texto"],
                  (CENTRO.centerx, CENTRO.y + 410))
            self.btn_ya_tiro.dibujar(pantalla, rec)
        elif fase == "DECLARAR":
            texto(pantalla, "¿Cuántos tantos dice el rival?", titulo_f, COLOR["texto"], (CENTRO.centerx, CENTRO.y + 22))
            robot_pts = calculate_envido_points(self.partida.cartas_robot() + self.partida.data["played_cards"][self.partida.robot])
            texto(pantalla, f"El G1 tiene {robot_pts}. Tocá lo que dice el rival, o escribilo.", rec.fuente(17),
                  COLOR["texto_suave"], (CENTRO.centerx, CENTRO.y + 60))
            for b in self._botones_declarar():
                b.dibujar(pantalla, rec)
            self._dibujar_entrada(pantalla)
        elif fase == "RIVAL":
            texto(pantalla, "Turno del rival", titulo_f, COLOR["texto"], (CENTRO.centerx, CENTRO.y + 22))
            pendiente = self._canto_pendiente()
            if pendiente:
                texto(pantalla, f"El G1 cantó {pendiente}: ¿qué contesta?", rec.fuente(17, negrita=True),
                      COLOR["dorado"], (CENTRO.centerx, CENTRO.y + 46))
            for b in self._botones_rival():
                b.dibujar(pantalla, rec)
            jugables = [a.payload["card"] for a in self.partida.acciones_rival() if a.action_type == ActionType.PLAY_CARD]
            if jugables:
                texto(pantalla, "…o tocá la carta que tiró:", rec.fuente(16), COLOR["texto_suave"],
                      (CENTRO.x + 12, CENTRO.y + 154), ancla="topleft")
                self._dibujar_grilla(pantalla, fase, jugables, [])
            self._dibujar_entrada(pantalla)
        elif fase == "ROBOT":
            puntos = "." * (1 + int(ahora * 2.5) % 3)
            texto(pantalla, f"El G1 está pensando{puntos}", titulo_f, COLOR["texto"], CENTRO.center)

        if self.aviso:
            self._dibujar_aviso(pantalla)
        if fase == "FINAL":
            self._dibujar_final(pantalla)
        if self.confirmar_salida:
            self._velo(pantalla, 150)
            r = pygame.Rect(0, 0, 420, 200)
            r.center = (ANCHO // 2, 360)
            panel(pantalla, r, borde=COLOR["panel_borde"], radio=20)
            texto(pantalla, "¿Abandonar la partida?", rec.fuente(26, negrita=True, serif=True),
                  COLOR["texto"], (r.centerx, r.y + 58))
            self.btn_si.dibujar(pantalla, rec)
            self.btn_no.dibujar(pantalla, rec)

    def _canto_pendiente(self) -> Optional[str]:
        data = self.partida.data
        if data["envido_state"] == "WAITING_RESPONSE":
            return NOMBRE_CANTO[data["envido_bid_chain"][-1]]
        if data["truco_state"] == "WAITING_RESPONSE":
            return NOMBRE_CANTO[data["truco_bid_name"]]
        return None

    def _dibujar_entrada(self, pantalla):
        rec = self.rec
        caja = pygame.Rect(CENTRO.x, 648, CENTRO.w - 130, 40)
        pygame.draw.rect(pantalla, COLOR["crema"], caja, border_radius=8)
        contenido = self.entrada or "Escribí lo que dijo el rival (ej: quiero retruco, tiro el 7 de oro)"
        color = COLOR["tinta"] if self.entrada else (140, 128, 112)
        cursor = "|" if self.entrada and int(self.ahora * 2) % 2 == 0 else ""
        texto(pantalla, contenido + cursor, rec.fuente(16), color, (caja.x + 12, caja.centery), ancla="midleft")
        self.btn_aplicar.visible = self.sugerencia is not None
        self.btn_aplicar.dibujar(pantalla, rec)
        if self.mensaje_entrada:
            color = COLOR["quiero"] if self.sugerencia else (220, 150, 120)
            texto(pantalla, self.mensaje_entrada, rec.fuente(15), color, (CENTRO.x, 700), ancla="midleft")

    def _dibujar_columna_robot(self, pantalla):
        rec = self.rec
        p = self.partida
        x0 = 24
        texto(pantalla, "CARTAS DEL G1", rec.fuente(14, negrita=True), COLOR["texto_suave"], (x0, 112), ancla="topleft")
        cartas = p.cartas_robot() if p.cartas_cargadas else []
        a_tirar = self.pendiente.accion.payload["card"] if self.pendiente else None
        for i in range(3):
            cx, cy = x0 + 62 + i * 128, 222
            if i < len(cartas):
                rec.dibujar_carta(pantalla, cartas[i], cx, cy, 0.62)
            else:
                r = pygame.Rect(0, 0, CARTA_W * 0.62, CARTA_H * 0.62)
                r.center = (cx, cy)
                pygame.draw.rect(pantalla, (60, 52, 46), r, width=2, border_radius=10)
        if a_tirar:
            texto(pantalla, f"Tirar: {nombre_carta(a_tirar)}", rec.fuente(17, negrita=True), COLOR["dorado"],
                  (x0, 316), ancla="topleft")
        elif p.cartas_cargadas and p.data["envido_state"] == "UNOPENED":
            pts = calculate_envido_points(p.cartas_robot())
            texto(pantalla, f"Envido del G1: {pts}", rec.fuente(15), COLOR["texto_suave"], (x0, 316), ancla="topleft")

        texto(pantalla, "MESA", rec.fuente(14, negrita=True), COLOR["texto_suave"], (x0, 352), ancla="topleft")
        f = rec.fuente(15)
        texto(pantalla, "G1", f, COLOR["texto_suave"], (x0 + 132, 374))
        texto(pantalla, "Rival", f, COLOR["texto_suave"], (x0 + 220, 374))
        for i, baza in enumerate(p.bazas() if p.cartas_cargadas or self.pendiente else []):
            y = 432 + i * 104
            texto(pantalla, f"Baza {i + 1}", f, COLOR["texto_suave"], (x0, y), ancla="midleft")
            for clave, x in (("robot", x0 + 132), ("rival", x0 + 220)):
                if baza[clave]:
                    rec.dibujar_carta(pantalla, baza[clave], x, y, 0.38, sombra=False)
            if baza["ganador"]:
                quien = {p.robot: "G1", p.rival: "Rival"}.get(baza["ganador"], "Parda")
                texto(pantalla, quien, rec.fuente(16, negrita=True), COLOR["dorado"], (x0 + 300, y), ancla="midleft")

    def _dibujar_columna_derecha(self, pantalla):
        rec = self.rec
        alto = anotador.alto_necesario(self.objetivo)
        rect = pygame.Rect(1072, 104, 188, alto)
        puntos = self.partida.puntos()
        anotador.dibujar(pantalla, rec, rect, ("Rival", "G1"),
                         (puntos[self.partida.rival], puntos[self.partida.robot]), self.objetivo)
        y = rect.bottom + 22
        texto(pantalla, "REGISTRO", rec.fuente(13, negrita=True), COLOR["texto_suave"], (1072, y), ancla="topleft")
        y += 22
        f = rec.fuente(12)
        disponibles = (ALTO - 12 - y) // 17
        lineas = []
        for ev in self.eventos:
            lineas.extend(envolver(ev, f, 188))
        for linea in lineas[-max(0, disponibles):]:
            texto(pantalla, linea, f, COLOR["texto_suave"], (1072, y), ancla="topleft")
            y += 17

    def _dibujar_aviso(self, pantalla):
        titulo, detalle, inicio, duracion = self.aviso
        t = self.ahora - inicio
        alfa = max(0.0, min(1.0, t / 0.2, (duracion - t) / 0.3))
        dy = (1 - salir(min(1.0, t / 0.3))) * 16
        capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        f_det = self.rec.fuente(19)
        lineas = envolver(detalle, f_det, 540)
        r = pygame.Rect(0, 0, 600, 80 + 28 * len(lineas))
        r.center = (CENTRO.centerx, 360 + dy)
        panel(capa, r, borde=COLOR["dorado"], radio=16, alfa=245)
        texto(capa, titulo, self.rec.fuente(28, negrita=True, serif=True), COLOR["texto"], (r.centerx, r.y + 38))
        for k, l in enumerate(lineas):
            texto(capa, l, f_det, COLOR["dorado"], (r.centerx, r.y + 78 + k * 28))
        capa.set_alpha(int(255 * alfa))
        pantalla.blit(capa, (0, 0))

    def _velo(self, pantalla, alfa=170):
        v = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        v.fill((10, 8, 6, alfa))
        pantalla.blit(v, (0, 0))

    def _dibujar_final(self, pantalla):
        self._velo(pantalla)
        gano_robot = self.partida.state.winner_id == self.partida.robot
        r = pygame.Rect(0, 0, 520, 300)
        r.center = (ANCHO // 2, 360)
        panel(pantalla, r, borde=COLOR["dorado"], radio=24)
        titulo = "Ganó el G1" if gano_robot else "¡Ganó el rival!"
        texto(pantalla, titulo, self.rec.fuente(52, negrita=True, serif=True), COLOR["dorado"], (r.centerx, r.y + 80))
        puntos = self.partida.puntos()
        texto(pantalla, f"Rival {puntos[self.partida.rival]}  ·  G1 {puntos[self.partida.robot]}",
              self.rec.fuente(26), COLOR["texto"], (r.centerx, r.y + 150))
        self.btn_revancha.dibujar(pantalla, self.rec)
        self.btn_al_menu.dibujar(pantalla, self.rec)
