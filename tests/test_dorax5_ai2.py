from __future__ import annotations

from cant_stop import protocol
from cant_stop.players import dorax5_AI2


def test_dorax5_ai2_prioritizes_edges_then_center_lanes():
    assert dorax5_AI2.choose_pair({"type": protocol.CHOOSE_PAIR, "options": [[6, 7], [2, 5], [4, 9]]}) == [2, 5]
    assert dorax5_AI2.choose_column({"type": protocol.CHOOSE_COLUMN, "columns": [5, 8, 12]}) == 12


def test_dorax5_ai2_stops_when_pawn_reaches_configured_steps_from_player_progress():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 1,
        "pawns": {"5": 6},
        "board": {
            "scores": [0, 0, 0, 0],
            "columns": {"5": 9},
            "progress": [{}, {"5": 3}, {}, {}],
        },
    }

    assert dorax5_AI2.advanced_steps(message, 5, 6) == 3
    assert dorax5_AI2.reached_stop_steps(message) is True
    assert dorax5_AI2.roll_probability(message) == 0.0


def test_dorax5_ai2_late_game_ignores_non_summit_stop_steps():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 1},
        "board": {
            "scores": [2, 0, 0, 0],
            "columns": {"2": 3},
            "progress": [{}, {}, {}, {}],
        },
    }

    assert dorax5_AI2.is_late_game(message) is True
    assert dorax5_AI2.reached_stop_steps(message) is True
    assert dorax5_AI2.roll_probability(message) == 0.80


def test_dorax5_ai2_late_game_still_stops_at_summit():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 3},
        "board": {
            "scores": [2, 0, 0, 0],
            "columns": {"2": 3},
            "progress": [{}, {}, {}, {}],
        },
    }

    assert dorax5_AI2.has_summit_pawn(message) is True
    assert dorax5_AI2.roll_probability(message) == 0.0
