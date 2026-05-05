from __future__ import annotations

try:
    from .bot_base import choose_random_action, run_player
except ImportError:
    from bot_base import choose_random_action, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "Caravan Random"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/05 22:21'
LAST_GAME_DATE = '2026/05/05 22:21'
PLAY_TIMES = 1
WIN = 0
POINT = 5


def strategy(message):
    return choose_random_action(message)


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
