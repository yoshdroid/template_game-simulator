from __future__ import annotations

import random

try:
    from .bot_base import choose_highest_option, protocol, run_player
except ImportError:
    from bot_base import choose_highest_option, protocol, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "cautious_player"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/03 01:00'
LAST_GAME_DATE = '2026/05/03 07:54'
PLAY_TIMES = 11
WIN = 1
POINT = 5


def strategy(message):
    if protocol.message_type(message) == protocol.CHOOSE_PAIR:
        return protocol.make_choose_pair_response(choose_highest_option(message))
    if protocol.message_type(message) == protocol.DECIDE_CONTINUE:
        action = protocol.STOP if random.random() < 0.65 else protocol.ROLL
        return protocol.make_decide_continue_response(action)
    return None


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
