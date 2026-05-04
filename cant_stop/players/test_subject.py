from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

try:
    from .bot_base import protocol, stable_seed
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from bot_base import protocol, stable_seed


########################################
# Player Information & Records
########################################
PLAYER_NAME = "実験体ｘ"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/04 22:27'
LAST_GAME_DATE = '2026/05/04 22:28'
PLAY_TIMES = 2
WIN = 1
POINT = 4


CENTER_LANES = {6, 7, 8}
EDGE_LANES = {2, 12}
MIDDLE_LANES = {3, 4, 5, 9, 10, 11}
SIDE_MIDDLE_LANES = {4, 5, 9, 10}
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


def _scores(message: dict[str, Any]) -> list[int]:
    return [int(score) for score in ((message.get("board") or {}).get("scores") or [])]


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


def _other_progress(message: dict[str, Any]) -> list[dict[int, int]]:
    player_index = _player_index(message)
    return [player for index, player in enumerate(_progress(message)) if index != player_index]


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


def _is_second_from_top(message: dict[str, Any], column: int) -> bool:
    height = (_columns(message) or COLUMN_HEIGHTS).get(column)
    return height is not None and _my_progress(message).get(column) == height - 1


def _is_within_top_three(message: dict[str, Any], column: int) -> bool:
    height = (_columns(message) or COLUMN_HEIGHTS).get(column)
    return height is not None and _my_progress(message).get(column, 0) >= height - 2


def critical_priority(message: dict[str, Any], lanes: list[int]) -> int:
    second_count = sum(1 for column in lanes if _is_second_from_top(message, column))
    if second_count == len(lanes):
        return 3
    if second_count:
        return 2
    if len(set(lanes)) == 1 and _is_within_top_three(message, lanes[0]):
        return 1
    return 0


def _has_other_at_least(message: dict[str, Any], column: int, position: int) -> bool:
    return any(player.get(column, 0) >= position for player in _other_progress(message))


def _has_other_near_top(message: dict[str, Any], column: int, depth: int) -> bool:
    height = (_columns(message) or COLUMN_HEIGHTS).get(column)
    if height is None:
        return False
    return any(player.get(column, 0) >= height - depth + 1 for player in _other_progress(message))


def _has_other_above_me(message: dict[str, Any], column: int) -> bool:
    my_position = _my_progress(message).get(column, 0)
    return any(player.get(column, 0) > my_position for player in _other_progress(message))


def new_lane_priority(message: dict[str, Any], column: int) -> tuple[int, int, int]:
    my_progress = _my_progress(message)
    if column in CENTER_LANES and not _has_other_at_least(message, column, 4):
        tier = 5
    elif column in EDGE_LANES and not _has_other_near_top(message, column, 2):
        tier = 4
    elif column in my_progress and not _has_other_above_me(message, column):
        tier = 3
    elif column in MIDDLE_LANES:
        tier = 2
    elif column in CENTER_LANES | EDGE_LANES:
        tier = 1
    else:
        tier = 0
    return tier, -abs(column - 7), column


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


def is_late_game(message: dict[str, Any]) -> bool:
    scores = _scores(message)
    return any(score >= 2 for score in scores) or sum(scores) >= 4


def has_summit_pawn(message: dict[str, Any]) -> bool:
    columns = _columns(message) or COLUMN_HEIGHTS
    return any(position >= columns.get(column, 999) for column, position in _pawns(message).items())


def _option_priority(message: dict[str, Any], option: list[int]) -> tuple[int, int, int, tuple[tuple[int, int, int], ...], int]:
    lanes = [int(column) for column in option]
    pawns = _pawns(message)
    projected = apply_option(message, pawns, lanes)
    existing_count = sum(1 for column in lanes if column in pawns)
    new_priorities = tuple(sorted((new_lane_priority(message, column) for column in lanes if column not in pawns), reverse=True))
    late_edge_count = sum(1 for column in lanes if column in EDGE_LANES)
    return critical_priority(message, lanes), existing_count, turn_score(message, projected) + (late_edge_count * 2 if is_late_game(message) else 0), new_priorities, sum(lanes)


def choose_pair(message: dict[str, Any]) -> list[int]:
    options = message.get("options") or []
    if not options:
        return []
    return list(max(options, key=lambda option: _option_priority(message, list(option))))


def choose_column(message: dict[str, Any]) -> int:
    columns = [int(column) for column in (message.get("columns") or [])]
    if not columns:
        return 7
    pawns = _pawns(message)
    return max(
        columns,
        key=lambda column: (
            turn_score(message, apply_option(message, pawns, (column,))),
            new_lane_priority(message, column),
        ),
    )


def base_roll_probability(message: dict[str, Any]) -> float:
    pawns = _pawns(message)
    center_count = sum(1 for column in pawns if column in CENTER_LANES)
    side_middle_count = sum(1 for column in pawns if column in SIDE_MIDDLE_LANES)
    center_claimed = any(column in CENTER_LANES for column in _claimed_by(message))

    if is_late_game(message):
        if center_count >= 2:
            return 1.0
        if center_count == 1:
            return 0.90
        if side_middle_count >= 2:
            return 0.90
        if side_middle_count == 1:
            return 0.80
        return 0.80

    if center_claimed:
        if center_count == 1:
            return 0.80
        if center_count >= 2:
            return 0.85
        if side_middle_count == 1:
            return 0.70
        if side_middle_count >= 2:
            return 0.85
        return 0.20

    if center_count == 1:
        return 0.80
    if center_count >= 2:
        return 0.95
    return 0.35


def roll_probability(message: dict[str, Any], roll_count: int = 0) -> float:
    pawns = _pawns(message)
    if len(pawns) < 3:
        return 1.0
    if has_summit_pawn(message):
        return 0.0
    if is_late_game(message):
        return round(max(base_roll_probability(message) - roll_count * 0.03, 0.0), 2)
    if turn_score(message, pawns) >= 28:
        return 0.0
    return round(max(base_roll_probability(message) - roll_count * 0.05, 0.0), 2)


class TestSubjectPlayer:
    def __init__(self) -> None:
        self.roll_count = 0

    def reset_turn(self) -> None:
        self.roll_count = 0

    def strategy(self, message: dict[str, Any]) -> dict[str, Any] | None:
        message_type = protocol.message_type(message)
        if message_type == protocol.CHOOSE_PAIR:
            return protocol.make_choose_pair_response(choose_pair(message))
        if message_type == protocol.CHOOSE_COLUMN:
            return protocol.make_choose_column_response(choose_column(message))
        if message_type == protocol.DECIDE_CONTINUE:
            probability = roll_probability(message, self.roll_count)
            action = protocol.ROLL if random.random() < probability else protocol.STOP
            if action == protocol.ROLL:
                self.roll_count += 1
            return protocol.make_decide_continue_response(action)
        return None


def run_player() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    seeded = stable_seed(PLAYER_NAME, args.seed)
    if seeded is not None:
        random.seed(seeded)

    player = TestSubjectPlayer()
    print(f"({PLAYER_NAME}) ready", file=sys.stderr)
    for line in sys.stdin:
        message = json.loads(line)
        message_type = protocol.message_type(message)
        if message_type == protocol.HELLO:
            response = protocol.make_hello_response(PLAYER_NAME, VERSION)
        elif message_type in {protocol.CHOOSE_PAIR, protocol.CHOOSE_COLUMN, protocol.DECIDE_CONTINUE}:
            response = player.strategy(message)
        elif message_type == protocol.TURN_START:
            player.reset_turn()
            response = None
        elif message_type in {protocol.TURN_END, protocol.BURST}:
            player.reset_turn()
            response = None
        elif message_type == protocol.BYE:
            response = protocol.make_bye_response(PLAYER_NAME)
        else:
            response = None

        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
        if message_type == protocol.BYE:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(run_player())
