from __future__ import annotations

import random

from bot_base import choose_highest_option, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "aggressive_player"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/03 01:00'
LAST_GAME_DATE = '2026/05/03 01:03'
PLAY_TIMES = 7
WIN = 5
POINT = 17


def strategy(message):
    if message.get("type") == "choose_pair":
        return {"type": "choose_pair", "sums": choose_highest_option(message)}
    if message.get("type") == "decide_continue":
        return {"type": "decide_continue", "action": "stop" if random.random() < 0.25 else "roll"}
    return None


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
