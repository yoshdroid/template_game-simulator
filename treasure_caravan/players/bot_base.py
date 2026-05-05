from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

try:
    from treasure_caravan import protocol
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import protocol


Strategy = Callable[[dict[str, Any]], dict[str, Any] | None]


def stable_seed(name: str, seed: int | None) -> int | None:
    if seed is None:
        return None
    return seed + sum(ord(char) for char in name)


def choose_random_action(message: dict[str, Any]) -> dict[str, Any]:
    legal_actions = message.get("legal_actions") or []
    if not legal_actions:
        return {"action": "rest"}
    return dict(random.choice(legal_actions))


def route_info(message: dict[str, Any], route: str) -> dict[str, Any]:
    return dict(message.get("state", {}).get("routes", {}).get(route, {}))


def player_state(message: dict[str, Any]) -> dict[str, Any]:
    state = message.get("state", {})
    index = int(message.get("player_index", state.get("current_player", 0)))
    players = state.get("players", [])
    return dict(players[index]) if index < len(players) else {}


def estimated_danger(message: dict[str, Any], action: dict[str, Any]) -> int:
    player = player_state(message)
    action_name = action.get("action")
    if action_name not in {"advance", "dig"}:
        return 0
    route = str(player.get("route"))
    depth = int(player.get("depth", 0))
    heat = int(player.get("heat", 0))
    cargo = int(player.get("cargo", 0))
    if action_name == "advance":
        depth += 1
        heat += 1
    elif action_name == "dig":
        treasure = route_info(message, route).get("treasure", [])
        if 1 <= depth <= len(treasure):
            cargo += int(treasure[depth - 1])
        heat += 2
    risk = int(route_info(message, route).get("risk", 0))
    return risk + depth + heat + cargo // 5


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
        elif message_type == protocol.CHOOSE_ACTION:
            action = strategy(message) or choose_random_action(message)
            response = protocol.make_choose_action_response(action)
        elif message_type == protocol.TURN_START:
            print(f"({player_name}) turn start", file=sys.stderr)
            response = None
        elif message_type == protocol.ACTION_RESULT:
            print(f"({player_name}) action={message.get('action')} bust={message.get('bust', False)}", file=sys.stderr)
            response = None
        elif message_type == protocol.BUST:
            print(f"({player_name}) bust lost={message.get('lost_cargo', 0)}", file=sys.stderr)
            response = None
        elif message_type == protocol.RETURN:
            print(f"({player_name}) returned banked+={message.get('banked_delta', 0)}", file=sys.stderr)
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
