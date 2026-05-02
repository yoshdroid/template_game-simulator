# Console prototype. Prefer human_tk_player.py for normal play.
from __future__ import annotations

import argparse
import json
import random
import sys


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
    return {"type": "choose_pair", "sums": selected}


def ask_continue(message):
    print(f"pawns: {message.get('pawns')}", file=sys.stderr)
    raw = input("stop? [y/N]> ").strip().lower()
    return {"type": "decide_continue", "action": "stop" if raw in {"y", "yes"} else "roll"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    for line in sys.stdin:
        message = json.loads(line)
        message_type = message.get("type")
        if message_type == "hello":
            response = {"type": "hello", "player_name": PLAYER_NAME, "version": VERSION}
        elif message_type == "choose_pair":
            response = ask_pair(message)
        elif message_type == "decide_continue":
            response = ask_continue(message)
        elif message_type in {"turn_start", "move", "turn_end", "burst", "final"}:
            print(f"{message_type}: {message}", file=sys.stderr)
            response = None
        elif message_type == "bye":
            response = {"type": "bye", "player_name": PLAYER_NAME}
        else:
            response = {"type": "error", "error": f"unknown message type: {message_type}"}

        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
        if message_type == "bye":
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
