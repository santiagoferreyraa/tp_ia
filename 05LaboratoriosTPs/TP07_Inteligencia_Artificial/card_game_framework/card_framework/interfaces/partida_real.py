"""Partida contra el robot con cartas de verdad.

El robot no ve la mesa: un OPERADOR le carga sus cartas al empezar cada mano
y le cuenta lo que hace el rival (que carta tiro, que canto, cuantos tantos
dice tener). El robot decide con el mismo motor y la misma IA que la mesa
virtual, y dice su jugada; la carta la tira una persona.

No depende de pygame: la pantalla del operador, una consola o un futuro
modulo de vision pueden manejarla igual.

    partida = PartidaReal(objetivo=15)
    partida.cargar_cartas_robot([Card(Suit.ESPADA, 1), ...])
    partida.aplicar(accion_del_rival)
    resultado = partida.jugar_robot()
    print(resultado.dice)          # "Tiro el ancho de espada."
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from card_framework.agents.heuristic_truco_agent import HeuristicTrucoAgent
from card_framework.core.action import Action, ActionType
from card_framework.core.card import Card
from card_framework.games.truco.truco_deck import calculate_envido_points
from card_framework.games.truco.truco_game import TrucoGame
from card_framework.interfaces import frases_robot


@dataclass
class Resultado:
    """Que paso despues de una jugada. Lo que la pantalla necesita mostrar."""
    accion: Action
    de_robot: bool
    dice: Optional[str] = None                 # lo que dice el robot, si habla
    envido: Optional[dict] = None              # resultado del envido, si se resolvio
    mano_terminada: bool = False
    ganador_mano: Optional[str] = None
    puntos_mano: Dict[str, int] = field(default_factory=dict)
    envido_por_mazo: int = 0
    verificacion_envido: Optional[str] = None  # si el rival declaro tantos que sus cartas no dan
    partida_terminada: bool = False


class PartidaReal:
    def __init__(self, objetivo: int = 15, farol: float = 0.5, robot_es_mano: bool = False,
                 nombre_robot: str = "G1", nombre_rival: str = "Rival"):
        self.game = TrucoGame(p1_name=nombre_rival, p2_name=nombre_robot, target_score=objetivo,
                              ocultos=("player_1",))
        self.rival, self.robot = self.game.p1_id, self.game.p2_id
        self.state = self.game.reset()
        if robot_es_mano:
            self.state.game_data["mano_player_id"] = self.robot
            self.state.current_player_id = self.robot
        self.agente = HeuristicTrucoAgent(name=nombre_robot, bluff_frequency=farol)
        self.cartas_cargadas = False
        # Lo que el rival fue mostrando en la mano, para verificar su envido.
        self._tiradas_rival: List[Card] = []
        self._declarado_rival: Optional[int] = None

    # ---------- consultas ----------
    @property
    def data(self) -> dict:
        return self.state.game_data

    @property
    def terminada(self) -> bool:
        return self.state.is_terminal

    def puntos(self) -> Dict[str, int]:
        return {pid: p.score for pid, p in self.state.players.items()}

    def necesita_cartas(self) -> bool:
        return not self.terminada and not self.cartas_cargadas

    def turno_robot(self) -> bool:
        return not self.terminada and self.cartas_cargadas and self.state.current_player_id == self.robot

    def turno_rival(self) -> bool:
        return not self.terminada and self.cartas_cargadas and self.state.current_player_id == self.rival

    def esperando_declaracion(self) -> bool:
        return self.turno_rival() and self.data["envido_state"] == "WAITING_DECLARATION"

    def acciones_rival(self) -> List[Action]:
        return self.game.get_valid_actions(self.state, self.rival) if self.turno_rival() else []

    def cartas_robot(self) -> List[Card]:
        return list(self.state.players[self.robot].hand)

    def cartas_vistas(self) -> List[Card]:
        return self.game.cartas_vistas(self.state)

    def bazas(self) -> List[dict]:
        """Por baza: la carta del robot, la del rival y quien la gano."""
        jugadas = self.data["played_cards"]
        ganadores = self.data["trick_winners"]
        filas = []
        for i in range(3):
            r = jugadas[self.robot][i] if i < len(jugadas[self.robot]) else None
            v = jugadas[self.rival][i] if i < len(jugadas[self.rival]) else None
            filas.append({"robot": r, "rival": v, "ganador": ganadores[i] if i < len(ganadores) else None})
        return filas

    # ---------- comandos ----------
    def cargar_cartas_robot(self, cartas: List[Card]) -> None:
        self.game.asignar_mano(self.state, self.robot, cartas)
        self.cartas_cargadas = True

    def aplicar(self, accion: Action) -> Resultado:
        """Aplica una jugada del rival (cargada por el operador)."""
        if accion.player_id != self.rival:
            raise ValueError("aplicar() es para las jugadas del rival; el robot juega con jugar_robot().")
        valida = next((a for a in self.acciones_rival() if a == accion), None)
        if valida is None:
            raise ValueError(f"Ahora no se puede: {accion.name}")
        # Se usa la accion del motor: trae la carta con su jerarquia cargada.
        return self._paso(valida, de_robot=False)

    def jugar_robot(self) -> Resultado:
        """El robot decide y juega. Devuelve lo que hizo y lo que dice."""
        if not self.turno_robot():
            raise ValueError("No es el turno del robot.")
        acciones = self.game.get_valid_actions(self.state, self.robot)
        obs = self.game.get_player_observation(self.state, self.robot)
        accion = self.agente.select_action(obs, acciones)
        return self._paso(accion, de_robot=True)

    # ---------- interno ----------
    def _paso(self, accion: Action, de_robot: bool) -> Resultado:
        antes = self.puntos()
        declarado_antes = dict(self.data.get("envido_declarado", {}))
        if not de_robot and accion.action_type == ActionType.PLAY_CARD:
            self._tiradas_rival.append(accion.payload["card"])
        cartas_robot = self.cartas_robot()

        self.state, _, _ = self.game.step(self.state, accion)
        data = self.data

        r = Resultado(accion=accion, de_robot=de_robot)
        if de_robot:
            r.dice = frases_robot.frase(accion, anunciar_carta=True)

        if data["envido_just_resolved"]:
            r.envido = dict(data["envido_resolved_info"])
            if r.envido.get("accepted"):
                # El robot canta sus tantos, como en la mesa.
                propios = calculate_envido_points(cartas_robot + data["played_cards"][self.robot])
                gano = r.envido["winner_id"] == self.robot
                texto = f"Tengo {propios}." + (" Son mejores." if gano else " Son buenas.")
                r.dice = f"{r.dice} {texto}" if r.dice else texto
            declarado_antes = dict(r.envido.get("declarado", declarado_antes))
            self._declarado_rival = declarado_antes.get(self.rival)

        if data["hand_just_finished"]:
            r.mano_terminada = True
            r.ganador_mano = data["last_hand_winner_id"]
            r.puntos_mano = {pid: self.puntos()[pid] - antes[pid] for pid in antes}
            r.envido_por_mazo = data.get("envido_por_mazo", 0)
            r.verificacion_envido = self._verificar_envido()
            self.cartas_cargadas = False
            self._tiradas_rival = []
            self._declarado_rival = None
        r.partida_terminada = self.terminada
        return r

    def _verificar_envido(self) -> Optional[str]:
        """Si el rival declaro tantos y mostro sus 3 cartas, se controla que no haya mentido."""
        if self._declarado_rival is None:
            return None
        if len(self._tiradas_rival) < 3:
            return (f"El rival dijo tener {self._declarado_rival} y no mostró todas sus cartas: "
                    "pedile que las muestre.")
        reales = calculate_envido_points(self._tiradas_rival)
        if reales != self._declarado_rival:
            return f"¡Ojo! El rival dijo {self._declarado_rival} de envido, pero sus cartas suman {reales}."
        return None
