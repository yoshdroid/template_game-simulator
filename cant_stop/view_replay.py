from __future__ import annotations

import argparse
import json
import tkinter as tk
from pathlib import Path
from typing import Any

try:
    from .gui import BACKGROUND_PATH, CANVAS_HEIGHT, CANVAS_WIDTH, draw_scene
    from .live_view import empty_board, event_status
except ImportError:
    from gui import BACKGROUND_PATH, CANVAS_HEIGHT, CANVAS_WIDTH, draw_scene
    from live_view import empty_board, event_status


class ReplayViewer:
    def __init__(self, result_json: Path, delay: int, autoplay: bool) -> None:
        self.result_json = result_json
        self.delay = delay
        self.autoplay = autoplay
        self.data = json.loads(result_json.read_text(encoding="utf-8"))
        self.events: list[dict[str, Any]] = list(self.data.get("events") or [])
        if not self.events:
            self.events = [{"type": "final_board", "board": self.data["final_board"]}]
        self.players: list[str] = list(self.data.get("players") or [])
        self.index = 0

        self.root = tk.Tk()
        self.root.title(f"Can't Stop Replay - {result_json.name}")
        self.canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        if BACKGROUND_PATH.exists():
            background = tk.PhotoImage(file=str(BACKGROUND_PATH))
            self.canvas.background = background

        self.root.bind("<space>", self._toggle_play)
        self.root.bind("<Right>", self._next_event)
        self.root.bind("<Left>", self._previous_event)
        self.root.bind("<Home>", self._first_event)
        self.root.bind("<End>", self._last_event)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

    def start(self) -> None:
        self._draw_current()
        if self.autoplay:
            self.root.after(self.delay, self._play_next)
        self.root.mainloop()

    def _status(self, event: dict[str, Any]) -> str:
        play_state = "Playing" if self.autoplay else "Paused"
        return f"{play_state} {self.index + 1}/{len(self.events)} - {event_status(event)}"

    def _draw_current(self) -> None:
        event = self.events[self.index]
        board = event.get("board") or empty_board()
        draw_scene(self.canvas, board, players=self.players, status=self._status(event))

    def _play_next(self) -> None:
        if not self.autoplay:
            return
        if self.index < len(self.events) - 1:
            self.index += 1
            self._draw_current()
            self.root.after(self.delay, self._play_next)
        else:
            self.autoplay = False
            self._draw_current()

    def _toggle_play(self, _event: tk.Event) -> None:
        self.autoplay = not self.autoplay
        self._draw_current()
        if self.autoplay:
            self.root.after(self.delay, self._play_next)

    def _next_event(self, _event: tk.Event) -> None:
        self.autoplay = False
        self.index = min(self.index + 1, len(self.events) - 1)
        self._draw_current()

    def _previous_event(self, _event: tk.Event) -> None:
        self.autoplay = False
        self.index = max(self.index - 1, 0)
        self._draw_current()

    def _first_event(self, _event: tk.Event) -> None:
        self.autoplay = False
        self.index = 0
        self._draw_current()

    def _last_event(self, _event: tk.Event) -> None:
        self.autoplay = False
        self.index = len(self.events) - 1
        self._draw_current()


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a Can't Stop result file.")
    parser.add_argument("result_json", type=Path)
    parser.add_argument("--delay", type=int, default=350, help="Milliseconds between replay events.")
    parser.add_argument("--paused", action="store_true", help="Start paused.")
    args = parser.parse_args()
    ReplayViewer(args.result_json, args.delay, autoplay=not args.paused).start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
