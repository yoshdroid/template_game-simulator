from __future__ import annotations

from typing import Any


HELLO = "hello"
CHOOSE_ACTION = "choose_action"
TURN_START = "turn_start"
ACTION_RESULT = "action_result"
BUST = "bust"
RETURN = "return"
FINAL = "final"
BYE = "bye"
ERROR = "error"


def message_type(message: dict[str, Any]) -> str:
    return str(message.get("type", ""))


def require_type(message: dict[str, Any], expected: str) -> None:
    actual = message_type(message)
    if actual != expected:
        raise ValueError(f"expected message type {expected!r}, got {actual!r}")


def require_keys(message: dict[str, Any], *keys: str) -> None:
    missing = [key for key in keys if key not in message]
    if missing:
        raise ValueError(f"missing message keys: {', '.join(missing)}")


def make_hello_request(player_index: int, color: str) -> dict[str, Any]:
    return {"type": HELLO, "player_index": player_index, "color": color}


def make_hello_response(player_name: str, version: str) -> dict[str, Any]:
    return {"type": HELLO, "player_name": player_name, "version": version}


def make_choose_action_request(
    player_index: int,
    state: dict[str, Any],
    legal_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "type": CHOOSE_ACTION,
        "player_index": player_index,
        "state": state,
        "legal_actions": legal_actions,
    }


def make_choose_action_response(action: dict[str, Any]) -> dict[str, Any]:
    return {"type": CHOOSE_ACTION, "action": action}


def parse_choose_action_response(
    message: dict[str, Any],
    legal_actions: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    require_type(message, CHOOSE_ACTION)
    require_keys(message, "action")
    action = message["action"]
    if not isinstance(action, dict):
        raise ValueError("action must be an object")
    if action not in legal_actions:
        raise ValueError(f"illegal action: {action}")
    return dict(action)


def make_bye_request() -> dict[str, Any]:
    return {"type": BYE}


def make_bye_response(player_name: str) -> dict[str, Any]:
    return {"type": BYE, "player_name": player_name}


def make_error_response(error: str) -> dict[str, Any]:
    return {"type": ERROR, "error": error}
