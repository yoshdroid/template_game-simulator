from __future__ import annotations

import pytest

from cant_stop import protocol


def test_parse_choose_pair_response_accepts_legal_pair():
    message = protocol.make_choose_pair_response([9, 5])

    assert protocol.parse_choose_pair_response(message, ((5, 9), (6, 8))) == (5, 9)


def test_parse_choose_pair_response_rejects_missing_sums():
    with pytest.raises(ValueError):
        protocol.parse_choose_pair_response({"type": protocol.CHOOSE_PAIR}, ((5, 9),))


def test_parse_choose_column_response_accepts_option():
    message = protocol.make_choose_column_response(9)

    assert protocol.parse_choose_column_response(message, (5, 9)) == 9


def test_parse_choose_column_response_rejects_illegal_option():
    with pytest.raises(ValueError):
        protocol.parse_choose_column_response(protocol.make_choose_column_response(7), (5, 9))


def test_parse_decide_continue_response_rejects_unknown_action():
    with pytest.raises(ValueError):
        protocol.parse_decide_continue_response({"type": protocol.DECIDE_CONTINUE, "action": "maybe"})
