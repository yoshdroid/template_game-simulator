from __future__ import annotations

import random

try:
    from .bot_base import protocol, run_player
except ImportError:
    from bot_base import protocol, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "登山家"
VERSION = "1.2"
FIRST_GAME_DATE = '2026/05/03 13:46'
LAST_GAME_DATE = '2026/05/03 15:01'
PLAY_TIMES = 37
WIN = 3
POINT = 34


TOP_DANGER_DEPTH = {
    2: 2,
    3: 2,
    11: 2,
    12: 2,
    4: 3,
    5: 3,
    9: 3,
    10: 3,
    6: 4,
    7: 4,
    8: 4,
}


def _columns(message):
    return {int(column): int(height) for column, height in ((message.get("board") or {}).get("columns") or {}).items()}


def _pawns(message):
    return {int(column): int(position) for column, position in (message.get("pawns") or {}).items()}


def _lane_priority(column: int) -> tuple[int, int, int]:
    if column in {6, 7, 8}:
        tier = 3
    elif column in {2, 12}:
        tier = 2
    else:
        tier = 1
    return tier, -abs(column - 7), column


def _option_priority(option) -> tuple[int, int, int, int]:
    lanes = [int(column) for column in option]
    priority_count = sum(1 for column in lanes if column in {6, 7, 8})
    edge_count = sum(1 for column in lanes if column in {2, 12})
    center_score = -sum(abs(column - 7) for column in lanes)
    return priority_count, edge_count, center_score, sum(lanes)


def has_summit_pawn(message) -> bool:
    columns = _columns(message)
    for column, position in _pawns(message).items():
        if position >= columns.get(column, 999):
            return True
    return False


def has_top_danger_pawn(message) -> bool:
    columns = _columns(message)
    for column, position in _pawns(message).items():
        depth = TOP_DANGER_DEPTH.get(column)
        if depth is None:
            continue
        height = columns.get(column)
        if height is not None and position >= height - depth + 1:
            return True
    return False


def roll_probability(message) -> float:
    if has_summit_pawn(message):
        return 0.0

    probability = 0.60  # ver 1.2
    if has_top_danger_pawn(message):
        probability = 0.65  # ver 1.2
        pawns = _pawns(message)
        if 7 in pawns and pawns[7] <= 8:
            probability += 0.20 # ver 1.2
        if any(lane in pawns and pawns[lane] <= 6 for lane in (6, 8)):
            probability += 0.08  # ver 1.2
    return round(min(probability, 1.0), 2)


def choose_pair(message):
    options = message.get("options") or []
    if not options:
        return []
    return list(max(options, key=_option_priority))


def choose_column(message):
    columns = [int(column) for column in (message.get("columns") or [])]
    if not columns:
        return 7
    return max(columns, key=_lane_priority)


def strategy(message):
    message_type = protocol.message_type(message)
    if message_type == protocol.CHOOSE_PAIR:
        return protocol.make_choose_pair_response(choose_pair(message))
    if message_type == protocol.CHOOSE_COLUMN:
        return protocol.make_choose_column_response(choose_column(message))
    if message_type == protocol.DECIDE_CONTINUE:
        action = protocol.ROLL if random.random() < roll_probability(message) else protocol.STOP
        return protocol.make_decide_continue_response(action)
    return None


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
