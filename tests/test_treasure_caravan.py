from __future__ import annotations

from random import Random

from treasure_caravan import protocol
from treasure_caravan.simulator import PlayerState, apply_action, legal_actions, run_game


class FakeRng:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, start: int, end: int) -> int:
        return self.value


class ScriptedPort:
    def __init__(self, name: str) -> None:
        self.name = name
        self.notifications = []

    def request(self, message):
        if protocol.message_type(message) == protocol.HELLO:
            return protocol.make_hello_response(self.name, "test")
        if protocol.message_type(message) == protocol.CHOOSE_ACTION:
            legal_actions = message["legal_actions"]
            return protocol.make_choose_action_response(legal_actions[0])
        if protocol.message_type(message) == protocol.BYE:
            return protocol.make_bye_response(self.name)
        raise AssertionError(f"unexpected request: {message}")

    def notify(self, message):
        self.notifications.append(message)


def test_legal_actions_at_base_are_depart_routes():
    players = [PlayerState() for _ in range(4)]

    assert legal_actions(players, 0) == (
        {"action": "depart", "route": "oasis"},
        {"action": "depart", "route": "ruins"},
        {"action": "depart", "route": "mirage"},
    )


def test_depart_dig_return_banks_cargo():
    players = [PlayerState() for _ in range(4)]

    apply_action(players, 0, {"action": "depart", "route": "ruins"}, Random(0))
    dig_event = apply_action(players, 0, {"action": "dig"}, FakeRng(20))
    return_event = apply_action(players, 0, {"action": "return"}, Random(0))

    assert dig_event["cargo_delta"] == 2
    assert players[0].banked == 2
    assert players[0].location == "base"
    assert return_event["banked_delta"] == 2


def test_danger_bust_loses_cargo_and_resets_expedition():
    players = [PlayerState() for _ in range(4)]
    apply_action(players, 0, {"action": "depart", "route": "mirage"}, Random(0))

    event = apply_action(players, 0, {"action": "dig"}, FakeRng(1))

    assert event["bust"] is True
    assert event["lost_cargo"] == 3
    assert players[0].cargo == 0
    assert players[0].location == "base"
    assert players[0].busts == 1


def test_protocol_rejects_illegal_action():
    legal = ({"action": "return"}, {"action": "rest"})
    message = protocol.make_choose_action_response({"action": "dig"})

    try:
        protocol.parse_choose_action_response(message, legal)
    except ValueError as exc:
        assert "illegal action" in str(exc)
    else:
        raise AssertionError("illegal action was accepted")


def test_run_game_reaches_max_actions():
    ports = tuple(ScriptedPort(f"P{index}") for index in range(4))

    result = run_game(ports, seed=0, max_actions=8)

    assert len(result.actions) == 8
    assert result.final_state["action_count"] == 8
    assert result.players == ("P0", "P1", "P2", "P3")
