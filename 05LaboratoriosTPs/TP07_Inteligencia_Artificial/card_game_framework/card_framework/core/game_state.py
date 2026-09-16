"""Contenedor de Estado del Juego y vista con información parcial (imperfecta)."""

from typing import Any, Dict, List, Optional
from card_framework.core.player import Player


class GameState:
    """Representa el estado actual completo o la observación privada de un juego."""

    def __init__(self, current_player_id: str, players: Dict[str, Player], round_num: int = 1):
        self.current_player_id = current_player_id
        self.players = players
        self.round_num = round_num
        self.history: List[Any] = []
        self.is_terminal: bool = False
        self.winner_id: Optional[str] = None
        self.game_data: Dict[str, Any] = {}

    def get_player_observation(self, player_id: str) -> "GameState":
        """Crea una vista del estado que oculta la información privada de otros jugadores.

        Garantiza que el bot o jugador sólo vea sus propias cartas.
        """
        obs_players = {}
        for pid, p in self.players.items():
            obs_p = Player(p.player_id, p.name, p.is_ai)
            obs_p.score = p.score
            if pid == player_id:
                obs_p.hand = p.hand[:]
            else:
                # Ocultar la mano del rival
                obs_p.hand = []
            obs_players[pid] = obs_p

        obs = GameState(self.current_player_id, obs_players, self.round_num)
        obs.history = self.history[:]
        obs.is_terminal = self.is_terminal
        obs.winner_id = self.winner_id
        obs.game_data = self.game_data.copy()
        return obs
