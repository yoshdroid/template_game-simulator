from __future__ import annotations

import random
from typing import Any

try:
    from .bot_base import protocol, run_player
except ImportError:
    from bot_base import protocol, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "rule_of_28"
VERSION = "1.0"
FIRST_GAME_DATE = ""
LAST_GAME_DATE = ""
PLAY_TIMES = 0
WIN = 0
POINT = 0


COLUMN_HEIGHTS = {
    2: 3,
    3: 5,
    4: 7,
    5: 9,
    6: 11,
    7: 13,
    8: 11,
    9: 9,
    10: 7,
    11: 5,
    12: 3,
}
MARK_VALUES = {2: 12, 3: 10, 4: 8, 5: 6, 6: 4, 7: 2, 8: 4, 9: 6, 10: 8, 11: 10, 12: 12}
ADVANCE_VALUES = {2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6}


def _columns(message: dict[str, Any]) -> dict[int, int]:
    return {int(column): int(height) for column, height in ((message.get("board") or {}).get("columns") or {}).items()}


def _pawns(message: dict[str, Any]) -> dict[int, int]:
    return {int(column): int(position) for column, position in (message.get("pawns") or {}).items()}


def _claimed_by(message: dict[str, Any]) -> dict[int, int]:
    return {int(column): int(owner) for column, owner in ((message.get("board") or {}).get("claimed_by") or {}).items()}


def _progress(message: dict[str, Any]) -> list[dict[int, int]]:
    return [
        {int(column): int(position) for column, position in player.items()}
        for player in ((message.get("board") or {}).get("progress") or [])
    ]


def _player_index(message: dict[str, Any]) -> int:
    return int(message.get("player_index", 0))


def _my_progress(message: dict[str, Any]) -> dict[int, int]:
    progress = _progress(message)
    player_index = _player_index(message)
    return progress[player_index] if player_index < len(progress) else {}


def can_advance(message: dict[str, Any], pawns: dict[int, int], column: int) -> bool:
    columns = _columns(message) or COLUMN_HEIGHTS
    if column not in columns or column in _claimed_by(message):
        return False
    if column in pawns:
        return pawns[column] < columns[column]
    if len(pawns) >= 3:
        return False
    return _my_progress(message).get(column, 0) + 1 <= columns[column]


def apply_option(message: dict[str, Any], pawns: dict[int, int], option: list[int] | tuple[int, ...]) -> dict[int, int]:
    result = dict(pawns)
    for raw_column in option:
        column = int(raw_column)
        if not can_advance(message, result, column):
            continue
        if column in result:
            result[column] += 1
        else:
            result[column] = _my_progress(message).get(column, 0) + 1
    return result


def column_turn_score(message: dict[str, Any], column: int, position: int) -> int:
    start = _my_progress(message).get(column, 0)
    if position <= start:
        return 0
    if start == 0:
        return MARK_VALUES[column] + ADVANCE_VALUES[column] * (position - 1)
    return ADVANCE_VALUES[column] * (position - start)


def turn_score(message: dict[str, Any], pawns: dict[int, int] | None = None) -> int:
    current_pawns = _pawns(message) if pawns is None else pawns
    score = sum(column_turn_score(message, column, position) for column, position in current_pawns.items())
    columns = set(current_pawns)
    if len(columns) == 3:
        if all(column % 2 == 1 for column in columns):
            score += 2
        if all(column % 2 == 0 for column in columns):
            score -= 2
        if all(column < 8 for column in columns) or all(column > 6 for column in columns):
            score += 4
    return score


def has_summit_pawn(message: dict[str, Any]) -> bool:
    columns = _columns(message) or COLUMN_HEIGHTS
    return any(position >= columns.get(column, 999) for column, position in _pawns(message).items())


def choose_pair(message: dict[str, Any]) -> list[int]:
    options = message.get("options") or []
    if not options:
        return []
    pawns = _pawns(message)
    return list(max(options, key=lambda option: (turn_score(message, apply_option(message, pawns, option)), sum(option))))


def choose_column(message: dict[str, Any]) -> int:
    columns = [int(column) for column in (message.get("columns") or [])]
    if not columns:
        return 7
    pawns = _pawns(message)
    return max(columns, key=lambda column: (turn_score(message, apply_option(message, pawns, (column,))), column))


def roll_probability(message: dict[str, Any]) -> float:
    pawns = _pawns(message)
    if len(pawns) < 3:
        return 1.0
    if has_summit_pawn(message):
        return 0.0
    return 0.0 if turn_score(message, pawns) >= 28 else 1.0


def strategy(message: dict[str, Any]) -> dict[str, Any] | None:
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
