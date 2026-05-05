from __future__ import annotations

import argparse
import queue
import re
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from . import protocol
    from .gui import CANVAS_HEIGHT, CANVAS_WIDTH, draw_scene
    from .master import (
        DEFAULT_PLAYER_DIR,
        PlayerProcessPort,
        append_game_log,
        read_player_header,
        update_player_header,
        write_result_file,
    )
    from .simulator import run_game
except ImportError:
    import protocol
    from gui import CANVAS_HEIGHT, CANVAS_WIDTH, draw_scene
    from master import DEFAULT_PLAYER_DIR, PlayerProcessPort, append_game_log, read_player_header, update_player_header, write_result_file
    from simulator import run_game


def resolve_player_path(value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path
    fallback = DEFAULT_PLAYER_DIR / value
    if fallback.exists():
        return fallback
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch a live Treasure Caravan match.")
    parser.add_argument("--casual_match", action="store_true", help="Do not update player header records.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed. Defaults to current datetime.")
    parser.add_argument("--max_actions", type=int, default=200, help="Stop after this many actions.")
    parser.add_argument("--delay", type=int, default=450, help="Milliseconds between event draws.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for each player response.")
    parser.add_argument("--silent", action="store_true", help="Suppress child player stderr logs.")
    parser.add_argument("--no_result_json", action="store_true", help="Skip writing results/*.json and append only game.log.")
    args, unknown = parser.parse_known_args()
    players: dict[int, str] = {}
    index = 0
    while index < len(unknown):
        token = unknown[index]
        match = re.fullmatch(r"--player(\d+)", token)
        if not match:
            parser.error(f"unknown argument: {token}")
        if index + 1 >= len(unknown):
            parser.error(f"{token} requires a path")
        players[int(match.group(1))] = unknown[index + 1]
        index += 2
    args.players = [resolve_player_path(players[key]) for key in sorted(players)]
    if len(args.players) != 4:
        parser.error("exactly --player1 through --player4 are required")
    return args


def event_status(event: dict[str, Any]) -> str:
    event_type = event.get("type")
    player_name = event.get("player_name", "")
    action = event.get("action") or {}
    if event_type == "game_start":
        return "League caravan leaves the city."
    if event_type == "turn_start":
        return f"{player_name}'s turn"
    if event_type == "action_result":
        action_name = action.get("action")
        if action_name == "depart":
            return f"{player_name} departs for {action.get('route')}."
        if action_name == "advance":
            return f"{player_name} advances. danger {event.get('danger_score')} roll {event.get('danger_roll')}"
        if action_name == "dig":
            return f"{player_name} digs treasure +{event.get('cargo_delta', 0)}. danger {event.get('danger_score')} roll {event.get('danger_roll')}"
        if action_name == "rest":
            return f"{player_name} rests and lowers heat."
        if action_name == "return":
            return f"{player_name} returns with +{event.get('banked_delta', 0)} banked."
    if event_type == "bust":
        return f"{player_name} busts and loses {event.get('lost_cargo', 0)} cargo."
    if event_type == "return":
        return f"{player_name} secured treasure at base."
    if event_type == "game_end":
        return f"Winner: {event.get('winner_name')}" if event.get("winner_name") else "Game ended in a tie."
    if event_type == "saved":
        return f"Saved: {event.get('path')}"
    if event_type == "error":
        return f"Error: {event.get('error')}"
    return str(event_type)


class LiveViewer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.events: queue.Queue[dict[str, Any]] = queue.Queue()
        self.done = False
        self.close_enabled = False
        self.players: list[str] = []
        self.active_player_index: int | None = None
        self.last_state: dict[str, Any] | None = None
        self.last_status = "Waiting for game..."

        self.root = tk.Tk()
        self.root.title("Treasure Caravan Live")
        self.root.bind("<Escape>", self._close_if_finished)
        self.canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        draw_scene(self.canvas, self.last_state, status=self.last_status, active_player_index=self.active_player_index)

    def start(self) -> None:
        worker = threading.Thread(target=self._run_match, daemon=True)
        worker.start()
        self.root.after(self.args.delay, self._poll_events)
        self.root.mainloop()

    def _run_match(self) -> None:
        now = datetime.now()
        seed = self.args.seed if self.args.seed is not None else int(now.strftime("%Y%m%d%H%M%S"))
        player_paths = [path.resolve() for path in self.args.players]
        ports: list[PlayerProcessPort] = []
        try:
            for path in player_paths:
                if not path.exists():
                    raise FileNotFoundError(f"player file not found: {path}")
            headers = [read_player_header(path) for path in player_paths]
            casual_match = self.args.casual_match or len(set(player_paths)) != len(player_paths)
            ports = [
                PlayerProcessPort(path, seed + index, timeout_seconds=self.args.timeout, silent=self.args.silent)
                for index, path in enumerate(player_paths)
            ]
            result = run_game(tuple(ports), seed=seed, max_actions=self.args.max_actions, on_event=self.events.put)
            result_path = None
            if not self.args.no_result_json:
                result_path = write_result_file(result, Path(__file__).resolve().parent.parent / "results")
            for port in ports:
                port.request(protocol.make_bye_request())
            if not casual_match:
                now_text = now.strftime("%Y/%m/%d %H:%M")
                for header, player_result in zip(headers, result.results):
                    update_player_header(header.path, now_text, player_result.final_result, player_result.banked)
            append_game_log(now, result)
            self.events.put({"type": "saved", "path": str(result_path or "game.log"), "state": result.final_state})
        except Exception as exc:
            self.events.put({"type": "error", "error": str(exc), "state": self.last_state})
        finally:
            for port in ports:
                port.close()
            self.events.put({"type": "viewer_done"})

    def _poll_events(self) -> None:
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            if not self.done:
                self.root.after(self.args.delay, self._poll_events)
            return

        if event.get("type") == "viewer_done":
            self.done = True
            self.close_enabled = True
            self.root.after(self.args.delay, self._poll_events)
            return

        if event.get("type") == "game_start":
            self.players = list(event.get("players") or [])
        if "player_index" in event:
            self.active_player_index = int(event["player_index"])
        elif event.get("type") in {"game_start", "game_end", "saved", "error"}:
            self.active_player_index = None
        self.last_status = event_status(event)
        self.last_state = event.get("state") or self.last_state
        draw_scene(
            self.canvas,
            self.last_state,
            players=self.players,
            status=self.last_status,
            active_player_index=self.active_player_index,
        )
        self.root.after(self.args.delay, self._poll_events)

    def _close_if_finished(self, _event: tk.Event) -> None:
        if self.close_enabled:
            self.root.destroy()


def main() -> int:
    LiveViewer(parse_args()).start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
