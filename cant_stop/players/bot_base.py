from __future__ import annotations

import argparse
import json
import random
import sys
from typing import Any, Callable


Strategy = Callable[[dict[str, Any]], dict[str, Any] | None]


def stable_seed(name: str, seed: int | None) -> int | None:
    if seed is None:
        return None
    return seed + sum(ord(char) for char in name)


def choose_highest_option(message: dict[str, Any]) -> list[int]:
    options = message.get("options") or []
    if not options:
        return []
    return list(max(options, key=lambda option: (sum(option), option.count(6) + option.count(7) + option.count(8))))


def run_player(player_name: str, version: str, strategy: Strategy) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    seeded = stable_seed(player_name, args.seed)
    if seeded is not None:
        random.seed(seeded)

    print(f"({player_name}) ready", file=sys.stderr)
    for line in sys.stdin:
        message = json.loads(line)
        message_type = message.get("type")
        if message_type == "hello":
            response = {"type": "hello", "player_name": player_name, "version": version}
        elif message_type == "choose_pair":
            response = strategy(message) or {"type": "choose_pair", "sums": choose_highest_option(message)}
        elif message_type == "decide_continue":
            response = strategy(message) or {"type": "decide_continue", "action": "roll"}
        elif message_type == "turn_start":
            print(f"({player_name}) turn start", file=sys.stderr)
            response = None
        elif message_type == "move":
            print(f"({player_name}) move sums={message.get('sums')} pawns={message.get('pawns')}", file=sys.stderr)
            response = None
        elif message_type == "turn_end":
            print(f"({player_name}) turn end claimed={message.get('claimed')}", file=sys.stderr)
            response = None
        elif message_type == "burst":
            print(f"({player_name}) burst dice={message.get('dice')}", file=sys.stderr)
            response = None
        elif message_type == "final":
            print(f"({player_name}) final winner={message.get('winner_name')}", file=sys.stderr)
            response = None
        elif message_type == "bye":
            print(f"({player_name}) bye", file=sys.stderr)
            response = {"type": "bye", "player_name": player_name}
        else:
            response = {"type": "error", "error": f"unknown message type: {message_type}"}

        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
        if message_type == "bye":
            break
    return 0
