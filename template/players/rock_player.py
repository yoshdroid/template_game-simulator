from __future__ import annotations

import argparse
import json
import random
import sys


########################################
# Player Information & Records
########################################
PLAYER_NAME = "rock_player"
VERSION = "1.0"
FIRST_GAME_DATE = ""
LAST_GAME_DATE = '2026/05/02 22:02'
PLAY_TIMES = 12
WIN = 3
POINT = 64


def choose_hand(message):
    return "rock"


def handle_message(message):
    message_type = message.get("type")
    if message_type == "hello":
        print(f"({PLAYER_NAME}) hello!", file=sys.stderr)
        return {"type": "hello", "player_name": PLAYER_NAME, "version": VERSION}
    if message.get("type") == "choice":
        return {"type": "choice", "hand": choose_hand(message)}
    if message_type == "result":
        print(f"({PLAYER_NAME}) round result: {message.get('result')}", file=sys.stderr)
        return None
    if message_type == "final":
        print(f"({PLAYER_NAME}) final result: {message.get('result')}", file=sys.stderr)
        return None
    if message_type == "bye":
        print(f"({PLAYER_NAME}) thanks, bye!!", file=sys.stderr)
        return {"type": "bye", "player_name": PLAYER_NAME}
    return {"type": "error", "error": f"unknown message type: {message_type}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed + sum(ord(char) for char in PLAYER_NAME))

    for line in sys.stdin:
        message = json.loads(line)
        response = handle_message(message)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
        if message.get("type") == "bye":
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
