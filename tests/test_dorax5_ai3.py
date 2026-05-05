from __future__ import annotations

from cant_stop import protocol
from cant_stop.players import dorax5_AI3


def base_board(columns=None):
    return {"columns": columns or {"2": 3, "6": 11, "7": 13, "8": 11, "12": 3}}


def message_with_pawns(pawns):
    return {"type": protocol.DECIDE_CONTINUE, "pawns": pawns, "board": base_board()}


def test_dorax5_ai3_header_values_are_requested_identity():
    assert dorax5_AI3.PLAYER_NAME == "ドレッドノート"
    assert dorax5_AI3.VERSION == "1.0"


def test_dorax5_ai3_uses_center_and_danger_probability_table():
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"6": 1, "7": 1, "8": 1})) == 0.95
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"6": 1, "7": 1, "5": 1})) == 0.80
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"6": 1, "7": 1, "2": 1})) == 0.70
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"6": 1, "5": 1, "9": 1})) == 0.70
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"6": 1, "2": 1, "5": 1})) == 0.50
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"6": 1, "2": 1, "12": 1})) == 0.35
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"4": 1, "5": 1, "9": 1})) == 0.60
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"4": 1, "2": 1, "9": 1})) == 0.50
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"4": 1, "2": 1, "12": 1})) == 0.30
    assert dorax5_AI3.base_roll_probability(message_with_pawns({"2": 1, "3": 1, "12": 1})) == 0.20


def test_dorax5_ai3_never_stops_before_three_pawns():
    message = message_with_pawns({"2": 3, "12": 3})

    assert dorax5_AI3.has_summit_pawn(message) is True
    assert dorax5_AI3.roll_probability(message, roll_count=10) == 1.0


def test_dorax5_ai3_stops_with_three_pawns_and_any_summit():
    message = message_with_pawns({"2": 3, "6": 1, "7": 1})

    assert dorax5_AI3.has_summit_pawn(message) is True
    assert dorax5_AI3.roll_probability(message) == 0.0


def test_dorax5_ai3_applies_repeated_roll_penalty():
    message = message_with_pawns({"6": 1, "7": 1, "8": 1})

    assert dorax5_AI3.roll_probability(message, roll_count=2) == 0.85


def test_dorax5_ai3_resets_roll_count_on_turn_boundaries():
    player = dorax5_AI3.DreadnoughtPlayer()
    player.roll_count = 4

    player.reset_turn()

    assert player.roll_count == 0
