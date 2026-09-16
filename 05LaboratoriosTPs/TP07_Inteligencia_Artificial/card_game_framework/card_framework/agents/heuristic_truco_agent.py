"""Agente Experto de IA para Truco basado en Heurísticas, Probabilidad y Engaño (Bluffing)."""

import random
from typing import List, Optional
from card_framework.agents.base_agent import AbstractAgent
from card_framework.core.action import Action, ActionType
from card_framework.core.card import Card
from card_framework.core.game_state import GameState
from card_framework.games.truco.truco_deck import calculate_envido_points


class HeuristicTrucoAgent(AbstractAgent):
    """Agente inteligente de Truco con toma de decisiones heurísticas y cálculo probabilístico."""

    def __init__(self, name: str = "TrucoBot-Pro", bluff_frequency: float = 0.15):
        super().__init__(name=name)
        self.bluff_frequency = bluff_frequency

    def select_action(self, observation: GameState, valid_actions: List[Action]) -> Action:
        if not valid_actions:
            raise ValueError("No hay acciones válidas para seleccionar.")

        player_id = observation.current_player_id
        player = observation.players[player_id]
        data = observation.game_data

        # 1. Evaluar si debemos responder a un cante de ENVIDO
        response_envido = self._handle_envido_response(player.hand, valid_actions)
        if response_envido:
            return response_envido

        # 2. Evaluar si debemos cantar ENVIDO
        bid_envido = self._handle_envido_bidding(player.hand, valid_actions, data)
        if bid_envido:
            return bid_envido

        # 3. Evaluar si debemos responder a un cante de TRUCO
        response_truco = self._handle_truco_response(player.hand, valid_actions)
        if response_truco:
            return response_truco

        # 4. Evaluar si debemos cantar TRUCO
        bid_truco = self._handle_truco_bidding(player.hand, valid_actions, data)
        if bid_truco:
            return bid_truco

        # 5. Seleccionar la mejor carta para jugar
        play_card_action = self._select_best_card(player.hand, valid_actions, data, player_id)
        if play_card_action:
            return play_card_action

        # Fallback por seguridad
        return valid_actions[0]

    def _handle_envido_response(self, hand: List[Card], valid_actions: List[Action]) -> Optional[Action]:
        env_resp_actions = [a for a in valid_actions if a.payload.get("response") in ["QUIERO_ENVIDO", "NO_QUIERO_ENVIDO"]]
        if not env_resp_actions:
            return None

        points = calculate_envido_points(hand)
        # Buscar opción de subida (ej. Falta Envido con > 31 puntos)
        raises = [a for a in valid_actions if a.payload.get("bid") in ["REAL_ENVIDO", "FALTA_ENVIDO"]]
        if points >= 31 and raises:
            return random.choice(raises)

        if points >= 26 or (random.random() < self.bluff_frequency):
            quiero = next((a for a in env_resp_actions if a.payload.get("response") == "QUIERO_ENVIDO"), None)
            if quiero:
                return quiero

        no_quiero = next((a for a in env_resp_actions if a.payload.get("response") == "NO_QUIERO_ENVIDO"), None)
        return no_quiero or env_resp_actions[0]

    def _handle_envido_bidding(self, hand: List[Card], valid_actions: List[Action], data: dict) -> Optional[Action]:
        bids = [a for a in valid_actions if a.payload.get("bid") in ["ENVIDO", "REAL_ENVIDO", "FALTA_ENVIDO"]]
        if not bids:
            return None

        points = calculate_envido_points(hand)
        if points >= 30:
            falta = next((a for a in bids if a.payload.get("bid") == "FALTA_ENVIDO"), None)
            real = next((a for a in bids if a.payload.get("bid") == "REAL_ENVIDO"), None)
            env = next((a for a in bids if a.payload.get("bid") == "ENVIDO"), None)
            return falta or real or env
        elif points >= 27:
            env = next((a for a in bids if a.payload.get("bid") == "ENVIDO"), None)
            if env:
                return env
        elif random.random() < (self.bluff_frequency * 0.5): # Farol ocasional
            env = next((a for a in bids if a.payload.get("bid") == "ENVIDO"), None)
            if env:
                return env

        return None

    def _handle_truco_response(self, hand: List[Card], valid_actions: List[Action]) -> Optional[Action]:
        truco_resp = [a for a in valid_actions if a.payload.get("response") in ["QUIERO_TRUCO", "NO_QUIERO_TRUCO"]]
        if not truco_resp:
            return None

        max_rank = max((c.rank for c in hand), default=0)
        avg_rank = sum(c.rank for c in hand) / max(len(hand), 1)

        # Si tenemos cartas altas (ej. Ancho, 7 de Espada/Oro, 3s)
        if max_rank >= 10 or avg_rank >= 7.0 or (random.random() < self.bluff_frequency):
            # Posibilidad de re-truco si la mano es devastadora
            retruco = next((a for a in valid_actions if a.payload.get("bid") in ["RETRUCO", "VALE_CUATRO"]), None)
            if retruco and max_rank >= 12:
                return retruco

            quiero = next((a for a in truco_resp if a.payload.get("response") == "QUIERO_TRUCO"), None)
            if quiero:
                return quiero

        no_quiero = next((a for a in truco_resp if a.payload.get("response") == "NO_QUIERO_TRUCO"), None)
        return no_quiero or truco_resp[0]

    def _handle_truco_bidding(self, hand: List[Card], valid_actions: List[Action], data: dict) -> Optional[Action]:
        truco_bids = [a for a in valid_actions if a.payload.get("bid") in ["TRUCO", "RETRUCO", "VALE_CUATRO"]]
        if not truco_bids:
            return None

        max_rank = max((c.rank for c in hand), default=0)
        if max_rank >= 11 or (random.random() < (self.bluff_frequency * 0.7)):
            return truco_bids[0]

        return None

    def _select_best_card(self, hand: List[Card], valid_actions: List[Action], data: dict, player_id: str) -> Optional[Action]:
        card_actions = [a for a in valid_actions if a.action_type == ActionType.PLAY_CARD]
        if not card_actions:
            return None

        current_trick = data.get("current_trick_cards", {})
        # Si somos segundos en tirar en esta baza
        if len(current_trick) == 1:
            opponent_id = next(pid for pid in current_trick if pid != player_id)
            opp_card = current_trick[opponent_id]

            # Buscar la carta más baja propia que le gane a la del rival
            winning_actions = [a for a in card_actions if a.payload["card"].rank > opp_card.rank]
            if winning_actions:
                winning_actions.sort(key=lambda a: a.payload["card"].rank)
                return winning_actions[0] # Ganar con la más chica posible

            # Si no le podemos ganar, tirar nuestra carta más baja de descarte
            card_actions.sort(key=lambda a: a.payload["card"].rank)
            return card_actions[0]

        # Si somos primeros en tirar
        # En primera mano, tirar carta media o baja para reservar la más alta
        card_actions.sort(key=lambda a: a.payload["card"].rank)
        if len(card_actions) >= 2:
            return card_actions[1] # Carta intermedia
        return card_actions[0]
