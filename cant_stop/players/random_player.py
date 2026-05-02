from __future__ import annotations

import random

from bot_base import run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "cant_stop_random_player"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/03 01:00'
LAST_GAME_DATE = '2026/05/03 01:03'
PLAY_TIMES = 7
WIN = 0
POINT = 7


def strategy(message):
    if message.get("type") == "choose_pair":
        options = message.get("options") or []
        return {"type": "choose_pair", "sums": random.choice(options)}
    if message.get("type") == "decide_continue":
        return {"type": "decide_continue", "action": random.choice(["stop", "roll"])}
    return None


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
