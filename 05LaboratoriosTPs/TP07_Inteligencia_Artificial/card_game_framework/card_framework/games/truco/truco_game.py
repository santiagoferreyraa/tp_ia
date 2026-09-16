"""Motor Completo de Reglas del Truco Argentino."""

from typing import Dict, List, Optional, Tuple
from card_framework.core.action import Action, ActionType
from card_framework.core.card import Card
from card_framework.core.game_state import GameState
from card_framework.core.player import Player
from card_framework.games.base_game import AbstractGame
from card_framework.games.truco.truco_deck import create_spanish_40_deck, calculate_envido_points


class TrucoGame(AbstractGame):
    """Implementación del juego Truco Argentino (1v1) a 15 o 30 puntos."""

    def __init__(self, p1_name: str = "Jugador 1", p2_name: str = "Jugador 2", target_score: int = 15):
        self.p1_id = "player_1"
        self.p2_id = "player_2"
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.target_score = target_score

    def reset(self) -> GameState:
        """Inicializa una nueva partida o nueva mano."""
        players = {
            self.p1_id: Player(self.p1_id, self.p1_name),
            self.p2_id: Player(self.p2_id, self.p2_name)
        }
        state = GameState(current_player_id=self.p1_id, players=players)
        state.game_data = {
            "mano_player_id": self.p1_id,
            "target_score": self.target_score,
            "envido_state": "UNOPENED",
            "envido_bid_chain": [],
            "envido_bidder_id": None,
            "envido_points_awarded": False,
            "envido_just_resolved": False,
            "envido_resolved_info": {},
            "truco_state": "NONE",
            "truco_bidder_id": None,
            "truco_last_offered_by": None,
            "truco_value": 1,
            "trick_winners": [],
            "current_trick_cards": {},
            "played_cards": {self.p1_id: [], self.p2_id: []},
            "trick_num": 1,
            "hand_finished": False,
            "hand_just_finished": False,
            "last_hand_winner_id": None,
        }
        self._deal_new_hand(state)
        return state

    def _deal_new_hand(self, state: GameState) -> None:
        """Reparte 3 cartas a cada jugador y resetea variables de la mano."""
        deck = create_spanish_40_deck()
        deck.shuffle()

        for p in state.players.values():
            p.clear_hand()
            p.receive_cards(deck.deal(3))

        data = state.game_data
        data["envido_state"] = "UNOPENED"
        data["envido_bid_chain"] = []
        data["envido_bidder_id"] = None
        data["envido_points_awarded"] = False
        data["envido_just_resolved"] = False
        data["envido_resolved_info"] = {}
        data["truco_state"] = "NONE"
        data["truco_bidder_id"] = None
        data["truco_last_offered_by"] = None
        data["truco_value"] = 1
        data["trick_winners"] = []
        data["current_trick_cards"] = {}
        data["played_cards"] = {self.p1_id: [], self.p2_id: []}
        data["trick_num"] = 1
        data["hand_finished"] = False
        state.current_player_id = data["mano_player_id"]

    def _opponent_id(self, player_id: str) -> str:
        return self.p2_id if player_id == self.p1_id else self.p1_id

    def get_valid_actions(self, state: GameState, player_id: str) -> List[Action]:
        """Devuelve las acciones legales disponibles para el jugador."""
        if state.is_terminal or state.current_player_id != player_id:
            return []

        actions = []
        data = state.game_data
        opponent_id = self._opponent_id(player_id)
        player = state.players[player_id]

        # 1. Si se está esperando respuesta a un cante de Envido
        if data["envido_state"] == "WAITING_RESPONSE" and data["envido_bidder_id"] == opponent_id:
            actions.append(Action(ActionType.RESPONSE, player_id, "Quiero", {"response": "QUIERO_ENVIDO"}))
            actions.append(Action(ActionType.RESPONSE, player_id, "No Quiero", {"response": "NO_QUIERO_ENVIDO"}))
            last_bid = data["envido_bid_chain"][-1]
            if last_bid == "ENVIDO":
                actions.append(Action(ActionType.BID, player_id, "Envido", {"bid": "ENVIDO"}))
                actions.append(Action(ActionType.BID, player_id, "Real Envido", {"bid": "REAL_ENVIDO"}))
                actions.append(Action(ActionType.BID, player_id, "Falta Envido", {"bid": "FALTA_ENVIDO"}))
            elif last_bid == "REAL_ENVIDO":
                actions.append(Action(ActionType.BID, player_id, "Falta Envido", {"bid": "FALTA_ENVIDO"}))
            return actions

        # 2. Si se está esperando respuesta a un cante de Truco
        if data["truco_state"] == "WAITING_RESPONSE" and data["truco_last_offered_by"] == opponent_id:
            actions.append(Action(ActionType.RESPONSE, player_id, "Quiero", {"response": "QUIERO_TRUCO"}))
            actions.append(Action(ActionType.RESPONSE, player_id, "No Quiero", {"response": "NO_QUIERO_TRUCO"}))
            last_offered = data["truco_bid_name"]
            if last_offered == "TRUCO":
                actions.append(Action(ActionType.BID, player_id, "Retruco", {"bid": "RETRUCO"}))
            elif last_offered == "RETRUCO":
                actions.append(Action(ActionType.BID, player_id, "Vale Cuatro", {"bid": "VALE_CUATRO"}))
            return actions

        # 3. Acciones de cante de Envido (sólo en ronda 1 y antes de tirar la 2da carta)
        if data["envido_state"] == "UNOPENED" and data["trick_num"] == 1 and len(data["played_cards"][player_id]) == 0:
            actions.append(Action(ActionType.BID, player_id, "Envido", {"bid": "ENVIDO"}))
            actions.append(Action(ActionType.BID, player_id, "Real Envido", {"bid": "REAL_ENVIDO"}))
            actions.append(Action(ActionType.BID, player_id, "Falta Envido", {"bid": "FALTA_ENVIDO"}))

        # 4. Acciones de cante de Truco
        if data["truco_last_offered_by"] != player_id:
            if data["truco_state"] == "NONE":
                actions.append(Action(ActionType.BID, player_id, "Truco", {"bid": "TRUCO"}))
            elif data["truco_state"] == "TRUCO":
                actions.append(Action(ActionType.BID, player_id, "Retruco", {"bid": "RETRUCO"}))
            elif data["truco_state"] == "RETRUCO":
                actions.append(Action(ActionType.BID, player_id, "Vale Cuatro", {"bid": "VALE_CUATRO"}))

        # 5. Jugar Carta
        for card in player.hand:
            actions.append(Action(ActionType.PLAY_CARD, player_id, f"Jugar {card.name}", {"card": card}))

        # 6. Irse al mazo
        actions.append(Action(ActionType.FOLD, player_id, "Me voy al mazo", {}))

        return actions

    def step(self, state: GameState, action: Action) -> Tuple[GameState, float, bool]:
        """Aplica la acción y actualiza la máquina de estados del Truco."""
        player_id = action.player_id
        opponent_id = self._opponent_id(player_id)
        data = state.game_data
        state.history.append(action)

        data["hand_just_finished"] = False
        data["envido_just_resolved"] = False

        # A) IRSE AL MAZO
        if action.action_type == ActionType.FOLD:
            points_won = data["truco_value"]
            state.players[opponent_id].score += points_won
            self._finish_hand(state, winner_id=opponent_id)
            return state, points_won, state.is_terminal

        # B) CANTAR ENVIDO
        if action.action_type == ActionType.BID and action.payload.get("bid") in ["ENVIDO", "REAL_ENVIDO", "FALTA_ENVIDO"]:
            bid_type = action.payload["bid"]
            data["envido_state"] = "WAITING_RESPONSE"
            data["envido_bid_chain"].append(bid_type)
            data["envido_bidder_id"] = player_id
            state.current_player_id = opponent_id
            return state, 0.0, state.is_terminal

        # C) RESPONDER ENVIDO
        if action.action_type in [ActionType.RESPONSE, ActionType.BID] and data["envido_state"] == "WAITING_RESPONSE":
            resp = action.payload.get("response") or action.payload.get("bid")

            if resp == "NO_QUIERO_ENVIDO":
                points = self._calculate_refused_envido_points(data["envido_bid_chain"])
                state.players[data["envido_bidder_id"]].score += points
                data["envido_state"] = "RESOLVED"
                data["envido_points_awarded"] = True
                data["envido_just_resolved"] = True
                data["envido_resolved_info"] = {
                    "accepted": False,
                    "winner_id": data["envido_bidder_id"],
                    "points_won": points
                }
                state.current_player_id = data["envido_bidder_id"]
                self._check_game_over(state)
                return state, 0.0, state.is_terminal

            elif resp == "QUIERO_ENVIDO":
                p1_pts = calculate_envido_points(state.players[self.p1_id].hand + data["played_cards"][self.p1_id])
                p2_pts = calculate_envido_points(state.players[self.p2_id].hand + data["played_cards"][self.p2_id])
                points_won = self._calculate_accepted_envido_points(data["envido_bid_chain"], state)

                winner_id = self.p1_id if p1_pts > p2_pts else (self.p2_id if p2_pts > p1_pts else data["mano_player_id"])
                state.players[winner_id].score += points_won
                data["envido_state"] = "RESOLVED"
                data["envido_points_awarded"] = True
                data["envido_just_resolved"] = True
                data["envido_resolved_info"] = {
                    "accepted": True,
                    "p1_pts": p1_pts,
                    "p2_pts": p2_pts,
                    "winner_id": winner_id,
                    "points_won": points_won
                }
                state.current_player_id = data["envido_bidder_id"]
                self._check_game_over(state)
                return state, 0.0, state.is_terminal

        # D) CANTAR TRUCO / RETRUCO / VALE CUATRO
        if action.action_type == ActionType.BID and action.payload.get("bid") in ["TRUCO", "RETRUCO", "VALE_CUATRO"]:
            bid_type = action.payload["bid"]
            data["truco_state"] = "WAITING_RESPONSE"
            data["truco_bid_name"] = bid_type
            data["truco_last_offered_by"] = player_id
            state.current_player_id = opponent_id
            return state, 0.0, state.is_terminal

        # E) RESPONDER TRUCO
        if action.action_type == ActionType.RESPONSE and data["truco_state"] == "WAITING_RESPONSE":
            resp = action.payload.get("response")
            if resp == "NO_QUIERO_TRUCO":
                points_won = data["truco_value"]
                state.players[opponent_id].score += points_won
                self._finish_hand(state, winner_id=opponent_id)
                return state, points_won, state.is_terminal
            elif resp == "QUIERO_TRUCO":
                bid_name = data["truco_bid_name"]
                data["truco_state"] = bid_name
                data["truco_value"] = 2 if bid_name == "TRUCO" else (3 if bid_name == "RETRUCO" else 4)
                state.current_player_id = opponent_id
                return state, 0.0, state.is_terminal

        # F) JUGAR CARTA
        if action.action_type == ActionType.PLAY_CARD:
            card = action.payload["card"]
            state.players[player_id].play_card(card)
            data["current_trick_cards"][player_id] = card
            data["played_cards"][player_id].append(card)

            if len(data["current_trick_cards"]) == 2:
                c1 = data["current_trick_cards"][self.p1_id]
                c2 = data["current_trick_cards"][self.p2_id]
                trick_winner = self.p1_id if c1.rank > c2.rank else (self.p2_id if c2.rank > c1.rank else "TIE")
                data["trick_winners"].append(trick_winner)
                data["current_trick_cards"] = {}
                data["trick_num"] += 1

                hand_winner = self._evaluate_hand_winner(data["trick_winners"], data["mano_player_id"])
                if hand_winner:
                    state.players[hand_winner].score += data["truco_value"]
                    self._finish_hand(state, winner_id=hand_winner)
                else:
                    state.current_player_id = trick_winner if trick_winner != "TIE" else data["mano_player_id"]
            else:
                state.current_player_id = opponent_id

            return state, 0.0, state.is_terminal

        return state, 0.0, state.is_terminal

    def _evaluate_hand_winner(self, winners: List[str], mano_id: str) -> Optional[str]:
        if len(winners) < 2:
            return None

        w1, w2 = winners[0], winners[1]
        if w1 != "TIE" and w2 == w1:
            return w1
        if w1 == "TIE" and w2 != "TIE":
            return w2
        if w2 == "TIE" and w1 != "TIE":
            return w1
        if w1 == "TIE" and w2 == "TIE":
            if len(winners) == 3:
                w3 = winners[2]
                return w3 if w3 != "TIE" else mano_id
            return None
        if len(winners) == 3:
            w3 = winners[2]
            return w3 if w3 != "TIE" else w1
        return None

    def _calculate_refused_envido_points(self, chain: List[str]) -> int:
        if len(chain) == 1:
            return 1
        points = 0
        for bid in chain[:-1]:
            points += 1 if bid == "ENVIDO" else (3 if bid == "REAL_ENVIDO" else 1)
        return points

    def _calculate_accepted_envido_points(self, chain: List[str], state: GameState) -> int:
        pts = 0
        for bid in chain:
            if bid == "ENVIDO":
                pts += 2
            elif bid == "REAL_ENVIDO":
                pts += 3
            elif bid == "FALTA_ENVIDO":
                max_score = max(state.players[self.p1_id].score, state.players[self.p2_id].score)
                return self.target_score - max_score
        return pts

    def _finish_hand(self, state: GameState, winner_id: str) -> None:
        state.game_data["hand_just_finished"] = True
        state.game_data["last_hand_winner_id"] = winner_id
        self._check_game_over(state)
        if not state.is_terminal:
            state.game_data["mano_player_id"] = self._opponent_id(state.game_data["mano_player_id"])
            self._deal_new_hand(state)

    def _check_game_over(self, state: GameState) -> None:
        s1 = state.players[self.p1_id].score
        s2 = state.players[self.p2_id].score
        if s1 >= self.target_score or s2 >= self.target_score:
            state.is_terminal = True
            state.winner_id = self.p1_id if s1 >= self.target_score else self.p2_id

    def is_terminal(self, state: GameState) -> bool:
        return state.is_terminal

    def get_player_observation(self, state: GameState, player_id: str) -> GameState:
        return state.get_player_observation(player_id)
