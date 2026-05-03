from __future__ import annotations

import random

try:
    from .bot_base import protocol, run_player
except ImportError:
    from bot_base import protocol, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "ギャンブラー"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/03 14:40'
LAST_GAME_DATE = '2026/05/03 16:42'
PLAY_TIMES = 39
WIN = 10
POINT = 62


STOP_STEPS = {
    2: 1,
    12: 1,
    3: 2,
    4: 2,
    10: 2,
    11: 2,
    5: 3,
    9: 3,
    6: 4,
    7: 4,
    8: 4,
}


def _columns(message):
    return {int(column): int(height) for column, height in ((message.get("board") or {}).get("columns") or {}).items()}


def _pawns(message):
    return {int(column): int(position) for column, position in (message.get("pawns") or {}).items()}


def _scores(message):
    return [int(score) for score in ((message.get("board") or {}).get("scores") or [])]


def _player_progress(message):
    player_index = int(message.get("player_index", 0))
    progress = (message.get("board") or {}).get("progress") or []
    if player_index >= len(progress):
        return {}
    return {int(column): int(position) for column, position in progress[player_index].items()}


def _lane_priority(column: int) -> tuple[int, int, int]:
    if column in {2, 12}:
        tier = 3
    elif column in {6, 7, 8}:
        tier = 2
    else:
        tier = 1
    return tier, -abs(column - 7), column


def _option_priority(option) -> tuple[int, int, int, int]:
    lanes = [int(column) for column in option]
    edge_count = sum(1 for column in lanes if column in {2, 12})
    center_count = sum(1 for column in lanes if column in {6, 7, 8})
    center_score = -sum(abs(column - 7) for column in lanes)
    return edge_count, center_count, center_score, sum(lanes)


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


def has_summit_pawn(message) -> bool:
    columns = _columns(message)
    for column, position in _pawns(message).items():
        if position >= columns.get(column, 999):
            return True
    return False


def is_late_game(message) -> bool:
    scores = _scores(message)
    return any(score >= 2 for score in scores) or sum(scores) >= 4


def advanced_steps(message, column: int, position: int) -> int:
    return position - _player_progress(message).get(column, 0)


def reached_stop_steps(message) -> bool:
    for column, position in _pawns(message).items():
        threshold = STOP_STEPS.get(column)
        if threshold is not None and advanced_steps(message, column, position) >= threshold:
            return True
    return False


def roll_probability(message) -> float:
    if has_summit_pawn(message):
        return 0.0
    if is_late_game(message):
        return 0.80
    if reached_stop_steps(message):
        return 0.0
    return 1.0


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
