from __future__ import annotations

from cant_stop import protocol
from cant_stop.players import rule_of_28


def base_board(progress=None, scores=None, claimed_by=None):
    return {
        "columns": {str(column): height for column, height in rule_of_28.COLUMN_HEIGHTS.items()},
        "progress": progress or [{}, {}, {}, {}],
        "claimed_by": claimed_by or {},
        "scores": scores or [0, 0, 0, 0],
    }


def test_rule_of_28_scores_mark_and_advance_values_from_current_turn():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 2, "7": 1, "10": 1},
        "board": base_board(),
    }

    assert rule_of_28.column_turn_score(message, 2, 2) == 18
    assert rule_of_28.column_turn_score(message, 7, 1) == 2
    assert rule_of_28.column_turn_score(message, 10, 1) == 8
    assert rule_of_28.turn_score(message) == 28


def test_rule_of_28_applies_three_column_parity_and_range_modifiers():
    odd_message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"3": 1, "5": 1, "7": 1},
        "board": base_board(),
    }
    even_message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 1, "4": 1, "6": 1},
        "board": base_board(),
    }

    assert rule_of_28.turn_score(odd_message) == 24
    assert rule_of_28.turn_score(even_message) == 26


def test_rule_of_28_does_not_stop_before_three_markers_are_placed():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 3, "12": 3},
        "board": base_board(),
    }

    assert rule_of_28.turn_score(message) >= 28
    assert rule_of_28.roll_probability(message) == 1.0


def test_rule_of_28_stops_at_28_after_three_markers():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 2, "7": 1, "10": 1},
        "board": base_board(),
    }

    assert rule_of_28.roll_probability(message) == 0.0


def test_rule_of_28_choose_pair_maximizes_rule_score():
    message = {
        "type": protocol.CHOOSE_PAIR,
        "player_index": 0,
        "options": [[6, 7], [2, 10]],
        "pawns": {"7": 1},
        "board": base_board(),
    }

    assert rule_of_28.choose_pair(message) == [2, 10]


def test_rule_of_28_choose_column_maximizes_rule_score():
    message = {
        "type": protocol.CHOOSE_COLUMN,
        "player_index": 0,
        "columns": [6, 12],
        "pawns": {"4": 1, "9": 1},
        "board": base_board(),
    }

    assert rule_of_28.choose_column(message) == 12
