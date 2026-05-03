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
PLAYER_NAME = "Brain"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/03 16:32'
LAST_GAME_DATE = '2026/05/03 22:03'
PLAY_TIMES = 43
WIN = 24
POINT = 92


CENTER_LANES = {6, 7, 8}
EDGE_LANES = {2, 12}
MIDDLE_LANES = {3, 4, 5, 9, 10, 11}
SIDE_MIDDLE_LANES = {4, 5, 9, 10}


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


def _is_second_from_top(message: dict[str, Any], column: int) -> bool:
    height = _columns(message).get(column)
    return height is not None and _my_progress(message).get(column) == height - 1


def _is_within_top_three(message: dict[str, Any], column: int) -> bool:
    height = _columns(message).get(column)
    return height is not None and _my_progress(message).get(column, 0) >= height - 2


def _critical_priority(message: dict[str, Any], lanes: list[int]) -> int:
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
    height = _columns(message).get(column)
    if height is None:
        return False
    return any(player.get(column, 0) >= height - depth + 1 for player in _other_progress(message))


def _has_other_above_me(message: dict[str, Any], column: int) -> bool:
    my_position = _my_progress(message).get(column, 0)
    return any(player.get(column, 0) > my_position for player in _other_progress(message))


def _new_lane_priority(message: dict[str, Any], column: int) -> tuple[int, int, int]:
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


def _option_priority(message: dict[str, Any], option: list[int]) -> tuple[int, int, tuple[tuple[int, int, int], ...], int]:
    lanes = [int(column) for column in option]
    critical = _critical_priority(message, lanes)
    pawns = _pawns(message)
    existing_pawn_count = sum(1 for column in lanes if column in pawns)
    new_priorities = tuple(sorted((_new_lane_priority(message, column) for column in lanes if column not in pawns), reverse=True))
    return critical, existing_pawn_count, new_priorities, sum(lanes)


def choose_pair(message: dict[str, Any]) -> list[int]:
    options = message.get("options") or []
    if not options:
        return []
    return list(max(options, key=lambda option: _option_priority(message, list(option))))


def choose_column(message: dict[str, Any]) -> int:
    columns = [int(column) for column in (message.get("columns") or [])]
    if not columns:
        return 7
    return max(columns, key=lambda column: _new_lane_priority(message, column))


def has_summit_pawn(message: dict[str, Any]) -> bool:
    columns = _columns(message)
    for column, position in _pawns(message).items():
        if position >= columns.get(column, 999):
            return True
    return False


def _base_roll_probability(message: dict[str, Any]) -> float:
    pawns = _pawns(message)
    scores = _scores(message)
    score_total = sum(scores)
    center_count = sum(1 for column in pawns if column in CENTER_LANES)
    side_middle_count = sum(1 for column in pawns if column in SIDE_MIDDLE_LANES)
    center_claimed = any(column in CENTER_LANES for column in _claimed_by(message))

    if score_total > 3:
        if center_count == 1:
            return 0.85
        if center_count >= 2:
            return 1.00
        if side_middle_count == 1:
            return 0.65
        if side_middle_count >= 2:
            return 0.90
        return 0.25

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

    if score_total == 0:
        if center_count == 1:
            return 0.80
        if center_count >= 2:
            return 0.95
        return 0.35

    if center_count == 1:
        return 0.80
    if center_count >= 2:
        return 0.95
    return 0.35


def roll_probability(message: dict[str, Any], roll_count: int = 0) -> float:
    if len(_pawns(message)) < 3:
        return 1.0
    if has_summit_pawn(message):
        return 0.0
    return round(max(_base_roll_probability(message) - roll_count * 0.05, 0.0), 2)


class BrainPlayer:
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

    player = BrainPlayer()
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
            print(f"({PLAYER_NAME}) turn start", file=sys.stderr)
            response = None
        elif message_type == protocol.MOVE:
            print(f"({PLAYER_NAME}) move sums={message.get('sums')} pawns={message.get('pawns')}", file=sys.stderr)
            response = None
        elif message_type in {protocol.TURN_END, protocol.BURST}:
            player.reset_turn()
            print(f"({PLAYER_NAME}) {message_type}", file=sys.stderr)
            response = None
        elif message_type == protocol.FINAL:
            print(f"({PLAYER_NAME}) final winner={message.get('winner_name')}", file=sys.stderr)
            response = None
        elif message_type == protocol.BYE:
            print(f"({PLAYER_NAME}) bye", file=sys.stderr)
            response = protocol.make_bye_response(PLAYER_NAME)
        else:
            response = protocol.make_error_response(f"unknown message type: {message_type}")

        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
        if message_type == protocol.BYE:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(run_player())


# 実装指示文
#・「どちらのレーンも上から2番目に自分のコマがある」「どちらかのレーンの上から2番目に自分のコマがある」「x x(xに入る数字のレーンの上から3番目までに自分のコマがある)」の3パターンは最優先でとる
#・上の3パターンに当てはまらない限りできるだけ新しいポーンを出さず、すでにポーンが出ているレーンを優先する。
#・新しいポーンを出すとき、優先順位を「4マス以上進んでいる自分以外のプレイヤーがいない6 7 8のいずれか」「上から2番目までに自分以外のプレイヤーがいない2 12のどちらか」「自分より上に他のプレイヤーがおらず、かつ自分のコマが既にあるレーン」「3 4 5 9 10 11のいずれかのレーン」「2 6 7 8 12のいずれかのレーン」の順番にする
#・いずれかのポーンが登頂していて、かつ自分のポーンが3個ある場合は即座にストップする
#・自分のポーンが3個になるまではストップしない
#・誰もまだポイントを獲得していない時、ロール継続確率は6 7 8のレーンに自分のポーンが1つあれば80%、2つか3つあれば95%。それ以外は35%。
#・6 7 8のレーンのいずれかが埋まっていたら、ロール継続確率は6 7 8のレーンに自分のポーンが1つあれば80%、2つあれば85%。6 7 8のレーンにポーンが無く、4 5 9 10のレーンのいずれかに自分のポーンが1つあれば70%、2つか3つあれば85%。それ以外は20%。
#・4人のプレイヤーのポイントの合計が3を超えたら、ロール継続確率は6 7 8のレーンに自分のポーンが1つあれば85%、2つあれば100%。6 7 8のレーンにポーンが無く、4 5 9 10のレーンのいずれかに自分のポーンが1つあれば65%、2つか3つあれば90%。それ以外は25%。
#・ロールするたび、ロール継続確率が5%低下（重複あり）。このロール継続確率の低下はターンエンドかバーストでリセット