from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Any

try:
    from .simulator import PLAYER_COLORS, ROUTES, TARGET_BANKED
except ImportError:
    from simulator import PLAYER_COLORS, ROUTES, TARGET_BANKED


CANVAS_WIDTH = 900
CANVAS_HEIGHT = 600
BOARD_WIDTH = 600
PANEL_LEFT = 600
ASSET_PATH = Path(__file__).resolve().parent / "assets" / "concept_treasure_caravan.png"

ROUTE_LAYOUT = {
    "oasis": {"y": 155, "color": "#3aa76d", "label": "Oasis"},
    "ruins": {"y": 300, "color": "#b88746", "label": "Ruins"},
    "mirage": {"y": 445, "color": "#c95f4a", "label": "Mirage"},
}
PLAYER_OFFSETS = ((-10, -10), (10, -10), (-10, 10), (10, 10))


def _empty_state() -> dict[str, Any]:
    return {
        "action_count": 0,
        "current_player": 0,
        "target_banked": TARGET_BANKED,
        "routes": ROUTES,
        "players": [
            {"location": "base", "route": None, "depth": 0, "cargo": 0, "banked": 0, "heat": 0, "dug_sites": [], "busts": 0}
            for _ in range(4)
        ],
    }


def _route_x(depth: int, length: int) -> float:
    if length <= 1:
        return 120
    left = 124
    right = 536
    return left + (right - left) * ((depth - 1) / (length - 1))


def _draw_background(canvas: tk.Canvas) -> None:
    canvas.create_rectangle(0, 0, BOARD_WIDTH, CANVAS_HEIGHT, fill="#f6d18b", outline="")
    canvas.create_rectangle(PANEL_LEFT, 0, CANVAS_WIDTH, CANVAS_HEIGHT, fill="#f7f7f4", outline="")
    canvas.create_line(PANEL_LEFT, 0, PANEL_LEFT, CANVAS_HEIGHT, fill="#d8d1c4", width=2)
    canvas.create_oval(-120, -80, 260, 190, fill="#f0b96d", outline="")
    canvas.create_polygon(0, 510, 180, 470, 340, 520, 520, 462, 600, 492, 600, 600, 0, 600, fill="#d59d5b", outline="")
    canvas.create_text(32, 34, text="Treasure Caravan", anchor="w", fill="#4a2d16", font=("Segoe UI", 22, "bold"))
    canvas.create_text(34, 66, text=f"Goal {TARGET_BANKED} banked treasure", anchor="w", fill="#5f452e", font=("Segoe UI", 10))


def _draw_routes(canvas: tk.Canvas, state: dict[str, Any]) -> None:
    routes = state.get("routes") or ROUTES
    for route_id, layout in ROUTE_LAYOUT.items():
        route = routes[route_id]
        y = layout["y"]
        length = int(route["length"])
        color = layout["color"]
        canvas.create_text(42, y, text=layout["label"], anchor="w", fill="#2d2218", font=("Segoe UI", 14, "bold"))
        canvas.create_line(124, y, 536, y, fill="#76543a", width=6, capstyle=tk.ROUND)
        for depth in range(1, length + 1):
            x = _route_x(depth, length)
            treasure = route["treasure"][depth - 1]
            canvas.create_oval(x - 18, y - 18, x + 18, y + 18, fill="#fff4c9", outline=color, width=3)
            canvas.create_text(x, y, text=str(treasure), fill="#3c2a1c", font=("Segoe UI", 10, "bold"))
        canvas.create_text(540, y - 32, text=f"risk +{route['risk']}", anchor="e", fill="#5b3928", font=("Segoe UI", 10, "bold"))

    canvas.create_rectangle(36, 242, 94, 358, fill="#d6f0ff", outline="#4d7a92", width=3)
    canvas.create_text(65, 228, text="Base", fill="#24465c", font=("Segoe UI", 13, "bold"))


def _draw_players_on_board(canvas: tk.Canvas, state: dict[str, Any], active_player_index: int | None) -> None:
    players = state.get("players") or []
    base_slots = ((54, 266), (76, 266), (54, 336), (76, 336))
    for index, player in enumerate(players):
        color = PLAYER_COLORS[index % len(PLAYER_COLORS)]
        if player.get("location") == "route" and player.get("route") in ROUTE_LAYOUT:
            route_id = str(player["route"])
            route = (state.get("routes") or ROUTES)[route_id]
            x = _route_x(int(player.get("depth", 1)), int(route["length"]))
            y = ROUTE_LAYOUT[route_id]["y"]
            dx, dy = PLAYER_OFFSETS[index % len(PLAYER_OFFSETS)]
            x += dx
            y += dy
        else:
            x, y = base_slots[index % len(base_slots)]
        radius = 9 if index != active_player_index else 12
        canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color, outline="#1b1b1b", width=2)
        canvas.create_text(x, y, text=str(index + 1), fill="#ffffff", font=("Segoe UI", 8, "bold"))


def _player_line(canvas: tk.Canvas, x: int, y: int, index: int, name: str, player: dict[str, Any], active: bool) -> None:
    color = PLAYER_COLORS[index % len(PLAYER_COLORS)]
    canvas.create_rectangle(x, y - 10, x + 18, y + 8, fill=color, outline="#111111")
    text_id = canvas.create_text(x + 28, y, text=name, anchor="w", fill="#111111", font=("Meiryo UI", 11, "bold"))
    if active:
        bbox = canvas.bbox(text_id)
        if bbox is not None:
            canvas.create_line(bbox[0], bbox[3] + 2, bbox[2], bbox[3] + 2, fill=color, width=3)
    route = player.get("route") or "base"
    depth = player.get("depth", 0)
    canvas.create_text(
        x + 28,
        y + 22,
        text=f"banked {player.get('banked', 0)}  cargo {player.get('cargo', 0)}  heat {player.get('heat', 0)}",
        anchor="w",
        fill="#222222",
        font=("Segoe UI", 9),
    )
    canvas.create_text(
        x + 28,
        y + 40,
        text=f"{route} depth {depth}  busts {player.get('busts', 0)}",
        anchor="w",
        fill="#444444",
        font=("Segoe UI", 9),
    )


def _draw_panel(
    canvas: tk.Canvas,
    state: dict[str, Any],
    names: list[str] | None,
    status: str,
    active_player_index: int | None,
) -> None:
    canvas.create_text(PANEL_LEFT + 18, 30, text="Players", anchor="w", fill="#111111", font=("Meiryo UI", 15, "bold"))
    players = state.get("players") or []
    for index, player in enumerate(players):
        name = names[index] if names and index < len(names) else f"P{index + 1}"
        _player_line(canvas, PANEL_LEFT + 18, 68 + index * 76, index, name, player, active_player_index == index)

    canvas.create_text(PANEL_LEFT + 18, 392, text="Current Event", anchor="w", fill="#111111", font=("Segoe UI", 13, "bold"))
    canvas.create_text(
        PANEL_LEFT + 18,
        420,
        text=status or "-",
        anchor="nw",
        width=254,
        fill="#111111",
        font=("Meiryo UI", 11),
    )
    canvas.create_text(
        PANEL_LEFT + 18,
        552,
        text=f"Action {state.get('action_count', 0)}",
        anchor="w",
        fill="#444444",
        font=("Segoe UI", 10),
    )


def draw_scene(
    canvas: tk.Canvas,
    state: dict[str, Any] | None = None,
    players: list[str] | None = None,
    status: str = "",
    active_player_index: int | None = None,
) -> None:
    state = state or _empty_state()
    canvas.delete("all")
    _draw_background(canvas)
    _draw_routes(canvas, state)
    _draw_players_on_board(canvas, state, active_player_index)
    _draw_panel(canvas, state, players, status, active_player_index)


def show_state(state: dict[str, Any] | None = None) -> None:
    root = tk.Tk()
    root.title("Treasure Caravan")
    canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    draw_scene(canvas, state)
    root.mainloop()
