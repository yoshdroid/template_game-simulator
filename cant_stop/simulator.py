from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from collections.abc import Callable
from time import sleep
from typing import Any, Protocol


COLUMNS = tuple(range(2, 13))
COLUMN_HEIGHTS = {
    2: 3,
    3: 5,
    4: 7,
    5: 9,
    6: 11,
    7: 13,
    8: 11,
    9: 9,
    10: 7,
    11: 5,
    12: 3,
}
PAIR_INDEXES = (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2)))
PLAYER_COLORS = ("red", "green", "blue", "yellow")


class PlayerPort(Protocol):
    name: str

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        ...

    def notify(self, message: dict[str, Any]) -> None:
        ...


@dataclass(frozen=True)
class PlayerResult:
    final_result: str
    claimed_columns: tuple[int, ...]
    points: int


@dataclass(frozen=True)
class TurnRecord:
    player_index: int
    player_name: str
    dice: tuple[int, int, int, int]
    chosen_sums: tuple[int, int] | None
    action: str
    pawns: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class GameResult:
    players: tuple[str, ...]
    results: tuple[PlayerResult, ...]
    winner_index: int | None
    turns: tuple[TurnRecord, ...]
    events: tuple[dict[str, Any], ...]
    final_board: dict[str, Any]
    completed: bool

    @property
    def winner_name(self) -> str | None:
        if self.winner_index is None:
            return None
        return self.players[self.winner_index]


@dataclass
class BoardState:
    progress: list[dict[int, int]] = field(default_factory=lambda: [dict() for _ in range(4)])
    claimed_by: dict[int, int] = field(default_factory=dict)
    scores: list[int] = field(default_factory=lambda: [0, 0, 0, 0])

    def player_position(self, player_index: int, column: int) -> int:
        return self.progress[player_index].get(column, 0)

    def is_claimed(self, column: int) -> bool:
        return column in self.claimed_by

    def claim_column(self, player_index: int, column: int) -> None:
        if column in self.claimed_by:
            return
        self.claimed_by[column] = player_index
        self.scores[player_index] += 1
        for progress in self.progress:
            progress.pop(column, None)


def dice_pair_options(dice: tuple[int, int, int, int]) -> tuple[tuple[int, int], ...]:
    options = []
    for first_pair, second_pair in PAIR_INDEXES:
        first_sum = dice[first_pair[0]] + dice[first_pair[1]]
        second_sum = dice[second_pair[0]] + dice[second_pair[1]]
        option = tuple(sorted((first_sum, second_sum)))
        if option not in options:
            options.append(option)
    return tuple(options)


def can_advance_column(board: BoardState, player_index: int, pawns: dict[int, int], column: int) -> bool:
    if column not in COLUMN_HEIGHTS or board.is_claimed(column):
        return False
    if column in pawns:
        return pawns[column] < COLUMN_HEIGHTS[column]
    if len(pawns) >= 3:
        return False
    start = board.player_position(player_index, column) + 1
    return start <= COLUMN_HEIGHTS[column]


def advance_column(board: BoardState, player_index: int, pawns: dict[int, int], column: int) -> bool:
    if not can_advance_column(board, player_index, pawns, column):
        return False
    if column in pawns:
        pawns[column] += 1
    else:
        pawns[column] = board.player_position(player_index, column) + 1
    return True


def legal_pair_options(
    board: BoardState,
    player_index: int,
    pawns: dict[int, int],
    dice: tuple[int, int, int, int],
) -> tuple[tuple[int, int], ...]:
    legal = []
    for option in dice_pair_options(dice):
        simulated = dict(pawns)
        moved = False
        for column in option:
            moved = advance_column(board, player_index, simulated, column) or moved
        if moved:
            legal.append(option)
    return tuple(legal)


def apply_pair_option(
    board: BoardState,
    player_index: int,
    pawns: dict[int, int],
    chosen_sums: tuple[int, int],
) -> tuple[int, ...]:
    advanced = []
    for column in chosen_sums:
        if advance_column(board, player_index, pawns, column):
            advanced.append(column)
    return tuple(advanced)


def commit_pawns(board: BoardState, player_index: int, pawns: dict[int, int]) -> tuple[int, ...]:
    claimed = []
    for column, position in sorted(pawns.items()):
        if board.is_claimed(column):
            continue
        board.progress[player_index][column] = max(board.player_position(player_index, column), position)
        if board.progress[player_index][column] >= COLUMN_HEIGHTS[column]:
            board.claim_column(player_index, column)
            claimed.append(column)
    pawns.clear()
    return tuple(claimed)


def public_board_state(board: BoardState, pawns: dict[int, int] | None = None) -> dict[str, Any]:
    return {
        "columns": COLUMN_HEIGHTS,
        "progress": [{str(column): pos for column, pos in player.items()} for player in board.progress],
        "claimed_by": {str(column): player for column, player in board.claimed_by.items()},
        "scores": list(board.scores),
        "pawns": {str(column): pos for column, pos in (pawns or {}).items()},
    }


def _parse_choice(response: dict[str, Any], legal_options: tuple[tuple[int, int], ...]) -> tuple[int, int]:
    raw = response.get("sums", response.get("choice"))
    if isinstance(raw, str):
        parts = raw.replace(",", " ").split()
        raw = [int(part) for part in parts]
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        choice = tuple(sorted((int(raw[0]), int(raw[1]))))
        if choice in legal_options:
            return choice
    return legal_options[0]


def _parse_stop(response: dict[str, Any]) -> bool:
    action = str(response.get("action", response.get("choice", "roll"))).lower()
    return action in {"stop", "end", "bank"}


def run_game(
    players: tuple[PlayerPort, PlayerPort, PlayerPort, PlayerPort],
    *,
    seed: int | None = None,
    step: int | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    burst_pause_seconds: float = 0.0,
) -> GameResult:
    rng = Random(seed)
    board = BoardState()
    turns: list[TurnRecord] = []
    events: list[dict[str, Any]] = []

    def emit(event: dict[str, Any]) -> None:
        event = {"event_index": len(events), **event}
        events.append(event)
        if on_event is not None:
            on_event(event)

    for index, player in enumerate(players):
        player.request({"type": "hello", "player_index": index, "color": PLAYER_COLORS[index]})

    current_player = 0
    completed = False
    winner_index: int | None = None
    emit(
        {
            "type": "game_start",
            "players": [player.name for player in players],
            "colors": list(PLAYER_COLORS),
            "board": public_board_state(board),
        }
    )

    while not completed:
        if step is not None and len(turns) >= step:
            break

        player = players[current_player]
        pawns: dict[int, int] = {}
        player.notify({"type": "turn_start", "player_index": current_player, "board": public_board_state(board)})
        emit(
            {
                "type": "turn_start",
                "player_index": current_player,
                "player_name": player.name,
                "board": public_board_state(board),
            }
        )

        while True:
            if step is not None and len(turns) >= step:
                break

            dice = tuple(rng.randint(1, 6) for _ in range(4))
            legal_options = legal_pair_options(board, current_player, pawns, dice)
            emit(
                {
                    "type": "dice",
                    "player_index": current_player,
                    "player_name": player.name,
                    "dice": list(dice),
                    "options": [list(option) for option in legal_options],
                    "pawns": {str(column): pos for column, pos in pawns.items()},
                    "board": public_board_state(board, pawns),
                }
            )
            if not legal_options:
                player.notify({"type": "burst", "dice": list(dice), "pawns": pawns, "board": public_board_state(board, pawns)})
                emit(
                    {
                        "type": "burst",
                        "player_index": current_player,
                        "player_name": player.name,
                        "dice": list(dice),
                        "pawns": {str(column): pos for column, pos in pawns.items()},
                        "board": public_board_state(board, pawns),
                    }
                )
                if burst_pause_seconds > 0:
                    sleep(burst_pause_seconds)
                turns.append(
                    TurnRecord(
                        player_index=current_player,
                        player_name=player.name,
                        dice=dice,
                        chosen_sums=None,
                        action="burst",
                        pawns=dict(pawns),
                    )
                )
                pawns.clear()
                break

            response = player.request(
                {
                    "type": "choose_pair",
                    "dice": list(dice),
                    "options": [list(option) for option in legal_options],
                    "pawns": pawns,
                    "board": public_board_state(board, pawns),
                }
            )
            chosen_sums = _parse_choice(response, legal_options)
            apply_pair_option(board, current_player, pawns, chosen_sums)
            player.notify({"type": "move", "sums": list(chosen_sums), "pawns": pawns, "board": public_board_state(board, pawns)})
            emit(
                {
                    "type": "move",
                    "player_index": current_player,
                    "player_name": player.name,
                    "dice": list(dice),
                    "sums": list(chosen_sums),
                    "pawns": {str(column): pos for column, pos in pawns.items()},
                    "board": public_board_state(board, pawns),
                }
            )

            stop_response = player.request(
                {
                    "type": "decide_continue",
                    "pawns": pawns,
                    "board": public_board_state(board, pawns),
                }
            )
            if _parse_stop(stop_response):
                claimed = commit_pawns(board, current_player, pawns)
                player.notify({"type": "turn_end", "claimed": list(claimed), "board": public_board_state(board)})
                emit(
                    {
                        "type": "turn_end",
                        "player_index": current_player,
                        "player_name": player.name,
                        "action": "stop",
                        "claimed": list(claimed),
                        "board": public_board_state(board),
                    }
                )
                turns.append(
                    TurnRecord(
                        player_index=current_player,
                        player_name=player.name,
                        dice=dice,
                        chosen_sums=chosen_sums,
                        action="stop",
                        pawns={},
                    )
                )
                if board.scores[current_player] >= 3:
                    completed = True
                    winner_index = current_player
                break

            turns.append(
                TurnRecord(
                    player_index=current_player,
                    player_name=player.name,
                    dice=dice,
                    chosen_sums=chosen_sums,
                    action="roll",
                    pawns=dict(pawns),
                )
            )
            emit(
                {
                    "type": "continue",
                    "player_index": current_player,
                    "player_name": player.name,
                    "action": "roll",
                    "pawns": {str(column): pos for column, pos in pawns.items()},
                    "board": public_board_state(board, pawns),
                }
            )

        if step is not None and len(turns) >= step:
            break
        current_player = (current_player + 1) % len(players)

    results = tuple(
        PlayerResult(
            final_result="win" if index == winner_index else "lose",
            claimed_columns=tuple(sorted(column for column, owner in board.claimed_by.items() if owner == index)),
            points=board.scores[index],
        )
        for index in range(len(players))
    )
    final_message = {
        "type": "final",
        "winner_index": winner_index,
        "winner_name": players[winner_index].name if winner_index is not None else None,
        "board": public_board_state(board),
    }
    for player in players:
        player.notify(final_message)
    emit(
        {
            "type": "game_end",
            "winner_index": winner_index,
            "winner_name": players[winner_index].name if winner_index is not None else None,
            "completed": completed,
            "board": public_board_state(board),
        }
    )

    return GameResult(
        players=tuple(player.name for player in players),
        results=results,
        winner_index=winner_index,
        turns=tuple(turns),
        events=tuple(events),
        final_board=public_board_state(board),
        completed=completed,
    )
