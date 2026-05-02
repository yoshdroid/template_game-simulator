from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

try:
    from cant_stop import protocol
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import protocol


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


def choose_random_column(message: dict[str, Any]) -> int:
    columns = message.get("columns") or []
    return int(random.choice(columns)) if columns else 7


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
        message_type = protocol.message_type(message)
        if message_type == protocol.HELLO:
            response = protocol.make_hello_response(player_name, version)
        elif message_type == protocol.CHOOSE_PAIR:
            response = strategy(message) or protocol.make_choose_pair_response(choose_highest_option(message))
        elif message_type == protocol.CHOOSE_COLUMN:
            response = strategy(message) or protocol.make_choose_column_response(choose_random_column(message))
        elif message_type == protocol.DECIDE_CONTINUE:
            response = strategy(message) or protocol.make_decide_continue_response(protocol.ROLL)
        elif message_type == protocol.TURN_START:
            print(f"({player_name}) turn start", file=sys.stderr)
            response = None
        elif message_type == protocol.MOVE:
            print(f"({player_name}) move sums={message.get('sums')} pawns={message.get('pawns')}", file=sys.stderr)
            response = None
        elif message_type == protocol.TURN_END:
            print(f"({player_name}) turn end claimed={message.get('claimed')}", file=sys.stderr)
            response = None
        elif message_type == protocol.BURST:
            print(f"({player_name}) burst dice={message.get('dice')}", file=sys.stderr)
            response = None
        elif message_type == protocol.FINAL:
            print(f"({player_name}) final winner={message.get('winner_name')}", file=sys.stderr)
            response = None
        elif message_type == protocol.BYE:
            print(f"({player_name}) bye", file=sys.stderr)
            response = protocol.make_bye_response(player_name)
        else:
            response = protocol.make_error_response(f"unknown message type: {message_type}")

        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
        if message_type == protocol.BYE:
            break
    return 0
