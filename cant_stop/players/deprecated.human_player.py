# Console prototype. Prefer human_tk_player.py for normal play.
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

try:
    from cant_stop import protocol
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import protocol


########################################
# Player Information & Records
########################################
PLAYER_NAME = "human_player"
VERSION = "0.1"
FIRST_GAME_DATE = ""
LAST_GAME_DATE = ""
PLAY_TIMES = 0
WIN = 0
POINT = 0


def ask_pair(message):
    options = message.get("options") or []
    print(f"dice: {message.get('dice')}", file=sys.stderr)
    for index, option in enumerate(options, start=1):
        print(f"{index}: {option}", file=sys.stderr)
    raw = input("choose pair number> ")
    try:
        selected = options[int(raw) - 1]
    except (ValueError, IndexError):
        selected = options[0]
    return protocol.make_choose_pair_response(selected)


def ask_continue(message):
    print(f"pawns: {message.get('pawns')}", file=sys.stderr)
    raw = input("stop? [y/N]> ").strip().lower()
    action = protocol.STOP if raw in {"y", "yes"} else protocol.ROLL
    return protocol.make_decide_continue_response(action)


def ask_column(message):
    columns = message.get("columns") or []
    print(f"choose one lane from pair {message.get('sums')}: {columns}", file=sys.stderr)
    raw = input("choose lane> ")
    try:
        selected = int(raw)
    except ValueError:
        selected = columns[0]
    if selected not in columns:
        selected = columns[0]
    return protocol.make_choose_column_response(selected)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    for line in sys.stdin:
        message = json.loads(line)
        message_type = protocol.message_type(message)
        if message_type == protocol.HELLO:
            response = protocol.make_hello_response(PLAYER_NAME, VERSION)
        elif message_type == protocol.CHOOSE_PAIR:
            response = ask_pair(message)
        elif message_type == protocol.CHOOSE_COLUMN:
            response = ask_column(message)
        elif message_type == protocol.DECIDE_CONTINUE:
            response = ask_continue(message)
        elif message_type in {protocol.TURN_START, protocol.MOVE, protocol.TURN_END, protocol.BURST, protocol.FINAL}:
            print(f"{message_type}: {message}", file=sys.stderr)
            response = None
        elif message_type == protocol.BYE:
            response = protocol.make_bye_response(PLAYER_NAME)
        else:
            response = protocol.make_error_response(f"unknown message type: {message_type}")

        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
        if message_type == protocol.BYE:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
