"""La mesa: vos abajo, el G1 enfrente, y el anotador a un costado.

Esta escena solo DIBUJA y ANIMA. Las reglas son de `TrucoGame` y las
decisiones del robot de `HeuristicTrucoAgent`, los mismos que usaria el G1
real. Por eso la mesa lleva su propio "modelo visual" (que cartas se ven en
cada mano y en la mesa): el motor reparte la mano nueva en el mismo instante
en que termina la anterior, y la pantalla tiene que mostrar el final antes de
limpiar.
"""

import random
from typing import Callable, Dict, List, Optional

import pygame

from card_framework.agents.heuristic_truco_agent import HeuristicTrucoAgent
from card_framework.core.action import Action, ActionType
from card_framework.core.card import Card
from card_framework.games.truco.truco_deck import calculate_envido_points
from card_framework.games.truco.truco_game import TrucoGame
from card_framework.interfaces import frases_robot
from card_framework.interfaces.frases_robot import NOMBRE_CANTO
from card_framework.interfaces.mesa import anotador
from card_framework.interfaces.mesa.recursos import ALTO, ANCHO, CARTA_H, CARTA_W, COLOR, esquinas, rotar_punto
from card_framework.interfaces.mesa.widgets import Boton, Globo, mezclar, panel, salir, suavizar, texto

# Probabilidad de que el robot "mienta": que cante o acepte sin tener con que.
FAROL = 0.5

NOMBRE_ROBOT = "G1"

# ---------- geometria de la mesa ----------
MESA = [(300, 296), (980, 296), (1132, 626), (148, 626)]
MAZO = (1000, 430)

# Hueco de cada baza: x por columna, y de la fila, angulo por columna, escala, aplastado.
HUECOS = {
    "robot": {"xs": (478, 645, 812), "y": 372, "angulos": (-7, 0, 7), "escala": 0.5, "aplastar": 0.88},
    "yo": {"xs": (450, 645, 840), "y": 500, "angulos": (-11, 0, 11), "escala": 0.56, "aplastar": 0.9},
}
MANO = {
    "robot": {"x": 645, "y": 206, "escala": 0.5, "paso": 58, "caida": 7},
    "yo": {"x": 645, "y": 660, "escala": 0.82, "paso": 112, "caida": 16},
}
ANGULOS_ABANICO = {1: (0,), 2: (7, -7), 3: (13, 0, -13)}

PANEL_RESPUESTA = pygame.Rect(1072, 0, 188, 150)  # la y se acomoda bajo el anotador


class CartaVolando:
    """Una carta en viaje: de la mano a la mesa, o del mazo a la mano."""

    def __init__(self, carta: Optional[Card], desde: dict, hasta: dict, inicio: float,
                 duracion: float, girar: bool = False, al_llegar: Optional[Callable] = None):
        self.carta = carta
        self.desde, self.hasta = desde, hasta
        self.inicio, self.duracion = inicio, duracion
        self.girar = girar          # se da vuelta en el aire (reverso -> cara)
        self.al_llegar = al_llegar
        self.terminada = False

    def pose(self, ahora: float) -> dict:
        p = suavizar((ahora - self.inicio) / self.duracion)
        pose = {k: mezclar(self.desde[k], self.hasta[k], p) for k in ("x", "y", "angulo", "escala", "aplastar")}
        pose["y"] -= 38 * (1 - (2 * p - 1) ** 2)  # un arco: la carta se levanta al tirarla
        pose["cara"] = True
        pose["ancho_giro"] = 1.0
        if self.girar:
            pose["ancho_giro"] = max(0.02, abs(1 - 2 * p))
            pose["cara"] = p >= 0.5
        return pose

    def actualizar(self, ahora: float) -> None:
        if not self.terminada and ahora - self.inicio >= self.duracion:
            self.terminada = True
            if self.al_llegar:
                self.al_llegar()


class EscenaPartida:
    def __init__(self, app, objetivo: int):
        self.app = app
        self.rec = app.recursos
        self.objetivo = objetivo

        self.game = TrucoGame(p1_name="Nos", p2_name=NOMBRE_ROBOT, target_score=objetivo)
        self.bot = HeuristicTrucoAgent(name=NOMBRE_ROBOT, bluff_frequency=FAROL)
        self.state = self.game.reset()
        self.yo, self.rob = self.game.p1_id, self.game.p2_id

        # Modelo visual.
        self.manos: Dict[str, List[Card]] = {self.yo: [], self.rob: []}
        self.repartidas = {self.yo: 0, self.rob: 0}
        self.mesa: Dict[str, List[Card]] = {self.yo: [], self.rob: []}
        self.poses: Dict[tuple, dict] = {}
        self.volando: List[CartaVolando] = []
        self.agenda: List[tuple] = []           # (cuando, funcion)
        self.globos: Dict[str, Optional[Globo]] = {self.yo: None, self.rob: None}
        self.aviso = None                       # (titulo, detalle, inicio, duracion)
        self.bloqueado_hasta = 0.0
        self.bot_juega_en: Optional[float] = None
        self.hover: Optional[Card] = None
        self.ver_cartas_robot = False
        self.final = False
        self.confirmar_salida = False
        self.ahora = 0.0

        self._armar_botones()
        self._repartir(0.0)

    # =================================================================
    #  Botones
    # =================================================================
    def _armar_botones(self):
        x, w, h = 24, 176, 46
        self.btn_menu = Boton((24, 18, 110, 38), "Menú", self._pedir_salida, "oscuro", 17, 8)
        self.btn_envido = Boton((x, 196, w, h), "Envido", lambda: self._jugar_por_nombre("Envido"))
        self.btn_real = Boton((x, 252, w, h), "Real envido", lambda: self._jugar_por_nombre("Real Envido"), tam=18)
        self.btn_falta = Boton((x, 308, w, h), "Falta envido", lambda: self._jugar_por_nombre("Falta Envido"), tam=18)
        self.btn_truco = Boton((x, 384, w, h), "Truco", self._jugar_truco, "dorado")
        self.btn_mazo = Boton((x, 460, w, h), "Irse al mazo", lambda: self._jugar_por_nombre("Me voy al mazo"), "oscuro", 18)

        alto_anotador = anotador.alto_necesario(self.objetivo)
        self.rect_anotador = pygame.Rect(1072, 22, 188, alto_anotador)
        self.rect_respuesta = PANEL_RESPUESTA.move(0, self.rect_anotador.bottom + 22)
        r = self.rect_respuesta
        self.btn_quiero = Boton((r.x + 14, r.y + 66, r.w - 28, 34), "Quiero", lambda: self._responder(True), "quiero", 18)
        self.btn_no_quiero = Boton((r.x + 14, r.y + 108, r.w - 28, 34), "No quiero", lambda: self._responder(False), "no_quiero", 18)

        self.btn_revancha = Boton((ANCHO // 2 - 190, 430, 180, 54), "Revancha",
                                  lambda: self.app.nueva_partida(self.objetivo), "dorado", 22)
        self.btn_al_menu = Boton((ANCHO // 2 + 10, 430, 180, 54), "Menú", self.app.ir_al_menu, "claro", 22)
        self.btn_si = Boton((ANCHO // 2 - 150, 400, 140, 50), "Abandonar", self.app.ir_al_menu, "no_quiero", 19)
        self.btn_no = Boton((ANCHO // 2 + 10, 400, 140, 50), "Seguir", self._cancelar_salida, "claro", 19)

    def _botones_juego(self):
        return [self.btn_envido, self.btn_real, self.btn_falta, self.btn_truco, self.btn_mazo,
                self.btn_quiero, self.btn_no_quiero]

    def _refrescar_botones(self):
        acciones = self._acciones_mias() if self._puedo_actuar() else []
        nombres = {a.name for a in acciones}
        self.btn_envido.habilitado = "Envido" in nombres
        self.btn_real.habilitado = "Real Envido" in nombres
        self.btn_falta.habilitado = "Falta Envido" in nombres
        self.btn_mazo.habilitado = "Me voy al mazo" in nombres

        truco = next((a for a in acciones if a.payload.get("bid") in ("TRUCO", "RETRUCO", "VALE_CUATRO")), None)
        self.btn_truco.habilitado = truco is not None
        self.btn_truco.etiqueta = truco.name if truco else self._proximo_truco()

        responder = "Quiero" in nombres
        self.btn_quiero.visible = self.btn_no_quiero.visible = responder

    def _proximo_truco(self) -> str:
        data = self.state.game_data
        if data["truco_state"] == "WAITING_RESPONSE":
            actual = data["truco_bid_name"]
        else:
            actual = data["truco_state"]
        return {"NONE": "Truco", "TRUCO": "Retruco"}.get(actual, "Vale Cuatro")

    # =================================================================
    #  Turnos
    # =================================================================
    def _ocupado(self) -> bool:
        return bool(self.volando or self.agenda or self.final or self.ahora < self.bloqueado_hasta)

    def _puedo_actuar(self) -> bool:
        return not self._ocupado() and not self.confirmar_salida and self.state.current_player_id == self.yo

    def _acciones_mias(self) -> List[Action]:
        return self.game.get_valid_actions(self.state, self.yo)

    def _jugar_por_nombre(self, nombre: str):
        if not self._puedo_actuar():
            return
        accion = next((a for a in self._acciones_mias() if a.name == nombre), None)
        if accion:
            self._aplicar(accion)

    def _jugar_truco(self):
        if not self._puedo_actuar():
            return
        accion = next((a for a in self._acciones_mias()
                       if a.payload.get("bid") in ("TRUCO", "RETRUCO", "VALE_CUATRO")), None)
        if accion:
            self._aplicar(accion)

    def _responder(self, quiero: bool):
        self._jugar_por_nombre("Quiero" if quiero else "No Quiero")

    def _jugar_carta(self, carta: Card):
        if not self._puedo_actuar():
            return
        accion = next((a for a in self._acciones_mias()
                       if a.action_type == ActionType.PLAY_CARD and a.payload["card"] == carta), None)
        if accion:
            self._aplicar(accion)

    def _turno_del_robot(self):
        if self._ocupado() or self.confirmar_salida or self.state.current_player_id != self.rob:
            self.bot_juega_en = None
            return
        if self.bot_juega_en is None:
            # Un momento para "pensar": mas largo si tiene que contestar un canto.
            data = self.state.game_data
            contestando = "WAITING_RESPONSE" in (data["envido_state"], data["truco_state"])
            self.bot_juega_en = self.ahora + (1.3 if contestando else 0.85) + random.random() * 0.4
            return
        if self.ahora < self.bot_juega_en:
            return
        self.bot_juega_en = None
        acciones = self.game.get_valid_actions(self.state, self.rob)
        if acciones:
            obs = self.game.get_player_observation(self.state, self.rob)
            self._aplicar(self.bot.select_action(obs, acciones))

    # =================================================================
    #  Aplicar una accion: motor + lo que se ve
    # =================================================================
    def _aplicar(self, accion: Action):
        pid = accion.player_id
        data = self.state.game_data
        puntos_antes = {p: self.state.players[p].score for p in (self.yo, self.rob)}
        cadena_envido = list(data["envido_bid_chain"])
        truco_cantado = data.get("truco_bid_name")

        if accion.action_type == ActionType.PLAY_CARD:
            self._tirar_carta(pid, accion.payload["card"])

        self.state, _, _ = self.game.step(self.state, accion)
        data = self.state.game_data

        self._hablar(pid, accion, cadena_envido, truco_cantado)

        # Resultado del envido.
        if data["envido_just_resolved"]:
            info = data["envido_resolved_info"]
            suma = f"Vos sumás {info['points_won']}" if info["winner_id"] == self.yo                 else f"{NOMBRE_ROBOT} suma {info['points_won']}"
            if info["accepted"]:
                mios, suyos = info["p1_pts"], info["p2_pts"]
                gano_robot = info["winner_id"] == self.rob
                self._decir(self.rob, f"{suyos} son mejores." if gano_robot else "Son buenas.", retraso=0.9)
                self._avisar(f"Envido: vos {mios} · {NOMBRE_ROBOT} {suyos}",
                             suma, 2.6, retraso=0.5)
            else:
                self._avisar("No quiso el envido", suma, 1.8, retraso=0.4)

        if data["hand_just_finished"] or self.state.is_terminal:
            self._cerrar_mano(puntos_antes, data["hand_just_finished"], data.get("envido_por_mazo", 0))

    def _tirar_carta(self, pid: str, carta: Card):
        lado = "yo" if pid == self.yo else "robot"
        desde = self.poses.get((pid, carta)) or self._pose_mano(pid, self.manos[pid].index(carta), len(self.manos[pid]))
        self.manos[pid].remove(carta)
        self.repartidas[pid] -= 1

        indice = len(self.mesa[pid]) + sum(1 for v in self.volando if v.hasta.get("pid") == pid)
        h = HUECOS[lado]
        hasta = {"x": h["xs"][indice], "y": h["y"], "angulo": h["angulos"][indice],
                 "escala": h["escala"], "aplastar": h["aplastar"], "pid": pid}
        desde = dict(desde, aplastar=1.0)
        girar = pid == self.rob and not self.ver_cartas_robot
        self.volando.append(CartaVolando(carta, desde, hasta, self.ahora, 0.42, girar,
                                         al_llegar=lambda: self.mesa[pid].append(carta)))

    def _hablar(self, pid: str, accion: Action, cadena_envido: list, truco_cantado: Optional[str]):
        bid = accion.payload.get("bid")
        respuesta = accion.payload.get("response")
        es_robot = pid == self.rob

        if bid:
            if es_robot:
                # Casi siempre canta derecho; de vez en cuando se luce con un verso.
                self._decir(pid, frases_robot.frase(accion))
                self.app.robot_sim.gesto("canto")
            else:
                self._decir(pid, f"¡{NOMBRE_CANTO[bid]}!")
        elif respuesta:
            if respuesta.startswith("QUIERO"):
                self._decir(pid, "¡Quiero!")
                if es_robot:
                    self.app.robot_sim.gesto("canto")
            else:
                self._decir(pid, "No quiero.")
        elif accion.action_type == ActionType.FOLD:
            self._decir(pid, "Me voy al mazo.")
            if es_robot:
                self.app.robot_sim.gesto("mazo")

    def _decir(self, pid: str, contenido: str, retraso: float = 0.0):
        def _mostrar():
            self.globos[pid] = Globo(contenido, self.ahora)
            if pid == self.rob:
                self.app.voz.decir(contenido)
        if retraso:
            self.agenda.append((self.ahora + retraso, _mostrar))
        else:
            _mostrar()

    def _avisar(self, titulo: str, detalle: str, duracion: float, retraso: float = 0.0):
        def _mostrar():
            self.aviso = (titulo, detalle, self.ahora, duracion)
            self.bloqueado_hasta = max(self.bloqueado_hasta, self.ahora + duracion * 0.7)
        self.agenda.append((self.ahora + retraso, _mostrar))

    def _cerrar_mano(self, puntos_antes: dict, mano_terminada: bool, envido_por_mazo: int = 0):
        ganador_id = self.state.game_data["last_hand_winner_id"]
        terminal = self.state.is_terminal

        def _anunciar():
            ganados = {p: self.state.players[p].score - puntos_antes[p] for p in (self.yo, self.rob)}
            if mano_terminada:
                quien = "vos" if ganador_id == self.yo else NOMBRE_ROBOT
                n = ganados[ganador_id]
                detalle = f"+{n} punto{'s' if n != 1 else ''}"
                if envido_por_mazo:
                    detalle += " (uno por el envido sin jugar)"
                self.aviso = (f"Mano para {quien}", detalle, self.ahora, 2.2 if envido_por_mazo else 1.9)
                self.bloqueado_hasta = self.ahora + 1.9
            if terminal:
                # Si la partida la cerro un envido, se deja leer su resultado.
                self.agenda.append((self.ahora + (2.0 if mano_terminada else 2.4), self._terminar))
            else:
                self.agenda.append((self.ahora + 2.0, lambda: self._repartir(self.ahora)))

        # Primero que aterricen las cartas en el aire.
        espera = max((v.inicio + v.duracion for v in self.volando), default=self.ahora) - self.ahora
        self.agenda.append((self.ahora + espera + 0.7, _anunciar))

    def _terminar(self):
        self.final = True
        gane = self.state.winner_id == self.yo
        self.app.voz.decir("Me ganaste. Bien jugado." if gane else "Te gané. ¿La revancha?")

    def _repartir(self, ahora: float):
        """Limpia la mesa y reparte con animacion desde el mazo."""
        self.mesa = {self.yo: [], self.rob: []}
        self.poses.clear()
        self.globos = {self.yo: None, self.rob: None}
        for pid in (self.yo, self.rob):
            self.manos[pid] = list(self.state.players[pid].hand)
            self.repartidas[pid] = 0

        mano = self.state.game_data["mano_player_id"]
        self.mano_visible = mano   # el HUD no se adelanta a la mano siguiente
        orden = [mano, self.rob if mano == self.yo else self.yo]
        t = ahora + 0.2
        for i in range(3):
            for pid in orden:
                destino = self._pose_mano(pid, i, 3)
                desde = {"x": MAZO[0], "y": MAZO[1], "angulo": 90, "escala": 0.42, "aplastar": 1.0}
                # Las del robot viajan boca abajo (carta None = reverso).
                boca_arriba = pid == self.yo or self.ver_cartas_robot
                carta = self.manos[pid][i] if boca_arriba else None
                v = CartaVolando(carta, desde, destino, t, 0.34, boca_arriba,
                                 al_llegar=lambda p=pid: self._llego_al_abanico(p))
                self.volando.append(v)
                t += 0.11

    def _llego_al_abanico(self, pid):
        self.repartidas[pid] += 1

    # =================================================================
    #  Posiciones
    # =================================================================
    def _pose_mano(self, pid: str, i: int, n: int) -> dict:
        m = MANO["yo" if pid == self.yo else "robot"]
        centro = (n - 1) / 2
        return {
            "x": m["x"] + (i - centro) * m["paso"],
            "y": m["y"] + abs(i - centro) * m["caida"],
            "angulo": ANGULOS_ABANICO[n][i] if n in ANGULOS_ABANICO else 0,
            "escala": m["escala"],
            "aplastar": 1.0,
        }

    def _objetivo_mano(self, pid: str, i: int, carta: Card) -> dict:
        pose = self._pose_mano(pid, i, len(self.manos[pid]))
        if pid == self.yo and carta == self.hover and self._puedo_actuar():
            pose["y"] -= 34
        return pose

    def _carta_bajo_el_mouse(self, pos) -> Optional[Card]:
        mano = self.manos[self.yo][:self.repartidas[self.yo]]
        for carta in reversed(mano):      # la de mas a la derecha esta encima
            p = self.poses.get((self.yo, carta))
            if not p:
                continue
            lx, ly = rotar_punto(pos[0] - p["x"], pos[1] - p["y"], -p["angulo"])
            if abs(lx) <= CARTA_W * p["escala"] / 2 and abs(ly) <= CARTA_H * p["escala"] / 2:
                return carta
        return None

    # =================================================================
    #  Ciclo
    # =================================================================
    def _pedir_salida(self):
        if not self.final:
            self.confirmar_salida = True

    def _cancelar_salida(self):
        self.confirmar_salida = False

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.final:
                    self.app.ir_al_menu()
                else:
                    self.confirmar_salida = not self.confirmar_salida
            elif e.key == pygame.K_d:
                self.ver_cartas_robot = not self.ver_cartas_robot
            elif e.key == pygame.K_m:
                self.app.voz.alternar()
            return

        if self.final:
            for b in (self.btn_revancha, self.btn_al_menu):
                b.evento(e)
            return
        if self.confirmar_salida:
            for b in (self.btn_si, self.btn_no):
                b.evento(e)
            return

        self.btn_menu.evento(e)
        for b in self._botones_juego():
            if b.evento(e):
                return
        if e.type == pygame.MOUSEMOTION:
            self.hover = self._carta_bajo_el_mouse(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            carta = self._carta_bajo_el_mouse(e.pos)
            if carta:
                self.hover = None
                self._jugar_carta(carta)

    def actualizar(self, ahora: float):
        self.ahora = ahora

        for v in list(self.volando):
            v.actualizar(ahora)
            if v.terminada:
                self.volando.remove(v)

        pendientes = sorted(self.agenda, key=lambda x: x[0])
        self.agenda = []
        for cuando, funcion in pendientes:
            if cuando <= ahora:
                funcion()
            else:
                self.agenda.append((cuando, funcion))

        # Las cartas de la mano se deslizan hacia su lugar.
        for pid in (self.yo, self.rob):
            for i, carta in enumerate(self.manos[pid][:self.repartidas[pid]]):
                objetivo = self._objetivo_mano(pid, i, carta)
                actual = self.poses.get((pid, carta))
                if actual is None:
                    self.poses[(pid, carta)] = objetivo
                else:
                    for k in ("x", "y", "angulo", "escala"):
                        actual[k] = mezclar(actual[k], objetivo[k], 0.22)

        for pid, g in self.globos.items():
            if g and not g.vivo(ahora):
                self.globos[pid] = None
        if self.aviso and ahora - self.aviso[2] > self.aviso[3]:
            self.aviso = None

        self._turno_del_robot()
        self._refrescar_botones()

    # =================================================================
    #  Dibujo
    # =================================================================
    def dibujar(self, pantalla: pygame.Surface, ahora: float):
        rec = self.rec
        pantalla.blit(rec.fondo(), (0, 0))
        self._dibujar_mesa(pantalla)
        self._dibujar_mazo(pantalla)
        self._dibujar_bazas(pantalla)
        self._dibujar_mano(pantalla, self.rob, cara=self.ver_cartas_robot)
        for v in self.volando:
            if ahora >= v.inicio:
                p = v.pose(ahora)
                rec.dibujar_carta(pantalla, v.carta if p["cara"] else None, p["x"], p["y"], p["escala"],
                                  p["angulo"], p["aplastar"], p["ancho_giro"])
        self._dibujar_mano(pantalla, self.yo, cara=True)
        self._dibujar_hud(pantalla)

        if self.globos[self.rob]:
            self.globos[self.rob].dibujar(pantalla, rec, (760, 58), 290, ahora, "izquierda")
        if self.globos[self.yo]:
            self.globos[self.yo].dibujar(pantalla, rec, (455, 592), 200, ahora, "derecha")

        if self.aviso:
            self._dibujar_aviso(pantalla)
        if self.final:
            self._dibujar_final(pantalla)
        elif self.confirmar_salida:
            self._dibujar_confirmacion(pantalla)

    def _dibujar_mesa(self, pantalla):
        # La mesa no cambia: se arma una vez y despues solo se copia.
        capa = self.rec._bases.get("mesa")
        if capa is None:
            capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            self._armar_mesa(capa)
            capa = capa.convert_alpha()
            self.rec._bases["mesa"] = capa
        pantalla.blit(capa, (0, 0))

    def _armar_mesa(self, pantalla):
        mesa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        borde = [(x + dx, y + dy) for (x, y), (dx, dy) in zip(MESA, ((-14, -12), (14, -12), (22, 14), (-22, 14)))]
        pygame.draw.polygon(mesa, COLOR["madera_oscura"], [(x, y + 10) for x, y in borde])
        pygame.draw.polygon(mesa, COLOR["madera"], borde)
        pygame.draw.polygon(mesa, COLOR["pano"], MESA)

        # Degradado del pano: mas claro al fondo, donde pega la luz.
        top, bottom = MESA[0][1], MESA[2][1]
        grad = pygame.Surface((ANCHO, bottom - top), pygame.SRCALPHA)
        for y in range(bottom - top):
            p = y / (bottom - top)
            c = [int(mezclar(a, b, p)) for a, b in zip(COLOR["pano_claro"], COLOR["pano_oscuro"])]
            pygame.draw.line(grad, c, (0, y), (ANCHO, y))
        mascara = pygame.Surface((ANCHO, bottom - top), pygame.SRCALPHA)
        pygame.draw.polygon(mascara, (255, 255, 255, 255), [(x, y - top) for x, y in MESA])
        grad.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        mesa.blit(grad, (0, top))
        pygame.draw.aalines(mesa, COLOR["madera_oscura"], True, MESA)
        pantalla.blit(mesa, (0, 0))

        # Huecos de las bazas, con borde punteado.
        huecos = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        for lado in ("robot", "yo"):
            h = HUECOS[lado]
            for x, ang in zip(h["xs"], h["angulos"]):
                w = CARTA_W * h["escala"] + 10
                alto = CARTA_H * h["escala"] * h["aplastar"] + 10
                puntos = esquinas(x, h["y"], w, alto, ang)
                pygame.draw.polygon(huecos, (*COLOR["hueco"], 40), puntos)
                _punteado(huecos, (*COLOR["hueco"], 150), puntos)
        pantalla.blit(huecos, (0, 0))

    def _dibujar_mazo(self, pantalla):
        for i in range(3):
            self.rec.dibujar_carta(pantalla, None, MAZO[0] + i * 1.5, MAZO[1] - i * 2.5, 0.42, 90, sombra=i == 0)

    def _dibujar_bazas(self, pantalla):
        mias, suyas = self.mesa[self.yo], self.mesa[self.rob]
        for lado, pid in (("robot", self.rob), ("yo", self.yo)):
            h = HUECOS[lado]
            for i, carta in enumerate(self.mesa[pid]):
                perdio = False
                if i < len(mias) and i < len(suyas):
                    propia, ajena = (mias[i], suyas[i]) if pid == self.yo else (suyas[i], mias[i])
                    perdio = propia.rank < ajena.rank
                self.rec.dibujar_carta(pantalla, carta, h["xs"][i], h["y"], h["escala"], h["angulos"][i],
                                       h["aplastar"], velo=perdio)

    def _dibujar_mano(self, pantalla, pid: str, cara: bool):
        for carta in self.manos[pid][:self.repartidas[pid]]:
            p = self.poses.get((pid, carta))
            if p:
                self.rec.dibujar_carta(pantalla, carta if cara else None, p["x"], p["y"], p["escala"], p["angulo"])

    def _dibujar_hud(self, pantalla):
        rec = self.rec
        data = self.state.game_data

        # Arriba al centro: de quien es el turno.
        if self.final:
            estado = ""
        elif self._ocupado():
            estado = ""
        elif self.state.current_player_id == self.yo:
            estado = "Te toca contestar" if self.btn_quiero.visible else "Tu turno"
        else:
            puntos = "." * (1 + int(self.ahora * 2.5) % 3)
            estado = f"{NOMBRE_ROBOT} está pensando{puntos}"
        if estado:
            texto(pantalla, estado, rec.fuente(22, negrita=True), COLOR["texto"], (ANCHO // 2, 36))

        # Placa del robot.
        conectado = self.app.robot_sim.conectado
        texto(pantalla, "UNITREE G1", rec.fuente(14, negrita=True), COLOR["texto_suave"], (ANCHO // 2, 84))
        if conectado:
            pygame.draw.circle(pantalla, (96, 200, 110), (ANCHO // 2 - 52, 84), 4)

        # Izquierda: menu, info y cantos.
        self.btn_menu.dibujar(pantalla, rec)
        mano = "vos" if self.mano_visible == self.yo else NOMBRE_ROBOT
        texto(pantalla, f"A {self.objetivo} · es mano {mano}", rec.fuente(16), COLOR["texto_suave"],
              (24, 76), ancla="topleft")
        valor = data["truco_value"]
        texto(pantalla, f"La mano vale {valor}", rec.fuente(16), COLOR["texto_suave"], (24, 100), ancla="topleft")

        texto(pantalla, "CANTOS", rec.fuente(13, negrita=True), COLOR["texto_suave"], (24, 170), ancla="topleft")
        for b in self._botones_juego()[:5]:
            b.dibujar(pantalla, rec)

        # Se calcula sobre las cartas que se VEN: el motor ya puede tener repartida la mano siguiente.
        mis_cartas = self.manos[self.yo]
        if (data["envido_state"] == "UNOPENED" and data["truco_state"] in ("NONE", "WAITING_RESPONSE")
                and len(mis_cartas) == 3 and self.repartidas[self.yo] == 3 and not self.mesa[self.yo]
                and not self.agenda):
            mis_puntos = calculate_envido_points(mis_cartas)
            texto(pantalla, f"Tenés {mis_puntos} de envido", rec.fuente(16, serif=True), COLOR["dorado"],
                  (24, 530), ancla="topleft")

        # Derecha: anotador y respuesta pendiente.
        anotador.dibujar(pantalla, rec, self.rect_anotador, ("Nos", NOMBRE_ROBOT),
                         (self.state.players[self.yo].score, self.state.players[self.rob].score), self.objetivo)
        if self.btn_quiero.visible:
            r = self.rect_respuesta
            panel(pantalla, r, borde=COLOR["dorado"], radio=12)
            texto(pantalla, f"{NOMBRE_ROBOT} cantó", rec.fuente(15), COLOR["texto_suave"], (r.centerx, r.y + 20))
            texto(pantalla, self._canto_pendiente(), rec.fuente(22, negrita=True, serif=True), COLOR["dorado"],
                  (r.centerx, r.y + 44))
            self.btn_quiero.dibujar(pantalla, rec)
            self.btn_no_quiero.dibujar(pantalla, rec)

        ayuda = f"D: ver cartas del robot · M: voz {'sí' if self.app.voz.activa else 'no'} · Esc: menú"
        texto(pantalla, ayuda, rec.fuente(13), (120, 110, 98), (ANCHO - 20, ALTO - 16), ancla="midright")

    def _canto_pendiente(self) -> str:
        data = self.state.game_data
        if data["envido_state"] == "WAITING_RESPONSE":
            return NOMBRE_CANTO[data["envido_bid_chain"][-1]]
        return NOMBRE_CANTO.get(data["truco_bid_name"], "")

    def _dibujar_aviso(self, pantalla):
        titulo, detalle, inicio, duracion = self.aviso
        t = self.ahora - inicio
        alfa = max(0.0, min(1.0, t / 0.2, (duracion - t) / 0.3))
        dy = (1 - salir(min(1.0, t / 0.3))) * 16
        capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        r = pygame.Rect(0, 0, 470, 108)
        r.center = (ANCHO // 2 + 5, 436 + dy)
        panel(capa, r, borde=COLOR["dorado"], radio=16, alfa=240)
        texto(capa, titulo, self.rec.fuente(28, negrita=True, serif=True), COLOR["texto"], (r.centerx, r.y + 38))
        texto(capa, detalle, self.rec.fuente(19), COLOR["dorado"], (r.centerx, r.y + 78))
        capa.set_alpha(int(255 * alfa))
        pantalla.blit(capa, (0, 0))

    def _velo(self, pantalla, alfa=170):
        v = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        v.fill((10, 8, 6, alfa))
        pantalla.blit(v, (0, 0))

    def _dibujar_final(self, pantalla):
        self._velo(pantalla)
        gane = self.state.winner_id == self.yo
        r = pygame.Rect(0, 0, 520, 300)
        r.center = (ANCHO // 2, 360)
        panel(pantalla, r, borde=COLOR["dorado"], radio=24)
        titulo = "¡Ganaste!" if gane else f"Ganó el {NOMBRE_ROBOT}"
        texto(pantalla, titulo, self.rec.fuente(52, negrita=True, serif=True), COLOR["dorado"], (r.centerx, r.y + 80))
        yo, rob = self.state.players[self.yo].score, self.state.players[self.rob].score
        texto(pantalla, f"Nos {yo}  ·  {NOMBRE_ROBOT} {rob}", self.rec.fuente(26), COLOR["texto"], (r.centerx, r.y + 150))
        self.btn_revancha.dibujar(pantalla, self.rec)
        self.btn_al_menu.dibujar(pantalla, self.rec)

    def _dibujar_confirmacion(self, pantalla):
        self._velo(pantalla, 150)
        r = pygame.Rect(0, 0, 420, 200)
        r.center = (ANCHO // 2, 360)
        panel(pantalla, r, borde=COLOR["panel_borde"], radio=20)
        texto(pantalla, "¿Abandonar la partida?", self.rec.fuente(26, negrita=True, serif=True),
              COLOR["texto"], (r.centerx, r.y + 58))
        self.btn_si.dibujar(pantalla, self.rec)
        self.btn_no.dibujar(pantalla, self.rec)


def _punteado(destino, color, puntos, largo=7, hueco=5):
    for a, b in zip(puntos, puntos[1:] + puntos[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        total = max(1.0, (dx * dx + dy * dy) ** 0.5)
        d = 0.0
        while d < total:
            f = min(d + largo, total)
            pygame.draw.line(destino, color,
                             (a[0] + dx * d / total, a[1] + dy * d / total),
                             (a[0] + dx * f / total, a[1] + dy * f / total), 2)
            d += largo + hueco
