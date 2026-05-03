from __future__ import annotations

from cant_stop import protocol
from cant_stop.players import brain


def test_brain_prioritizes_second_from_top_patterns():
    message = {
        "type": protocol.CHOOSE_PAIR,
        "player_index": 0,
        "options": [[6, 8], [4, 9], [3, 10]],
        "pawns": {},
        "board": {
            "columns": {"3": 5, "4": 7, "6": 11, "8": 11, "9": 9, "10": 7},
            "progress": [{"6": 10, "8": 10, "4": 6}, {}, {}, {}],
            "claimed_by": {},
            "scores": [0, 0, 0, 0],
        },
    }

    assert brain.choose_pair(message) == [6, 8]


def test_brain_avoids_new_pawns_unless_no_existing_pawn_option():
    message = {
        "type": protocol.CHOOSE_PAIR,
        "player_index": 0,
        "options": [[4, 9], [6, 7]],
        "pawns": {"4": 2, "9": 1},
        "board": {
            "columns": {"4": 7, "6": 11, "7": 13, "9": 9},
            "progress": [{}, {}, {}, {}],
            "claimed_by": {},
            "scores": [0, 0, 0, 0],
        },
    }

    assert brain.choose_pair(message) == [4, 9]


def test_brain_new_pawn_priority_checks_other_players():
    message = {
        "type": protocol.CHOOSE_COLUMN,
        "player_index": 0,
        "columns": [6, 12],
        "pawns": {"4": 1, "9": 1},
        "board": {
            "columns": {"6": 11, "12": 3},
            "progress": [{}, {"6": 4}, {}, {}],
            "claimed_by": {},
            "scores": [0, 0, 0, 0],
        },
    }

    assert brain.choose_column(message) == 12


def test_brain_never_stops_before_three_pawns_even_at_summit():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 3, "7": 4},
        "board": {
            "columns": {"2": 3, "7": 13},
            "progress": [{}, {}, {}, {}],
            "claimed_by": {},
            "scores": [0, 0, 0, 0],
        },
    }

    assert brain.has_summit_pawn(message) is True
    assert brain.roll_probability(message, roll_count=10) == 1.0


def test_brain_stops_with_three_pawns_and_a_summit_pawn():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 3, "6": 3, "7": 4},
        "board": {
            "columns": {"2": 3, "6": 11, "7": 13},
            "progress": [{}, {}, {}, {}],
            "claimed_by": {},
            "scores": [0, 0, 0, 0],
        },
    }

    assert brain.roll_probability(message) == 0.0


def test_brain_roll_probability_tables_and_roll_penalty():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"6": 2, "7": 3, "4": 1},
        "board": {
            "columns": {"4": 7, "6": 11, "7": 13},
            "progress": [{}, {}, {}, {}],
            "claimed_by": {},
            "scores": [1, 1, 1, 1],
        },
    }

    assert brain.roll_probability(message) == 1.0
    assert brain.roll_probability(message, roll_count=2) == 0.90


def test_brain_roll_count_resets_on_turn_end_and_burst():
    player = brain.BrainPlayer()
    player.roll_count = 3

    player.reset_turn()
    assert player.roll_count == 0
