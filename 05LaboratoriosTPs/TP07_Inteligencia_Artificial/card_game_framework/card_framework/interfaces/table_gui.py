"""Mesa Virtual de Truco (GUI) con Modo Debug (Revelar Cartas del Robot) y Limpieza de Mensajes de Voz."""

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Dict, List, Optional, Tuple

from card_framework.core.action import Action, ActionType
from card_framework.core.card import Card
from card_framework.core.card_images import get_card_photo_image
from card_framework.games.truco.truco_verses import get_random_verse
from card_framework.agents.heuristic_truco_agent import HeuristicTrucoAgent
from card_framework.games.truco.truco_game import TrucoGame

# Intentar importar el Robot del simulador oficial UADE
REPO_DESARROLLO = Path("C:/Users/santi/Documents/GitHub/UadeRobotLab/05LaboratoriosTPs/TP07_Inteligencia_Artificial/mi_desarrollo")
if REPO_DESARROLLO.exists() and str(REPO_DESARROLLO) not in sys.path:
    sys.path.insert(0, str(REPO_DESARROLLO))

try:
    from robot import Robot
except Exception:
    Robot = None


def speak_text_async(text: str):
    """Habla en voz alta a través del altavoz de Windows usando SAPI.SpVoice en segundo plano."""
    def _speak():
        try:
            clean_text = text.replace('"', '').replace("'", "")
            cmd = f"powershell -Command \"(New-Object -ComObject SAPI.SpVoice).Speak('{clean_text}')\""
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    threading.Thread(target=_speak, daemon=True).start()


class TrucoTableGUI:
    """Mesa Virtual de Truco con Modo Debug para ver las cartas de la IA y limpieza de mensajes."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Mesa Virtual de Truco - Unitree G1 Robot vs Humano")
        self.root.geometry("980x760")
        self.root.configure(bg="#14361d")

        self.game = TrucoGame(p1_name="Tú (Humano)", p2_name="Robot G1", target_score=15)
        self.bot = HeuristicTrucoAgent(name="Robot G1", bluff_frequency=0.18)
        self.state = self.game.reset()

        self.human_id = self.game.p1_id
        self.bot_id = self.game.p2_id

        # Modo Debug (Revelar Cartas del Robot)
        self.debug_mode = tk.BooleanVar(value=False)

        # Conexión con el simulador 3D MuJoCo
        self.robot_sim = None
        self.sim_connected = False
        self._try_connect_simulator()

        self._build_ui()
        self._update_display()

    def _try_connect_simulator(self):
        if Robot is not None:
            try:
                self.robot_sim = Robot()
                self.robot_sim.conectar()
                self.sim_connected = True
                print("[OK] ¡Conectado con éxito al Simulador 3D de Unitree G1!")
            except Exception as e:
                self.sim_connected = False
                print(f"[INFO] Simulador 3D no detectado ({e}). Modo Mesa Standalone activo.")

    def _build_ui(self):
        # 1. Título, Marcador y Modo Debug
        title_frame = tk.Frame(self.root, bg="#14361d", bd=2, relief="ridge")
        title_frame.pack(fill="x", padx=10, pady=4)

        header_top = tk.Frame(title_frame, bg="#14361d")
        header_top.pack(fill="x", padx=5, pady=2)

        tk.Label(
            header_top,
            text="🎴 MESA DE TRUCO - UNITREE G1 ROBOT 🎴",
            font=("Helvetica", 13, "bold"),
            fg="#f1c40f",
            bg="#14361d"
        ).pack(side="left", padx=10)

        # Checkbox Modo Debug + Botón Reiniciar
        controls_right = tk.Frame(header_top, bg="#14361d")
        controls_right.pack(side="right", padx=10)

        chk_debug = tk.Checkbutton(
            controls_right,
            text="🔍 Modo Debug (Ver cartas Robot)",
            variable=self.debug_mode,
            font=("Helvetica", 9, "bold"),
            fg="#8e44ad",
            bg="#14361d",
            activebackground="#14361d",
            selectcolor="#f1c40f",
            command=self._update_display
        )
        chk_debug.pack(side="left", padx=8)

        btn_restart = tk.Button(
            controls_right,
            text="🔄 Reiniciar Partido",
            font=("Helvetica", 9, "bold"),
            bg="#c0392b",
            fg="#ffffff",
            activebackground="#e74c3c",
            command=self._restart_game
        )
        btn_restart.pack(side="left", padx=5)

        self.score_label = tk.Label(
            title_frame,
            text="Marcador: Tú: 0 pts | Robot G1: 0 pts (Objetivo: 15 pts)",
            font=("Helvetica", 11, "bold"),
            fg="#ffffff",
            bg="#14361d"
        )
        self.score_label.pack(pady=2)

        # 2. Área del Robot (Arriba) + Bocadillo de voz
        robot_frame = tk.Frame(self.root, bg="#14361d")
        robot_frame.pack(fill="x", padx=20, pady=2)

        robot_header = tk.Frame(robot_frame, bg="#14361d")
        robot_header.pack(fill="x")

        tk.Label(robot_header, text="🤖 ROBOT UNITREE G1", font=("Helvetica", 10, "bold"), fg="#e74c3c", bg="#14361d").pack(side="left", padx=5)

        self.robot_hand_frame = tk.Frame(robot_header, bg="#14361d")
        self.robot_hand_frame.pack(side="right", padx=5)

        self.robot_speech_label = tk.Label(
            robot_frame,
            text="🤖 Robot G1: \"¡Hola! Hacé clic en tus cartas en abanico para jugar.\"",
            font=("Helvetica", 10, "italic"),
            fg="#f39c12",
            bg="#14361d",
            padx=10,
            pady=4,
            relief="solid",
            bd=1,
            wraplength=850
        )
        self.robot_speech_label.pack(fill="x", padx=20, pady=2)

        # 3. Paño Verde de Juego (Rondas en la mesa)
        center_table = tk.Frame(self.root, bg="#276638", bd=3, relief="sunken")
        center_table.pack(expand=True, fill="both", padx=15, pady=6)

        tk.Label(center_table, text="=== CARTAS JUGADAS EN LA MESA ===", font=("Helvetica", 11, "bold"), fg="#f1c40f", bg="#276638").pack(pady=3)

        self.rounds_container = tk.Frame(center_table, bg="#276638")
        self.rounds_container.pack(expand=True, fill="both", padx=10, pady=4)

        # 4. Área del Humano (Cartas en Abanico)
        human_frame = tk.Frame(self.root, bg="#14361d")
        human_frame.pack(fill="x", padx=20, pady=4)

        tk.Label(human_frame, text="👤 TUS CARTAS EN MANO (Haz clic en una para jugarla)", font=("Helvetica", 10, "bold"), fg="#3498db", bg="#14361d").pack()

        self.human_cards_frame = tk.Frame(human_frame, bg="#14361d")
        self.human_cards_frame.pack(pady=6)

        # 5. Panel de Acciones (Cantes)
        actions_panel = tk.Frame(self.root, bg="#14361d", bd=2, relief="groove")
        actions_panel.pack(fill="x", padx=10, pady=5)

        tk.Label(actions_panel, text="CANTES / ACCIONES:", font=("Helvetica", 9, "bold"), fg="#ffffff", bg="#14361d").pack(side="left", padx=5)
        self.buttons_container = tk.Frame(actions_panel, bg="#14361d")
        self.buttons_container.pack(side="left", fill="x", expand=True, padx=5, pady=4)

    def _update_display(self):
        p_human = self.state.players[self.human_id]
        p_bot = self.state.players[self.bot_id]
        data = self.state.game_data

        # Actualizar Marcador
        self.score_label.config(text=f"Marcador:  Tú: {p_human.score} pts  |  Robot G1: {p_bot.score} pts  (Objetivo: {self.game.target_score} pts)")

        # 1. NOTIFICAR RESOLUCIÓN DE ENVIDO
        if data.get("envido_just_resolved"):
            data["envido_just_resolved"] = False
            info = data.get("envido_resolved_info", {})
            winner_id = info.get("winner_id")
            w_name = "Tú 🏆" if winner_id == self.human_id else "Robot G1 🤖"
            pts_won = info.get("points_won", 0)

            if info.get("accepted"):
                p1_pts = info.get("p1_pts", 0)
                p2_pts = info.get("p2_pts", 0)
                env_msg = f"🃏 RESOLUCIÓN DEL ENVIDO\n\n- Tus puntos de Envido: {p1_pts} pts\n- Puntos del Robot G1: {p2_pts} pts\n\n🏆 Ganador del Envido: {w_name} (+{pts_won} pts)"
                speak_text_async(f"Tú tienes {p1_pts} de envido y el robot {p2_pts}. Ganó {w_name}.")
            else:
                env_msg = f"🃏 RESOLUCIÓN DEL ENVIDO\n\nEl rival no aceptó el Envido.\n🏆 Ganador del Envido: {w_name} (+{pts_won} pts)"
                speak_text_async(f"No quiso el envido. Puntos para {w_name}.")

            messagebox.showinfo("🃏 Tantos de Envido", env_msg)
            # Limpiar bocadillo de voz tras el envido para evitar confusión
            self.robot_speech_label.config(text="🤖 Robot G1: \"Envido resuelto. Sigamos jugando las cartas.\"")

        # 2. NOTIFICAR FIN DE MANO (Sólo al terminar la mano por completo)
        if data.get("hand_just_finished"):
            data["hand_just_finished"] = False
            last_winner_id = data.get("last_hand_winner_id")
            hand_winner_name = "Tú 🏆" if last_winner_id == self.human_id else "Robot G1 🤖"

            msg = f"🖐️ ¡MANO FINALIZADA!\n\nGanador de esta mano: {hand_winner_name}\n\nMarcador actual:\nTú: {p_human.score} pts  |  Robot G1: {p_bot.score} pts"
            speak_text_async(f"Mano finalizada. Ganó {hand_winner_name}.")
            messagebox.showinfo("🖐️ Fin de Mano", msg)

            # Limpiar bocadillo de voz tras fin de mano
            self.robot_speech_label.config(text="🤖 Robot G1: \"Nueva mano repartida. Tu turno.\"")

        # Limpiar contenedores
        for w in self.robot_hand_frame.winfo_children():
            w.destroy()
        for w in self.human_cards_frame.winfo_children():
            w.destroy()
        for w in self.rounds_container.winfo_children():
            w.destroy()
        for w in self.buttons_container.winfo_children():
            w.destroy()

        # DIBUJAR CARTAS DEL ROBOT (Ocultas o Reveladas en Modo Debug)
        for card in p_bot.hand:
            if self.debug_mode.get():
                img_b = get_card_photo_image(card)
                if img_b:
                    lbl = tk.Label(self.robot_hand_frame, image=img_b, bg="#8e44ad", bd=2, relief="solid")
                    lbl.image = img_b
                else:
                    lbl = tk.Label(self.robot_hand_frame, text=f"🔍 {card.name}", font=("Helvetica", 9, "bold"), bg="#8e44ad", fg="#ffffff", padx=8, pady=8)
            else:
                lbl = tk.Label(self.robot_hand_frame, text="🂠 [Oculta]", font=("Helvetica", 9, "bold"), bg="#34495e", fg="#ecf0f1", padx=10, pady=8, relief="raised")
            lbl.pack(side="left", padx=4)

        # DIBUJAR CARTAS DEL HUMANO EN ABANICO (Botones de fotos reales)
        hand_cards = p_human.hand
        num_cards = len(hand_cards)

        for idx, card in enumerate(hand_cards):
            img = get_card_photo_image(card)
            
            valid_actions = self.game.get_valid_actions(self.state, self.human_id)
            play_act = next((a for a in valid_actions if a.action_type == ActionType.PLAY_CARD and a.payload.get("card") == card), None)

            pady_val = (6 if idx in (0, 2) else 0) if num_cards == 3 else 0

            if img:
                btn = tk.Button(
                    self.human_cards_frame,
                    image=img,
                    bg="#14361d",
                    activebackground="#27ae60",
                    bd=2,
                    relief="raised",
                    state="normal" if play_act else "disabled",
                    command=lambda a=play_act: self._on_human_action(a) if a else None
                )
                btn.image = img
            else:
                btn = tk.Button(
                    self.human_cards_frame,
                    text=f"🃏 {card.name}",
                    font=("Helvetica", 10, "bold"),
                    bg="#f39c12",
                    fg="#2c3e50",
                    padx=12,
                    pady=10,
                    relief="raised",
                    state="normal" if play_act else "disabled",
                    command=lambda a=play_act: self._on_human_action(a) if a else None
                )
            btn.pack(side="left", padx=8, pady=(pady_val, 0))

        # MOSTRAR LAS 3 RONDAS EN LA MESA CENTRAL CON FOTOS REALES
        played_h = data["played_cards"][self.human_id]
        played_b = data["played_cards"][self.bot_id]
        trick_winners = data["trick_winners"]

        for r_idx in range(3):
            r_frame = tk.Frame(self.rounds_container, bg="#1e4d2b", bd=2, relief="groove")
            r_frame.pack(side="left", expand=True, fill="both", padx=5, pady=2)

            tk.Label(r_frame, text=f"RONDA {r_idx + 1}", font=("Helvetica", 10, "bold"), fg="#f1c40f", bg="#1e4d2b").pack(pady=2)

            # Carta jugada por Humano
            if r_idx < len(played_h):
                c_h = played_h[r_idx]
                img_h = get_card_photo_image(c_h)
                if img_h:
                    lbl_h = tk.Label(r_frame, image=img_h, bg="#2980b9", bd=2, relief="solid")
                    lbl_h.image = img_h
                else:
                    lbl_h = tk.Label(r_frame, text=f"Tú:\n{c_h.name}", font=("Helvetica", 9, "bold"), bg="#2980b9", fg="#ffffff", padx=6, pady=6)
            else:
                lbl_h = tk.Label(r_frame, text="Tú:\n---", font=("Helvetica", 9), bg="#2c3e50", fg="#bdc3c7", width=12, height=4)
            lbl_h.pack(pady=2)

            # Carta jugada por Robot
            if r_idx < len(played_b):
                c_b = played_b[r_idx]
                img_b = get_card_photo_image(c_b)
                if img_b:
                    lbl_b = tk.Label(r_frame, image=img_b, bg="#c0392b", bd=2, relief="solid")
                    lbl_b.image = img_b
                else:
                    lbl_b = tk.Label(r_frame, text=f"Robot G1:\n{c_b.name}", font=("Helvetica", 9, "bold"), bg="#c0392b", fg="#ffffff", padx=6, pady=6)
            else:
                lbl_b = tk.Label(r_frame, text="Robot:\n---", font=("Helvetica", 9), bg="#2c3e50", fg="#bdc3c7", width=12, height=4)
            lbl_b.pack(pady=2)

            # Resultado de la ronda
            if r_idx < len(trick_winners):
                w_id = trick_winners[r_idx]
                w_text = "Ganó: Tú 🏆" if w_id == self.human_id else ("Ganó: Robot 🤖" if w_id == self.bot_id else "Parda 🤝")
                tk.Label(r_frame, text=w_text, font=("Helvetica", 9, "bold"), fg="#2ecc71" if w_id != "TIE" else "#f1c40f", bg="#1e4d2b").pack(pady=2)

        # Verificar Fin de Juego
        if self.state.is_terminal:
            winner_name = self.state.players[self.state.winner_id].name if self.state.winner_id else "Nadie"
            speech_end = f"Partida finalizada. Ganador de la partida: {winner_name}."
            speak_text_async(speech_end)

            if messagebox.askyesno("🏆 ¡Partida Finalizada!", f"¡Ganador de la partida: {winner_name}!\n\n¿Querés jugar la revancha?"):
                self._restart_game()
            return

        # Generar Botones de Cantes / Respuestas (Quiero, No Quiero, Truco, Envido, etc.)
        curr_id = self.state.current_player_id
        if curr_id == self.human_id:
            valid_actions = self.game.get_valid_actions(self.state, self.human_id)
            cantes_actions = [a for a in valid_actions if a.action_type != ActionType.PLAY_CARD]
            for act in cantes_actions:
                btn_bg = "#27ae60" if act.name == "Quiero" else ("#c0392b" if act.name == "No Quiero" else "#e67e22")
                btn = tk.Button(
                    self.buttons_container,
                    text=act.name,
                    font=("Helvetica", 9, "bold"),
                    bg=btn_bg,
                    fg="#ffffff",
                    activebackground="#2980b9",
                    command=lambda a=act: self._on_human_action(a)
                )
                btn.pack(side="left", padx=3, pady=2)
        else:
            self.root.after(800, self._process_bot_turn)

    def _on_human_action(self, action: Action):
        self.state, _, _ = self.game.step(self.state, action)
        self._update_display()

    def _process_bot_turn(self):
        if self.state.is_terminal or self.state.current_player_id != self.bot_id:
            return

        valid_actions = self.game.get_valid_actions(self.state, self.bot_id)
        if not valid_actions:
            return

        obs = self.game.get_player_observation(self.state, self.bot_id)
        chosen_action = self.bot.select_action(obs, valid_actions)

        # Generar Frases Gauchas o Carta Jugada
        act_name = chosen_action.name
        if "Jugar" in act_name:
            card_played = act_name.replace('Jugar ', '')
            speech_raw = f"Juego el {card_played}."
            robot_speech_text = f"🤖 Robot G1: \"Juego el {card_played}.\""
        elif any(bid in act_name for bid in ["Envido", "Real", "Falta", "Truco", "Retruco"]):
            bid_key = "TRUCO"
            if "Real" in act_name: bid_key = "REAL_ENVIDO"
            elif "Falta" in act_name: bid_key = "FALTA_ENVIDO"
            elif "Envido" in act_name: bid_key = "ENVIDO"
            elif "Retruco" in act_name: bid_key = "RETRUCO"
            elif "Vale" in act_name: bid_key = "VALE_CUATRO"

            verse = get_random_verse(bid_key)
            speech_raw = verse
            robot_speech_text = f"🤖 Robot G1: \"{verse}\""
        elif "mazo" in act_name:
            speech_raw = "Me voy al mazo."
            robot_speech_text = "🤖 Robot G1: \"Me voy al mazo.\""
        else:
            speech_raw = act_name
            robot_speech_text = f"🤖 Robot G1: \"{act_name}\""

        self.robot_speech_label.config(text=robot_speech_text)
        speak_text_async(speech_raw)

        # Mover el Robot 3D en el Simulador MuJoCo si está abierto
        if self.sim_connected and self.robot_sim:
            def _move_sim():
                try:
                    if any(b in act_name for b in ["Truco", "Envido", "Quiero"]):
                        self.robot_sim.saludar()
                    elif "Jugar" in act_name:
                        self.robot_sim.avanzar(velocidad=0.1, tiempo=0.3)
                    elif "mazo" in act_name:
                        self.robot_sim.girar(velocidad=0.3, tiempo=0.5)
                except Exception:
                    pass
            threading.Thread(target=_move_sim, daemon=True).start()

        self.state, _, _ = self.game.step(self.state, chosen_action)
        self._update_display()

    def _restart_game(self):
        """Reinicia la partida por completo a 0 - 0."""
        self.state = self.game.reset()
        self.robot_speech_label.config(text="🤖 Robot G1: \"¡Partido nuevo iniciado! Repartamos las cartas.\"")
        speak_text_async("Partido nuevo iniciado. Repartamos las cartas.")
        self._update_display()


def main():
    root = tk.Tk()
    app = TrucoTableGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
