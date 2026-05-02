from __future__ import annotations

from pathlib import Path

import pytest

from template.master import update_player_header
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


def test_template_update_player_header_sets_first_game_date_only_when_empty():
    player = Path("tests/_tmp_template_player_header.py")
    try:
        player.write_text(
            "\n".join(
                [
                    'PLAYER_NAME = "sample"',
                    'FIRST_GAME_DATE = ""',
                    'LAST_GAME_DATE = ""',
                    "PLAY_TIMES = 0",
                    "WIN = 0",
                    "POINT = 0",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        update_player_header(player, "2026/05/03 01:23", "win", 2)
        update_player_header(player, "2026/05/04 02:34", "lose", 1)
        text = player.read_text(encoding="utf-8")

        assert "FIRST_GAME_DATE = '2026/05/03 01:23'" in text
        assert "LAST_GAME_DATE = '2026/05/04 02:34'" in text
        assert "PLAY_TIMES = 2" in text
        assert "WIN = 1" in text
        assert "POINT = 3" in text
    finally:
        player.unlink(missing_ok=True)
