"""Ejemplo de Adaptador para integrar el Framework de Truco con un Robot Físico o Simulador.

Demuestra cómo:
1. Recibir cartas vistas por la cámara del robot (Visión Computacional / Sensores).
2. Procesar la mejor jugada usando la IA del Truco.
3. Enviar la respuesta al altavoz (TTS) y pantalla del robot.
"""

from typing import List, Optional
from card_framework.core.card import Card, Suit
from card_framework.core.action import Action
from card_framework.games.truco.truco_deck import get_truco_rank
from card_framework.games.truco.truco_game import TrucoGame
from card_framework.agents.heuristic_truco_agent import HeuristicTrucoAgent


class RobotTrucoBridge:
    """Clase puente entre los sensores/altavoces del robot y el motor de IA."""

    def __init__(self, robot_name: str = "Unitree G1"):
        self.game = TrucoGame(p1_name="Rival Humano", p2_name=robot_name)
        self.ai = HeuristicTrucoAgent(name=robot_name)
        self.state = self.game.reset()
        self.robot_id = self.game.p2_id
        self.human_id = self.game.p1_id

    def on_cards_detected_by_camera(self, cards_raw: List[dict]) -> None:
        """Simula la entrada de visión por computadora cuando la cámara ve las cartas repartidas."""
        suit_map = {
            "Espada": Suit.ESPADA,
            "Basto": Suit.BASTO,
            "Oro": Suit.ORO,
            "Copa": Suit.COPA
        }

        detected_cards = []
        for c in cards_raw:
            s = suit_map[c["palo"]]
            v = c["valor"]
            r = get_truco_rank(s, v)
            detected_cards.append(Card(suit=s, value=v, rank=r))

        self.state.players[self.robot_id].clear_hand()
        self.state.players[self.robot_id].receive_cards(detected_cards)
        print(f"\n[Camara Robot] Cartas detectadas en la mesa para el robot: {[str(c) for c in detected_cards]}")

    def on_human_action_detected(self, action_name: str, card_data: Optional[dict] = None) -> None:
        """Registra la jugada o cante del rival humano cuando la cámara/micrófono lo detecta."""
        valid_actions = self.game.get_valid_actions(self.state, self.human_id)

        matched_action = None
        for act in valid_actions:
            if action_name.lower() in act.name.lower():
                matched_action = act
                break

        if not matched_action and valid_actions:
            matched_action = valid_actions[0]

        if matched_action:
            print(f"[Rival Humano]: {matched_action.name}")
            self.state, _, _ = self.game.step(self.state, matched_action)

    def get_robot_next_move(self) -> str:
        """Calcula la mejor jugada con la IA y devuelve el mensaje que debe decir/ejecutar el robot."""
        if self.state.current_player_id != self.robot_id:
            return "Es el turno del rival humano."

        obs = self.game.get_player_observation(self.state, self.robot_id)
        valid_actions = self.game.get_valid_actions(self.state, self.robot_id)

        if not valid_actions:
            return "No hay acciones posibles en este momento."

        chosen_action = self.ai.select_action(obs, valid_actions)
        self.state, _, _ = self.game.step(self.state, chosen_action)

        action_name = chosen_action.name
        if "Jugar" in action_name:
            speech = f"Juego el {action_name.replace('Jugar ', '')}."
        elif "Quiero" in action_name or "Envido" in action_name or "Truco" in action_name:
            speech = f"¡{action_name}!"
        elif "mazo" in action_name:
            speech = "Me voy al mazo."
        else:
            speech = f"Hago {action_name}."

        return speech


if __name__ == "__main__":
    print("=========================================================")
    print("      DEMOSTRACION DE INTEGRACION DE ROBOT Y CAMARA      ")
    print("=========================================================")
    bridge = RobotTrucoBridge("Unitree G1")

    # 1. La cámara detecta las cartas repartidas al robot:
    cartas_camara = [
        {"palo": "Espada", "valor": 7},
        {"palo": "Basto", "valor": 1},
        {"palo": "Copa", "valor": 3}
    ]
    bridge.on_cards_detected_by_camera(cartas_camara)

    # 2. El rival humano juega primero (ej. tira una carta):
    bridge.on_human_action_detected("Jugar")

    # 3. Le toca al robot: la IA evalúa y devuelve lo que debe decir por su altavoz:
    respuesta_voz = bridge.get_robot_next_move()
    print(f"\n[Altavoz Robot] El robot dice: \"{respuesta_voz}\"\n")
