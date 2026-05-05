from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

try:
    from .bot_base import choose_highest_option, choose_random_column, protocol, stable_seed
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from bot_base import choose_highest_option, choose_random_column, protocol, stable_seed


########################################
# Player Information & Records
########################################
PLAYER_NAME = "ドレッドノート"
VERSION = "1.1"
FIRST_GAME_DATE = '2026/05/05 17:51'
LAST_GAME_DATE = '2026/05/05 18:12'
PLAY_TIMES = 276
WIN = 100
POINT = 499


CENTER_LANES = {6, 7, 8}
EDGE_LANES = {2, 12}
DANGER_LANES = {2, 3, 11, 12}


def _columns(message: dict[str, Any]) -> dict[int, int]:
    return {int(column): int(height) for column, height in ((message.get("board") or {}).get("columns") or {}).items()}


def _pawns(message: dict[str, Any]) -> dict[int, int]:
    return {int(column): int(position) for column, position in (message.get("pawns") or {}).items()}


def has_summit_pawn(message: dict[str, Any]) -> bool:
    columns = _columns(message)
    for column, position in _pawns(message).items():
        if position >= columns.get(column, 999):
            return True
    return False


def base_roll_probability(message: dict[str, Any]) -> float:
    pawn_columns = set(_pawns(message))
    center_count = len(pawn_columns & CENTER_LANES)
    edge_count = len(pawn_columns & EDGE_LANES)
    danger_count = len(pawn_columns & DANGER_LANES)

    if center_count == 3:
        return 1.10
    if center_count == 2:
        return 0.80 if edge_count else 0.90
    if center_count == 1:
        if danger_count == 0:
            return 0.70
        if danger_count == 1:
            return 0.50
        return 0.35
    if danger_count == 0:
        return 0.55
    if danger_count == 1:
        return 0.45
    if danger_count == 2:
        return 0.30
    return 0.20


def roll_probability(message: dict[str, Any], roll_count: int = 0) -> float:
    pawns = _pawns(message)
    if len(pawns) < 3:
        return 1.0
    if has_summit_pawn(message):
        return 0.0
    return round(max(base_roll_probability(message) - roll_count * 0.05, 0.0), 2)


class DreadnoughtPlayer:
    def __init__(self) -> None:
        self.roll_count = 0

    def reset_turn(self) -> None:
        self.roll_count = 0

    def strategy(self, message: dict[str, Any]) -> dict[str, Any] | None:
        message_type = protocol.message_type(message)
        if message_type == protocol.CHOOSE_PAIR:
            return protocol.make_choose_pair_response(choose_highest_option(message))
        if message_type == protocol.CHOOSE_COLUMN:
            return protocol.make_choose_column_response(choose_random_column(message))
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

    player = DreadnoughtPlayer()
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
