from __future__ import annotations

import random

from bot_base import choose_highest_option, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "theory_player"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/03 01:00'
LAST_GAME_DATE = '2026/05/03 01:03'
PLAY_TIMES = 7
WIN = 1
POINT = 7


def strategy(message):
    if message.get("type") == "choose_pair":
        return {"type": "choose_pair", "sums": choose_highest_option(message)}
    if message.get("type") == "decide_continue":
        pawn_columns = {int(column) for column in (message.get("pawns") or {})}
        stop_probability = 0.50 if pawn_columns & {6, 7, 8} else 0.80
        return {"type": "decide_continue", "action": "stop" if random.random() < stop_probability else "roll"}
    return None


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
