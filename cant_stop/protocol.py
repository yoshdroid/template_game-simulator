from __future__ import annotations

from typing import Any


HELLO = "hello"
CHOOSE_PAIR = "choose_pair"
CHOOSE_COLUMN = "choose_column"
DECIDE_CONTINUE = "decide_continue"
TURN_START = "turn_start"
MOVE = "move"
TURN_END = "turn_end"
BURST = "burst"
FINAL = "final"
BYE = "bye"
ERROR = "error"

STOP = "stop"
ROLL = "roll"


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


def int_tuple(value: Any, *, length: int | None = None, name: str = "value") -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list or tuple")
    try:
        result = tuple(int(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain integers") from exc
    if length is not None and len(result) != length:
        raise ValueError(f"{name} must contain {length} integers")
    return result


def make_hello_request(player_index: int, color: str) -> dict[str, Any]:
    return {"type": HELLO, "player_index": player_index, "color": color}


def make_hello_response(player_name: str, version: str) -> dict[str, Any]:
    return {"type": HELLO, "player_name": player_name, "version": version}


def make_choose_pair_request(
    dice: list[int],
    options: list[list[int]],
    pawns: dict[int, int],
    board: dict[str, Any],
) -> dict[str, Any]:
    return {"type": CHOOSE_PAIR, "dice": dice, "options": options, "pawns": pawns, "board": board}


def make_choose_pair_response(sums: list[int] | tuple[int, int]) -> dict[str, Any]:
    return {"type": CHOOSE_PAIR, "sums": list(sums)}


def parse_choose_pair_response(message: dict[str, Any], legal_options: tuple[tuple[int, int], ...]) -> tuple[int, int]:
    require_type(message, CHOOSE_PAIR)
    require_keys(message, "sums")
    choice = tuple(sorted(int_tuple(message["sums"], length=2, name="sums")))
    if choice not in legal_options:
        raise ValueError(f"illegal choose_pair sums: {choice}")
    return choice


def make_choose_column_request(
    dice: list[int],
    sums: list[int],
    columns: list[int],
    pawns: dict[int, int],
    board: dict[str, Any],
) -> dict[str, Any]:
    return {"type": CHOOSE_COLUMN, "dice": dice, "sums": sums, "columns": columns, "pawns": pawns, "board": board}


def make_choose_column_response(column: int) -> dict[str, Any]:
    return {"type": CHOOSE_COLUMN, "column": int(column)}


def parse_choose_column_response(message: dict[str, Any], options: tuple[int, ...]) -> int:
    require_type(message, CHOOSE_COLUMN)
    require_keys(message, "column")
    try:
        column = int(message["column"])
    except (TypeError, ValueError) as exc:
        raise ValueError("column must be an integer") from exc
    if column not in options:
        raise ValueError(f"illegal choose_column column: {column}")
    return column


def make_decide_continue_request(
    pawns: dict[int, int],
    board: dict[str, Any],
    player_index: int | None = None,
) -> dict[str, Any]:
    message = {"type": DECIDE_CONTINUE, "pawns": pawns, "board": board}
    if player_index is not None:
        message["player_index"] = player_index
    return message


def make_decide_continue_response(action: str) -> dict[str, Any]:
    if action not in {STOP, ROLL}:
        raise ValueError(f"unknown continue action: {action}")
    return {"type": DECIDE_CONTINUE, "action": action}


def parse_decide_continue_response(message: dict[str, Any]) -> str:
    require_type(message, DECIDE_CONTINUE)
    require_keys(message, "action")
    action = str(message["action"]).lower()
    if action not in {STOP, ROLL}:
        raise ValueError(f"unknown continue action: {action}")
    return action


def make_bye_request() -> dict[str, Any]:
    return {"type": BYE}


def make_bye_response(player_name: str) -> dict[str, Any]:
    return {"type": BYE, "player_name": player_name}


def make_error_response(error: str) -> dict[str, Any]:
    return {"type": ERROR, "error": error}
