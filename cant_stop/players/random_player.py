from __future__ import annotations

import random

try:
    from .bot_base import protocol, run_player
except ImportError:
    from bot_base import protocol, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "cant_stop_random_player"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/03 01:00'
LAST_GAME_DATE = '2026/05/03 14:57'
PLAY_TIMES = 32
WIN = 2
POINT = 27


def strategy(message):
    if protocol.message_type(message) == protocol.CHOOSE_PAIR:
        options = message.get("options") or []
        return protocol.make_choose_pair_response(random.choice(options))
    if protocol.message_type(message) == protocol.DECIDE_CONTINUE:
        return protocol.make_decide_continue_response(random.choice([protocol.STOP, protocol.ROLL]))
    return None


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
