from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Any

try:
    from .simulator import COLUMN_HEIGHTS, COLUMNS, PLAYER_COLORS
except ImportError:
    from simulator import COLUMN_HEIGHTS, COLUMNS, PLAYER_COLORS


BACKGROUND_PATH = Path(__file__).with_name("background.png")
CANVAS_WIDTH = 1100
CANVAS_HEIGHT = 760
BOARD_LEFT = 90
BOARD_RIGHT = 1010
BOARD_TOP = 80
BOARD_BOTTOM = 690


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
        canvas.create_text(x, BOARD_BOTTOM + 28, text=str(column), fill="#ffffff", font=("Segoe UI", 14, "bold"))
        for position in range(1, height + 1):
            y = _cell_y(position, height)
            canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline="#ffffff", width=2)

    progress = board.get("progress") or []
    for player_index, player_progress in enumerate(progress):
        color = PLAYER_COLORS[player_index % len(PLAYER_COLORS)]
        for raw_column, position in player_progress.items():
            column = int(raw_column)
            if column not in COLUMN_HEIGHTS:
                continue
            x = _lane_x(COLUMNS.index(column)) + (player_index - 1.5) * 9
            y = _cell_y(int(position), COLUMN_HEIGHTS[column])
            canvas.create_oval(x - 8, y - 8, x + 8, y + 8, fill=color, outline="#111111")

    claimed_by = board.get("claimed_by") or {}
    for raw_column, player_index in claimed_by.items():
        column = int(raw_column)
        if column not in COLUMN_HEIGHTS:
            continue
        x = _lane_x(COLUMNS.index(column))
        y = _cell_y(COLUMN_HEIGHTS[column], COLUMN_HEIGHTS[column])
        color = PLAYER_COLORS[int(player_index) % len(PLAYER_COLORS)]
        canvas.create_rectangle(x - 18, y - 18, x + 18, y + 18, fill=color, outline="#ffffff", width=2)

    pawns = board.get("pawns") or {}
    for raw_column, position in pawns.items():
        column = int(raw_column)
        if column not in COLUMN_HEIGHTS:
            continue
        x = _lane_x(COLUMNS.index(column))
        y = _cell_y(int(position), COLUMN_HEIGHTS[column])
        canvas.create_oval(x - 12, y - 12, x + 12, y + 12, fill="#ffffff", outline="#111111", width=2)

    scores = board.get("scores") or []
    for index, score in enumerate(scores):
        color = PLAYER_COLORS[index % len(PLAYER_COLORS)]
        name = players[index] if players and index < len(players) else f"P{index + 1}"
        canvas.create_text(
            28,
            42 + index * 28,
            text=f"{name}: {score}",
            fill=color,
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        )

    if status:
        canvas.create_text(
            CANVAS_WIDTH // 2,
            28,
            text=status,
            fill="#ffffff",
            font=("Segoe UI", 15, "bold"),
        )


def draw_scene(canvas: tk.Canvas, board: dict[str, Any], players: list[str] | None = None, status: str = "") -> None:
    canvas.delete("all")
    background = getattr(canvas, "background", None)
    if background is not None:
        canvas.create_image(0, 0, image=background, anchor="nw")
    else:
        canvas.configure(bg="#20242a")
    draw_board(canvas, board, players=players, status=status)


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
