from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Any

try:
    from .simulator import COLUMN_HEIGHTS, COLUMNS, PLAYER_COLORS
except ImportError:
    from simulator import COLUMN_HEIGHTS, COLUMNS, PLAYER_COLORS


BACKGROUND_PATH = Path(__file__).with_name("background.png")
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 600
BOARD_AREA_SIZE = 600
PANEL_LEFT = 600
BOARD_LEFT = 46
BOARD_RIGHT = 554
BOARD_TOP = 44
BOARD_BOTTOM = 540


def _lane_x(index: int) -> float:
    gap = (BOARD_RIGHT - BOARD_LEFT) / (len(COLUMNS) - 1)
    return BOARD_LEFT + gap * index


def _cell_y(position: int, height: int) -> float:
    if height <= 1:
        return BOARD_BOTTOM
    gap = (BOARD_BOTTOM - BOARD_TOP) / (height - 1)
    return BOARD_BOTTOM - gap * (position - 1)


def draw_board(canvas: tk.Canvas, board: dict[str, Any], players: list[str] | None = None, status: str = "") -> None:
    for index, column in enumerate(COLUMNS):
        height = COLUMN_HEIGHTS[column]
        x = _lane_x(index)
        canvas.create_line(x, BOARD_TOP, x, BOARD_BOTTOM, fill="#f7f7f7", width=2)
        canvas.create_text(x, BOARD_BOTTOM + 24, text=str(column), fill="#ffffff", font=("Segoe UI", 12, "bold"))
        for position in range(1, height + 1):
            y = _cell_y(position, height)
            canvas.create_oval(x - 7, y - 7, x + 7, y + 7, outline="#ffffff", width=2)

    progress = board.get("progress") or []
    for player_index, player_progress in enumerate(progress):
        color = PLAYER_COLORS[player_index % len(PLAYER_COLORS)]
        for raw_column, position in player_progress.items():
            column = int(raw_column)
            if column not in COLUMN_HEIGHTS:
                continue
            x = _lane_x(COLUMNS.index(column)) + (player_index - 1.5) * 7
            y = _cell_y(int(position), COLUMN_HEIGHTS[column])
            canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=color, outline="#111111")

    claimed_by = board.get("claimed_by") or {}
    for raw_column, player_index in claimed_by.items():
        column = int(raw_column)
        if column not in COLUMN_HEIGHTS:
            continue
        x = _lane_x(COLUMNS.index(column))
        y = _cell_y(COLUMN_HEIGHTS[column], COLUMN_HEIGHTS[column])
        color = PLAYER_COLORS[int(player_index) % len(PLAYER_COLORS)]
        canvas.create_rectangle(x - 14, y - 14, x + 14, y + 14, fill=color, outline="#ffffff", width=2)

    pawns = board.get("pawns") or {}
    for raw_column, position in pawns.items():
        column = int(raw_column)
        if column not in COLUMN_HEIGHTS:
            continue
        x = _lane_x(COLUMNS.index(column))
        y = _cell_y(int(position), COLUMN_HEIGHTS[column])
        canvas.create_oval(x - 10, y - 10, x + 10, y + 10, fill="#ffffff", outline="#111111", width=2)


def draw_side_panel(
    canvas: tk.Canvas,
    board: dict[str, Any],
    players: list[str] | None = None,
    status: str = "",
    active_player_index: int | None = None,
) -> None:
    canvas.create_rectangle(PANEL_LEFT, 0, CANVAS_WIDTH, CANVAS_HEIGHT, fill="#f4f4f4", outline="")
    canvas.create_line(PANEL_LEFT, 0, PANEL_LEFT, CANVAS_HEIGHT, fill="#e3e3e3", width=2)
    canvas.create_text(
        PANEL_LEFT + 18,
        28,
        text="Players",
        fill="#000000",
        anchor="w",
        font=("Meiryo UI", 15, "bold"),
    )
    scores = board.get("scores") or []
    for index, score in enumerate(scores):
        color = PLAYER_COLORS[index % len(PLAYER_COLORS)]
        name = players[index] if players and index < len(players) else f"P{index + 1}"
        y = 66 + index * 38
        canvas.create_rectangle(PANEL_LEFT + 18, y - 9, PANEL_LEFT + 36, y + 9, fill=color, outline="#000000")
        text_id = canvas.create_text(
            PANEL_LEFT + 46,
            y,
            text=f"{name}: {score}",
            fill="#000000",
            anchor="w",
            font=("Meiryo UI", 12, "bold"),
        )
        if active_player_index == index:
            bbox = canvas.bbox(text_id)
            if bbox is not None:
                canvas.create_line(bbox[0], bbox[3] + 3, bbox[2], bbox[3] + 3, fill=color, width=3)

    claimed_by = board.get("claimed_by") or {}
    claimed_text = ", ".join(f"{column}:P{int(owner) + 1}" for column, owner in sorted(claimed_by.items(), key=lambda item: int(item[0])))
    canvas.create_text(PANEL_LEFT + 18, 235, text="Claimed", fill="#000000", anchor="w", font=("Segoe UI", 13, "bold"))
    canvas.create_text(
        PANEL_LEFT + 18,
        262,
        text=claimed_text or "-",
        fill="#000000",
        anchor="nw",
        width=250,
        font=("Segoe UI", 11),
    )

    canvas.create_text(PANEL_LEFT + 18, 360, text="Current Event", fill="#000000", anchor="w", font=("Segoe UI", 13, "bold"))
    canvas.create_text(
        PANEL_LEFT + 18,
        388,
        text=status or "-",
        fill="#000000",
        anchor="nw",
        width=250,
        font=("Segoe UI", 12),
    )


def draw_scene(
    canvas: tk.Canvas,
    board: dict[str, Any],
    players: list[str] | None = None,
    status: str = "",
    active_player_index: int | None = None,
) -> None:
    canvas.delete("all")
    background = getattr(canvas, "background", None)
    if background is not None:
        canvas.create_image(0, 0, image=background, anchor="nw")
    else:
        canvas.create_rectangle(0, 0, BOARD_AREA_SIZE, CANVAS_HEIGHT, fill="#20242a", outline="")
    draw_board(canvas, board, players=players, status=status)
    draw_side_panel(canvas, board, players=players, status=status, active_player_index=active_player_index)


def show_board(board: dict[str, Any]) -> None:
    root = tk.Tk()
    root.title("Can't Stop Board")
    canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    if BACKGROUND_PATH.exists():
        background = tk.PhotoImage(file=str(BACKGROUND_PATH))
        canvas.background = background
    else:
        canvas.configure(bg="#20242a")
    draw_scene(canvas, board)
    root.mainloop()
