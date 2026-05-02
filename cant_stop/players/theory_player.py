from __future__ import annotations

import random

from bot_base import choose_highest_option, protocol, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "theory_player"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/03 01:00'
LAST_GAME_DATE = '2026/05/03 07:54'
PLAY_TIMES = 11
WIN = 2
POINT = 11


def strategy(message):
    if protocol.message_type(message) == protocol.CHOOSE_PAIR:
        return protocol.make_choose_pair_response(choose_highest_option(message))
    if protocol.message_type(message) == protocol.CHOOSE_COLUMN:
        columns = message.get("columns") or []
        selected = min(columns, key=lambda column: (abs(int(column) - 7), int(column)))
        return protocol.make_choose_column_response(selected)
    if protocol.message_type(message) == protocol.DECIDE_CONTINUE:
        pawn_columns = {int(column) for column in (message.get("pawns") or {})}
        stop_probability = 0.20 if pawn_columns & {6, 7, 8} else 0.50
        action = protocol.STOP if random.random() < stop_probability else protocol.ROLL
        return protocol.make_decide_continue_response(action)
    return None


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
