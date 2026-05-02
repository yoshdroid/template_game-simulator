from __future__ import annotations

from cant_stop.simulator import (
    BoardState,
    advance_column,
    commit_pawns,
    dice_pair_options,
    legal_pair_options,
    run_game,
)


class FakePlayer:
    def __init__(self, name):
        self.name = name
        self.requests = []
        self.notifications = []

    def request(self, message):
        self.requests.append(message)
        if message["type"] == "hello":
            return {"type": "hello", "player_name": self.name}
        if message["type"] == "choose_pair":
            return {"type": "choose_pair", "sums": message["options"][0]}
        if message["type"] == "decide_continue":
            return {"type": "decide_continue", "action": "stop"}
        if message["type"] == "bye":
            return {"type": "bye"}
        raise AssertionError(message)

    def notify(self, message):
        self.notifications.append(message)


def test_dice_pair_options_deduplicates_pair_sums():
    assert dice_pair_options((1, 2, 3, 4)) == ((3, 7), (4, 6), (5, 5))


def test_legal_pair_options_respects_three_pawn_limit():
    board = BoardState()
    pawns = {2: 1, 3: 1, 4: 1}

    assert legal_pair_options(board, 0, pawns, (5, 5, 6, 6)) == ()
    assert legal_pair_options(board, 0, pawns, (1, 1, 1, 2)) == ((2, 3),)


def test_commit_pawns_claims_column_and_removes_other_progress():
    board = BoardState()
    board.progress[1][2] = 2
    pawns = {2: 3}

    claimed = commit_pawns(board, 0, pawns)

    assert claimed == (2,)
    assert board.claimed_by[2] == 0
    assert board.scores[0] == 1
    assert 2 not in board.progress[1]
    assert pawns == {}


def test_advance_column_starts_from_player_progress():
    board = BoardState()
    board.progress[0][7] = 4
    pawns = {}

    assert advance_column(board, 0, pawns, 7) is True
    assert pawns[7] == 5


def test_run_game_with_step_records_turns_and_final_board():
    players = tuple(FakePlayer(f"p{index}") for index in range(4))

    result = run_game(players, seed=1, step=4)

    assert len(result.turns) == 4
    assert result.completed is False
    assert result.final_board["scores"] == [0, 0, 0, 0]
    assert all(player.requests[0]["type"] == "hello" for player in players)
