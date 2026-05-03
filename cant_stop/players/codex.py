from __future__ import annotations

import random
from itertools import product
from typing import Any

try:
    from .bot_base import protocol, run_player
except ImportError:
    from bot_base import protocol, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "CODEX"
VERSION = "0.1"
FIRST_GAME_DATE = ""
LAST_GAME_DATE = ""
PLAY_TIMES = 0
WIN = 0
POINT = 0


COLUMNS = tuple(range(2, 13))
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
PAIR_INDEXES = (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2)))
ROLLS = tuple(product(range(1, 7), repeat=4))
SUM_FREQUENCY = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}


def _columns(message: dict[str, Any]) -> dict[int, int]:
    return {int(column): int(height) for column, height in ((message.get("board") or {}).get("columns") or {}).items()}


def _pawns(message: dict[str, Any]) -> dict[int, int]:
    return {int(column): int(position) for column, position in (message.get("pawns") or {}).items()}


def _scores(message: dict[str, Any]) -> list[int]:
    return [int(score) for score in ((message.get("board") or {}).get("scores") or [])]


def _progress(message: dict[str, Any]) -> list[dict[int, int]]:
    return [
        {int(column): int(position) for column, position in player.items()}
        for player in ((message.get("board") or {}).get("progress") or [])
    ]


def _claimed_by(message: dict[str, Any]) -> dict[int, int]:
    return {int(column): int(owner) for column, owner in ((message.get("board") or {}).get("claimed_by") or {}).items()}


def _player_index(message: dict[str, Any]) -> int:
    return int(message.get("player_index", 0))


def _my_progress(message: dict[str, Any]) -> dict[int, int]:
    progress = _progress(message)
    player_index = _player_index(message)
    return progress[player_index] if player_index < len(progress) else {}


def _other_progress(message: dict[str, Any]) -> list[dict[int, int]]:
    player_index = _player_index(message)
    return [player for index, player in enumerate(_progress(message)) if index != player_index]


def dice_pair_options(dice: tuple[int, int, int, int]) -> tuple[tuple[int, int], ...]:
    options = []
    for first_pair, second_pair in PAIR_INDEXES:
        first_sum = dice[first_pair[0]] + dice[first_pair[1]]
        second_sum = dice[second_pair[0]] + dice[second_pair[1]]
        option = tuple(sorted((first_sum, second_sum)))
        if option not in options:
            options.append(option)
    return tuple(options)


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
    for column in option:
        column = int(column)
        if not can_advance(message, result, column):
            continue
        if column in result:
            result[column] += 1
        else:
            result[column] = _my_progress(message).get(column, 0) + 1
    return result


def has_legal_option(message: dict[str, Any], pawns: dict[int, int], dice: tuple[int, int, int, int]) -> bool:
    for option in dice_pair_options(dice):
        if apply_option(message, pawns, option) != pawns:
            return True
    return False


def bust_probability(message: dict[str, Any], pawns: dict[int, int] | None = None) -> float:
    current_pawns = dict(_pawns(message) if pawns is None else pawns)
    busts = sum(1 for dice in ROLLS if not has_legal_option(message, current_pawns, dice))
    return busts / len(ROLLS)


def _column_value(message: dict[str, Any], column: int, position: int | None = None) -> float:
    columns = _columns(message) or COLUMN_HEIGHTS
    height = columns.get(column, COLUMN_HEIGHTS.get(column, 99))
    my_position = _my_progress(message).get(column, 0) if position is None else position
    remaining = max(height - my_position, 0)
    probability_weight = SUM_FREQUENCY.get(column, 0) / 6
    summit_bonus = 45.0 if remaining == 0 else 0.0
    near_top_bonus = max(0, 7 - remaining) * 3.0
    committed_bonus = 4.0 if column in _my_progress(message) else 0.0
    pawn_bonus = 5.0 if column in _pawns(message) else 0.0
    opponent_pressure = max((player.get(column, 0) for player in _other_progress(message)), default=0)
    lead_bonus = 2.0 if my_position >= opponent_pressure else -2.5
    return summit_bonus + near_top_bonus + committed_bonus + pawn_bonus + probability_weight + lead_bonus


def _state_value(message: dict[str, Any], pawns: dict[int, int]) -> float:
    value = 0.0
    for column, position in pawns.items():
        value += _column_value(message, column, position)
    value -= len([column for column in pawns if column not in _my_progress(message)]) * 1.2
    value -= bust_probability(message, pawns) * 18.0
    return value


def choose_pair(message: dict[str, Any]) -> list[int]:
    options = message.get("options") or []
    if not options:
        return []
    pawns = _pawns(message)
    return list(max(options, key=lambda option: (_state_value(message, apply_option(message, pawns, option)), sum(option))))


def choose_column(message: dict[str, Any]) -> int:
    columns = [int(column) for column in (message.get("columns") or [])]
    if not columns:
        return 7
    pawns = _pawns(message)
    return max(columns, key=lambda column: (_state_value(message, apply_option(message, pawns, (column,))), _column_value(message, column)))


def has_summit_pawn(message: dict[str, Any]) -> bool:
    columns = _columns(message) or COLUMN_HEIGHTS
    return any(position >= columns.get(column, 999) for column, position in _pawns(message).items())


def _bank_value(message: dict[str, Any]) -> float:
    return sum(_column_value(message, column, position) for column, position in _pawns(message).items())


def roll_probability(message: dict[str, Any]) -> float:
    pawns = _pawns(message)
    scores = _scores(message)
    my_score = scores[_player_index(message)] if _player_index(message) < len(scores) else 0
    max_other_score = max((score for index, score in enumerate(scores) if index != _player_index(message)), default=0)

    if has_summit_pawn(message):
        return 0.0
    if not pawns:
        return 1.0

    bust = bust_probability(message, pawns)
    bank = _bank_value(message)
    late_game = my_score >= 2 or max_other_score >= 2 or sum(scores) >= 5
    threshold = 0.36
    if len(pawns) == 1:
        threshold += 0.22
    elif len(pawns) == 2:
        threshold += 0.10
    if bank >= 35:
        threshold -= 0.12
    elif bank >= 25:
        threshold -= 0.07
    if late_game:
        threshold -= 0.08
    if my_score < max_other_score:
        threshold += 0.05

    if bust >= threshold:
        return 0.0
    return round(min(0.98, max(0.10, 1.0 - bust * 0.75)), 2)


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
