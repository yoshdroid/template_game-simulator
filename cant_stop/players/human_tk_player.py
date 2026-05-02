from __future__ import annotations

import argparse
import json
import queue
import random
import sys
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any


########################################
# Player Information & Records
########################################
PLAYER_NAME = "human_tk_player"
VERSION = "0.1"
FIRST_GAME_DATE = '2026/05/03 01:15'
LAST_GAME_DATE = '2026/05/03 01:15'
PLAY_TIMES = 1
WIN = 1
POINT = 3


PLAYER_COLORS = ("red", "green", "blue", "yellow")


class HumanTkPlayer:
    def __init__(self) -> None:
        self.inbox: queue.Queue[tuple[dict[str, Any], queue.Queue[dict[str, Any]] | None]] = queue.Queue()
        self.root = tk.Tk()
        self.root.title(PLAYER_NAME)
        self.root.geometry("420x520")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.player_index: int | None = None
        self.color = "black"
        self.closed = False

        self.title_var = tk.StringVar(value="Waiting for game...")
        self.status_var = tk.StringVar(value="")
        self.dice_var = tk.StringVar(value="Dice: -")
        self.pawns_var = tk.StringVar(value="Pawns: -")
        self.scores_var = tk.StringVar(value="Scores: -")
        self.detail_visible = False

        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.pack(fill="both", expand=True)

        ttk.Label(root_frame, textvariable=self.title_var, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        self.status_label = ttk.Label(root_frame, textvariable=self.status_var, wraplength=380)
        self.status_label.pack(anchor="w", pady=(4, 12))
        self.dice_label = ttk.Label(root_frame, textvariable=self.dice_var)
        self.pawns_label = ttk.Label(root_frame, textvariable=self.pawns_var, wraplength=380)
        self.scores_label = ttk.Label(root_frame, textvariable=self.scores_var, wraplength=380)

        ttk.Separator(root_frame).pack(fill="x", pady=8)
        self.controls = ttk.Frame(root_frame)
        self.controls.pack(fill="both", expand=True)
        self._hide_details()
        self._show_waiting_controls()

    def start(self) -> int:
        reader = threading.Thread(target=self._read_stdin, daemon=True)
        reader.start()
        self.root.after(50, self._poll_inbox)
        self.root.mainloop()
        return 0

    def _read_stdin(self) -> None:
        for line in sys.stdin:
            if self.closed:
                break
            message = json.loads(line)
            message_type = message.get("type")
            if message_type in {"hello", "choose_pair", "decide_continue", "bye"}:
                response_queue: queue.Queue[dict[str, Any]] = queue.Queue()
                self.inbox.put((message, response_queue))
                response = response_queue.get()
                print(json.dumps(response, ensure_ascii=False), flush=True)
                if message_type == "bye":
                    break
            else:
                self.inbox.put((message, None))

    def _poll_inbox(self) -> None:
        try:
            message, response_queue = self.inbox.get_nowait()
        except queue.Empty:
            if not self.closed:
                self.root.after(50, self._poll_inbox)
            return

        self._handle_message(message, response_queue)
        if not self.closed:
            self.root.after(50, self._poll_inbox)

    def _handle_message(self, message: dict[str, Any], response_queue: queue.Queue[dict[str, Any]] | None) -> None:
        message_type = message.get("type")
        self._update_state(message)
        if message_type == "hello":
            self.player_index = int(message.get("player_index", 0))
            self.color = PLAYER_COLORS[self.player_index % len(PLAYER_COLORS)]
            self.root.title(f"{PLAYER_NAME} P{self.player_index + 1} ({self.color})")
            self.title_var.set(f"P{self.player_index + 1} {PLAYER_NAME} ({self.color})")
            self.status_var.set("Connected. Waiting for your turn.")
            self._hide_details()
            self._show_waiting_controls()
            self._respond(response_queue, {"type": "hello", "player_name": PLAYER_NAME, "version": VERSION})
        elif message_type == "choose_pair":
            self._show_pair_choices(message, response_queue)
        elif message_type == "decide_continue":
            self._show_continue_choices(response_queue)
        elif message_type == "turn_start":
            self.status_var.set("Your turn started.")
            self._show_details()
            self._show_waiting_controls("Waiting for dice...")
        elif message_type == "move":
            self.status_var.set(f"Moved {message.get('sums')}.")
            self._show_details()
            self._show_waiting_controls("Waiting for next decision...")
        elif message_type == "turn_end":
            self.status_var.set(f"Turn ended. Claimed: {message.get('claimed') or []}")
            self._hide_details()
            self._show_waiting_controls()
        elif message_type == "burst":
            self.status_var.set(f"BURST! Dice: {message.get('dice')}")
            self._show_details()
            self._show_waiting_controls("Burst!")
            self.root.after(500, self._show_off_turn)
        elif message_type == "final":
            winner = message.get("winner_name") or "unfinished"
            self.status_var.set(f"Game finished. Winner: {winner}")
            self._show_details()
            self._show_waiting_controls("Game finished")
        elif message_type == "bye":
            self.status_var.set("Bye.")
            self._respond(response_queue, {"type": "bye", "player_name": PLAYER_NAME})
            self.root.after(300, self._on_close)
        else:
            self._respond(response_queue, {"type": "error", "error": f"unknown message type: {message_type}"})

    def _show_pair_choices(self, message: dict[str, Any], response_queue: queue.Queue[dict[str, Any]] | None) -> None:
        self._clear_controls()
        options = message.get("options") or []
        self._show_details()
        self.status_var.set("Choose a dice pairing.")
        ttk.Label(self.controls, text="Pair options", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        for option in options:
            ttk.Button(
                self.controls,
                text=f"{option[0]} + {option[1]}",
                command=lambda selected=option: self._respond(response_queue, {"type": "choose_pair", "sums": selected}),
            ).pack(fill="x", pady=4)

    def _show_continue_choices(self, response_queue: queue.Queue[dict[str, Any]] | None) -> None:
        self._clear_controls()
        self._show_details()
        self.status_var.set("Roll again or stop and bank the pawns?")
        ttk.Button(
            self.controls,
            text="Stop",
            command=lambda: self._respond(response_queue, {"type": "decide_continue", "action": "stop"}),
        ).pack(fill="x", pady=6)
        ttk.Button(
            self.controls,
            text="Roll",
            command=lambda: self._respond(response_queue, {"type": "decide_continue", "action": "roll"}),
        ).pack(fill="x", pady=6)

    def _update_state(self, message: dict[str, Any]) -> None:
        if "dice" in message:
            self.dice_var.set(f"Dice: {message['dice']}")
        if "pawns" in message:
            self.pawns_var.set(f"Pawns: {message['pawns']}")
        board = message.get("board") or {}
        if "scores" in board:
            self.scores_var.set(f"Scores: {board['scores']}")
        if "pawns" in board:
            self.pawns_var.set(f"Pawns: {board['pawns']}")

    def _clear_controls(self) -> None:
        for child in self.controls.winfo_children():
            child.destroy()

    def _show_waiting_controls(self, text: str = "Buttons are disabled outside your turn.") -> None:
        self._clear_controls()
        button = ttk.Button(self.controls, text=text, state="disabled")
        button.pack(fill="x", pady=6)

    def _show_details(self) -> None:
        if self.detail_visible:
            return
        self.dice_label.pack(anchor="w", pady=2)
        self.pawns_label.pack(anchor="w", pady=2)
        self.scores_label.pack(anchor="w", pady=(2, 12))
        self.detail_visible = True

    def _hide_details(self) -> None:
        if not self.detail_visible:
            return
        self.dice_label.pack_forget()
        self.pawns_label.pack_forget()
        self.scores_label.pack_forget()
        self.detail_visible = False

    def _show_off_turn(self) -> None:
        self.status_var.set("Waiting for your next turn.")
        self._hide_details()
        self._show_waiting_controls()

    def _respond(self, response_queue: queue.Queue[dict[str, Any]] | None, response: dict[str, Any]) -> None:
        self._show_waiting_controls("Waiting...")
        if response_queue is not None:
            response_queue.put(response)

    def _on_close(self) -> None:
        self.closed = True
        self.root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed + sum(ord(char) for char in PLAYER_NAME))
    return HumanTkPlayer().start()


if __name__ == "__main__":
    raise SystemExit(main())
