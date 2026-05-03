from __future__ import annotations

from cant_stop import protocol
from cant_stop.players import codex


def base_board(progress=None, scores=None, claimed_by=None):
    return {
        "columns": {str(column): height for column, height in codex.COLUMN_HEIGHTS.items()},
        "progress": progress or [{}, {}, {}, {}],
        "claimed_by": claimed_by or {},
        "scores": scores or [0, 0, 0, 0],
    }


def test_codex_stops_when_any_pawn_reaches_summit():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 3, "7": 4, "8": 2},
        "board": base_board(),
    }

    assert codex.has_summit_pawn(message) is True
    assert codex.roll_probability(message) == 0.0


def test_codex_continues_when_three_pawns_are_still_low_risk():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"6": 4, "7": 5, "8": 4},
        "board": base_board(),
    }

    assert codex.bust_probability(message) < 0.20
    assert codex.roll_probability(message) > 0.80


def test_codex_stops_when_bust_risk_is_high_and_bank_value_exists():
    message = {
        "type": protocol.DECIDE_CONTINUE,
        "player_index": 0,
        "pawns": {"2": 2, "3": 4, "12": 2},
        "board": base_board(),
    }

    assert codex.bust_probability(message) > 0.35
    assert codex.roll_probability(message) == 0.0


def test_codex_pair_choice_prefers_near_claim_progress_over_plain_center():
    message = {
        "type": protocol.CHOOSE_PAIR,
        "player_index": 0,
        "options": [[6, 7], [2, 12]],
        "pawns": {},
        "board": base_board(progress=[{"2": 2, "12": 2}, {}, {}, {}]),
    }

    assert codex.choose_pair(message) == [2, 12]


def test_codex_column_choice_uses_state_value():
    message = {
        "type": protocol.CHOOSE_COLUMN,
        "player_index": 0,
        "columns": [6, 12],
        "pawns": {"4": 1, "9": 1},
        "board": base_board(progress=[{"12": 2}, {}, {}, {}]),
    }

    assert codex.choose_column(message) == 12
