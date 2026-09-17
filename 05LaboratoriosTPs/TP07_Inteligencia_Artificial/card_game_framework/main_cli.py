"""Punto de entrada del Truco contra el robot.

    python main_cli.py             abre la mesa (pygame)
    python main_cli.py --consola   juega en la terminal
    python main_cli.py --sim       10 partidas IA vs. jugador al azar
"""

import sys
from card_framework.agents.heuristic_truco_agent import HeuristicTrucoAgent
from card_framework.agents.random_agent import RandomAgent
from card_framework.games.truco.truco_game import TrucoGame


def print_banner():
    print("=" * 65)
    print("      FRAMEWORK DE JUEGOS DE CARTAS - TRUCO ARGENTINO IA      ")
    print("=" * 65)


def play_game_interactive():
    print_banner()
    human_name = input("Ingresá tu nombre: ").strip() or "Jugador"
    target_score = 15

    print(f"\n¡Bienvenido {human_name}! Jugando partida a {target_score} puntos contra la IA.")
    print("-" * 65)

    game = TrucoGame(p1_name=human_name, p2_name="TrucoBot-AI", target_score=target_score)
    bot = HeuristicTrucoAgent(name="TrucoBot-AI", bluff_frequency=0.2)
    state = game.reset()

    human_id = game.p1_id
    bot_id = game.p2_id

    while not state.is_terminal:
        curr_id = state.current_player_id
        valid_actions = game.get_valid_actions(state, curr_id)

        if not valid_actions:
            break

        if curr_id == human_id:
            print(f"\n>>> TURNO DE {human_name.upper()} <<<")
            print(f"Puntaje actual: {human_name}: {state.players[human_id].score} | Bot: {state.players[bot_id].score}")
            print(f"Tus Cartas: {[str(c) for c in state.players[human_id].hand]}")

            print("\nAcciones disponibles:")
            for idx, act in enumerate(valid_actions, start=1):
                print(f"  [{idx}] {act.name}")

            while True:
                try:
                    choice = int(input("\nElegí una acción (número): "))
                    if 1 <= choice <= len(valid_actions):
                        chosen_action = valid_actions[choice - 1]
                        break
                    print("Opción inválida, reintentá.")
                except (ValueError, KeyboardInterrupt):
                    print("\nSalida del juego.")
                    sys.exit(0)
        else:
            obs = game.get_player_observation(state, bot_id)
            chosen_action = bot.select_action(obs, valid_actions)
            print(f"\n🤖 [Bot]: {chosen_action.name}")

        state, reward, is_term = game.step(state, chosen_action)

    print("\n" + "=" * 65)
    print("                   ¡PARTIDA FINALIZADA!                       ")
    print("=" * 65)
    winner_name = state.players[state.winner_id].name if state.winner_id else "Empate"
    print(f"🏆 GANADOR: {winner_name}")
    print(f"Puntaje Final: {human_name}: {state.players[human_id].score} | {bot.name}: {state.players[bot_id].score}\n")


def play_simulation_ai_vs_ai(num_games: int = 5):
    print_banner()
    print(f"Ejecutando Simulación de {num_games} partidas: HeuristicTrucoAgent vs RandomAgent\n")

    game = TrucoGame(p1_name="TrucoBot-Pro", p2_name="RandomBot", target_score=15)
    bot_pro = HeuristicTrucoAgent(name="TrucoBot-Pro")
    bot_rand = RandomAgent(name="RandomBot")

    pro_wins = 0
    rand_wins = 0

    for i in range(1, num_games + 1):
        state = game.reset()
        while not state.is_terminal:
            curr_id = state.current_player_id
            actions = game.get_valid_actions(state, curr_id)
            if not actions:
                break
            if curr_id == game.p1_id:
                obs = game.get_player_observation(state, game.p1_id)
                act = bot_pro.select_action(obs, actions)
            else:
                obs = game.get_player_observation(state, game.p2_id)
                act = bot_rand.select_action(obs, actions)
            state, _, _ = game.step(state, act)

        winner = state.players[state.winner_id].name
        if state.winner_id == game.p1_id:
            pro_wins += 1
        else:
            rand_wins += 1
        print(f"Partida {i}: Ganó {winner} ({state.players[game.p1_id].score} - {state.players[game.p2_id].score})")

    print("\n" + "-" * 65)
    print(f"Resultado Final Simulación:")
    print(f"  - {bot_pro.name}: {pro_wins} victorias ({pro_wins / num_games * 100:.1f}%)")
    print(f"  - {bot_rand.name}: {rand_wins} victorias ({rand_wins / num_games * 100:.1f}%)\n")


def launch_gui():
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("Falta pygame para abrir la mesa. Instalalo con:")
        print("    python -m pip install --user pygame")
        print("Mientras tanto podés jugar en consola:  python main_cli.py --consola")
        sys.exit(1)
    from card_framework.interfaces.mesa.app import main as abrir_mesa
    abrir_mesa()


if __name__ == "__main__":
    if "--sim" in sys.argv:
        play_simulation_ai_vs_ai(num_games=10)
    elif "--consola" in sys.argv:
        play_game_interactive()
    else:
        launch_gui()
