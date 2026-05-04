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
    from .gui import BACKGROUND_PATH, CANVAS_HEIGHT, CANVAS_WIDTH, draw_scene
    from .master import PlayerProcessPort, append_game_log, read_player_header, update_player_header, write_result_file
    from .simulator import COLUMN_HEIGHTS, run_game
except ImportError:
    import protocol
    from gui import BACKGROUND_PATH, CANVAS_HEIGHT, CANVAS_WIDTH, draw_scene
    from master import PlayerProcessPort, append_game_log, read_player_header, update_player_header, write_result_file
    from simulator import COLUMN_HEIGHTS, run_game


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch a live Can't Stop match.")
    parser.add_argument("--casual_match", action="store_true", help="Do not update player header records.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed. Defaults to current datetime.")
    parser.add_argument("--step", type=int, default=None, help="Stop simulator after this many recorded decisions.")
    parser.add_argument("--delay", type=int, default=350, help="Milliseconds between event draws.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for each player response.")
    parser.add_argument("--burst_pause", type=float, default=0.5, help="Seconds to pause after a burst event.")
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
    args.players = [Path(players[key]) for key in sorted(players)]
    if len(args.players) != 4:
        parser.error("exactly --player1 through --player4 are required")
    return args


def empty_board() -> dict[str, Any]:
    return {
        "columns": COLUMN_HEIGHTS,
        "progress": [{}, {}, {}, {}],
        "claimed_by": {},
        "scores": [0, 0, 0, 0],
        "pawns": {},
    }


def event_status(event: dict[str, Any]) -> str:
    event_type = event.get("type")
    player_name = event.get("player_name", "")
    if event_type == "game_start":
        return "Game start"
    if event_type == "turn_start":
        return f"{player_name} turn"
    if event_type == "dice":
        return f"{player_name} rolls {event.get('dice')}"
    if event_type == "move":
        return f"{player_name} moves {event.get('sums')}"
    if event_type == "choose_column":
        return f"{player_name} chooses lane {event.get('selected_column')} from {event.get('columns')}"
    if event_type == "continue":
        return f"{player_name} rolls again"
    if event_type == "burst":
        return f"{player_name} burst"
    if event_type == "turn_end":
        claimed = event.get("claimed") or []
        return f"{player_name} stops" + (f" and claims {claimed}" if claimed else "")
    if event_type == "game_end":
        return f"Winner: {event.get('winner_name')}" if event.get("winner_name") else "Game stopped"
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
        self.last_board = empty_board()
        self.last_status = "Waiting for game..."

        self.root = tk.Tk()
        self.root.title("Can't Stop Live")
        self.root.bind("<Escape>", self._close_if_finished)
        self.canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        if BACKGROUND_PATH.exists():
            background = tk.PhotoImage(file=str(BACKGROUND_PATH))
            self.canvas.background = background
        draw_scene(self.canvas, self.last_board, status=self.last_status, active_player_index=self.active_player_index)

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
            result = run_game(
                tuple(ports),
                seed=seed,
                step=self.args.step,
                on_event=self.events.put,
                burst_pause_seconds=self.args.burst_pause,
            )
            result_path = None
            if not self.args.no_result_json:
                result_path = write_result_file(result, Path(__file__).resolve().parent.parent / "results")
            for port in ports:
                port.request(protocol.make_bye_request())
            if not casual_match:
                now_text = now.strftime("%Y/%m/%d %H:%M")
                for header, player_result in zip(headers, result.results):
                    update_player_header(header.path, now_text, player_result.final_result, player_result.points)
            append_game_log(now, result)
            if result_path is None:
                self.events.put({"type": "saved", "path": "game.log", "board": result.final_board})
            else:
                self.events.put({"type": "saved", "path": str(result_path), "board": result.final_board})
        except Exception as exc:
            self.events.put({"type": "error", "error": str(exc), "board": self.last_board})
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
        if event.get("type") == "saved":
            self.last_status = f"Saved: {event.get('path')}"
        else:
            self.last_status = event_status(event)
        self.last_board = event.get("board") or self.last_board
        draw_scene(
            self.canvas,
            self.last_board,
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
