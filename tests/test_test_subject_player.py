from __future__ import annotations

from cant_stop import protocol
from cant_stop.players import test_subject


def base_board(progress=None, scores=None, claimed_by=None):
    return {
        "columns": {str(column): height for column, height in test_subject.COLUMN_HEIGHTS.items()},
        "progress": progress or [{}, {}, {}, {}],
        "claimed_by": claimed_by or {},
        "scores": scores or [0, 0, 0, 0],
    }


def test_subject_header_values_are_requested_identity():
    assert test_subject.PLAYER_NAME == "実験体ｘ"
    assert test_subject.VERSION == "1.0"


def test_subject_prioritizes_brain_like_near_summit_choice():
    message = {
        "type": protocol.CHOOSE_PAIR,
        "player_index": 0,
        "options": [[6, 7], [2, 10]],
        "pawns": {},
        "board": base_board(progress=[{"6": 10, "7": 1, "2": 1, "10": 1}, {}, {}, {}]),
    }

    assert test_subject.choose_pair(message) == [6, 7]


def test_subject_uses_rule_of_28_to_stop_in_opening():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 2, "7": 1, "10": 1},
        "board": base_board(scores=[0, 0, 0, 0]),
    }

    assert test_subject.turn_score(message) == 28
    assert test_subject.roll_probability(message) == 0.0


def test_subject_late_game_keeps_dorax5_ai2_style_pressure():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 2, "7": 1, "10": 1},
        "board": base_board(scores=[2, 0, 0, 0]),
    }

    assert test_subject.turn_score(message) == 28
    assert test_subject.roll_probability(message) == 0.90


def test_subject_stops_when_a_pawn_reaches_summit():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 3, "7": 1, "10": 1},
        "board": base_board(scores=[2, 0, 0, 0]),
    }

    assert test_subject.has_summit_pawn(message) is True
    assert test_subject.roll_probability(message) == 0.0


def test_subject_roll_count_penalty_is_lighter_in_late_game():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"6": 2, "7": 3, "8": 2},
        "board": base_board(scores=[2, 0, 0, 0]),
    }

    assert test_subject.roll_probability(message, roll_count=2) == 0.94
