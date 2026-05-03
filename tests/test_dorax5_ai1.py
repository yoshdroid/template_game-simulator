from __future__ import annotations

from cant_stop import protocol
from cant_stop.players import dorax5_AI1


def test_dorax5_ai1_stops_when_any_pawn_reaches_summit():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "pawns": {"7": 13},
        "board": {"columns": {"7": 13}},
    }

    assert dorax5_AI1.has_summit_pawn(message) is True
    assert dorax5_AI1.roll_probability(message) == 0.0


def test_dorax5_ai1_reduces_roll_probability_near_top_and_adds_center_bonus():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "pawns": {"7": 8, "8": 8, "6": 6},
        "board": {"columns": {"7": 13, "8": 11}},
    }

    assert dorax5_AI1.has_top_danger_pawn(message) is True
    assert dorax5_AI1.roll_probability(message) == 0.93


def test_dorax5_ai1_prioritizes_center_lanes_then_edges():
    message = {"type": protocol.CHOOSE_PAIR, "options": [[4, 9], [6, 11], [2, 12]]}

    assert dorax5_AI1.choose_pair(message) == [6, 11]
    assert dorax5_AI1.choose_column({"type": protocol.CHOOSE_COLUMN, "columns": [2, 5, 12]}) == 12
