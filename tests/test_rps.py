from __future__ import annotations

import pytest

from template.simulator.rps import judge, run_match


class FakePlayer:
    def __init__(self, name, hands):
        self.name = name
        self.hands = list(hands)
        self.requests = []
        self.notifications = []

    def request(self, message):
        self.requests.append(message)
        if message["type"] == "hello":
            return {"type": "hello", "player_name": self.name}
        if message["type"] == "choice":
            return {"type": "choice", "hand": self.hands.pop(0)}
        if message["type"] == "bye":
            return {"type": "bye"}
        raise AssertionError(message)

    def notify(self, message):
        self.notifications.append(message)


@pytest.mark.parametrize(
    ("p1_hand", "p2_hand", "expected"),
    [
        ("rock", "scissors", ("win", "lose")),
        ("scissors", "paper", ("win", "lose")),
        ("paper", "rock", ("win", "lose")),
        ("rock", "rock", ("draw", "draw")),
        ("bad", "rock", ("lose", "win")),
    ],
)
def test_judge(p1_hand, p2_hand, expected):
    assert judge(p1_hand, p2_hand) == expected


def test_run_match_until_target_wins():
    p1 = FakePlayer("p1", ["rock", "paper"])
    p2 = FakePlayer("p2", ["scissors", "rock"])

    result = run_match(p1, p2, target_wins=2)

    assert result.completed is True
    assert result.winner_name == "p1"
    assert result.p1_result.wins == 2
    assert result.p2_result.wins == 0
    assert len(result.rounds) == 2
    assert p1.notifications[-1]["type"] == "final"
    assert p1.notifications[-1]["result"] == "win"


def test_run_match_step_stops_early_and_uses_current_leader():
    p1 = FakePlayer("p1", ["rock"])
    p2 = FakePlayer("p2", ["scissors"])

    result = run_match(p1, p2, target_wins=2, step=1)

    assert result.completed is False
    assert result.winner_name == "p1"
    assert result.p1_result.wins == 1
    assert result.p2_result.wins == 0


def test_run_match_rejects_invalid_target():
    with pytest.raises(ValueError):
        run_match(FakePlayer("p1", []), FakePlayer("p2", []), target_wins=0)
