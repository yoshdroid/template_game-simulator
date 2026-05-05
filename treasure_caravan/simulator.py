from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from random import Random
from typing import Any, Protocol

try:
    from . import protocol
except ImportError:
    import protocol


PLAYER_COLORS = ("red", "green", "blue", "yellow")
TARGET_BANKED = 40
DEFAULT_MAX_ACTIONS = 200
ROUTES: dict[str, dict[str, Any]] = {
    "oasis": {"name": "Oasis Road", "length": 5, "risk": 0, "treasure": [1, 2, 2, 3, 4]},
    "ruins": {"name": "Ruins Trail", "length": 6, "risk": 1, "treasure": [2, 3, 4, 5, 6, 8]},
    "mirage": {"name": "Mirage Dunes", "length": 7, "risk": 2, "treasure": [3, 4, 6, 8, 10, 12, 15]},
}


class PlayerPort(Protocol):
    name: str

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        ...

    def notify(self, message: dict[str, Any]) -> None:
        ...


@dataclass
class PlayerState:
    location: str = "base"
    route: str | None = None
    depth: int = 0
    cargo: int = 0
    banked: int = 0
    heat: int = 0
    dug_sites: list[str] = field(default_factory=list)
    busts: int = 0

    def reset_expedition(self) -> None:
        self.location = "base"
        self.route = None
        self.depth = 0
        self.cargo = 0
        self.heat = 0
        self.dug_sites.clear()

    def public_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "route": self.route,
            "depth": self.depth,
            "cargo": self.cargo,
            "banked": self.banked,
            "heat": self.heat,
            "dug_sites": list(self.dug_sites),
            "busts": self.busts,
        }


@dataclass(frozen=True)
class ActionRecord:
    player_index: int
    player_name: str
    action: dict[str, Any]
    event: dict[str, Any]


@dataclass(frozen=True)
class PlayerResult:
    final_result: str
    banked: int
    cargo: int
    busts: int


@dataclass(frozen=True)
class GameResult:
    players: tuple[str, ...]
    results: tuple[PlayerResult, ...]
    winner_index: int | None
    actions: tuple[ActionRecord, ...]
    events: tuple[dict[str, Any], ...]
    final_state: dict[str, Any]
    completed: bool

    @property
    def winner_name(self) -> str | None:
        if self.winner_index is None:
            return None
        return self.players[self.winner_index]


def route_site(route: str, depth: int) -> str:
    return f"{route}:{depth}"


def danger_score(player: PlayerState) -> int:
    if player.location != "route" or player.route is None:
        return 0
    route = ROUTES[player.route]
    return int(route["risk"]) + player.depth + player.heat + player.cargo // 5


def legal_actions(players: list[PlayerState], player_index: int) -> tuple[dict[str, Any], ...]:
    player = players[player_index]
    if player.location == "base":
        return tuple({"action": "depart", "route": route} for route in ROUTES)

    actions: list[dict[str, Any]] = [{"action": "return"}, {"action": "rest"}]
    assert player.route is not None
    if player.depth < int(ROUTES[player.route]["length"]):
        actions.append({"action": "advance"})
    site = route_site(player.route, player.depth)
    if site not in player.dug_sites:
        actions.append({"action": "dig"})
    return tuple(actions)


def public_state(players: list[PlayerState], current_player: int, action_count: int) -> dict[str, Any]:
    return {
        "action_count": action_count,
        "current_player": current_player,
        "target_banked": TARGET_BANKED,
        "routes": ROUTES,
        "players": [player.public_dict() for player in players],
    }


def _danger_event(player: PlayerState, rng: Random) -> dict[str, Any]:
    score = danger_score(player)
    roll = rng.randint(1, 20)
    bust = roll <= score
    return {"danger_score": score, "danger_roll": roll, "bust": bust}


def apply_action(
    players: list[PlayerState],
    player_index: int,
    action: dict[str, Any],
    rng: Random,
) -> dict[str, Any]:
    player = players[player_index]
    action_name = str(action.get("action"))
    before = player.public_dict()
    event: dict[str, Any] = {
        "type": "action_result",
        "player_index": player_index,
        "action": dict(action),
        "before": before,
    }

    if action_name == "depart":
        route = str(action.get("route"))
        if player.location != "base" or route not in ROUTES:
            raise ValueError(f"illegal depart action: {action}")
        player.location = "route"
        player.route = route
        player.depth = 1
        player.cargo = 0
        player.heat = 0
        player.dug_sites.clear()
    elif action_name == "advance":
        if player.location != "route" or player.route is None:
            raise ValueError("advance requires a route")
        if player.depth >= int(ROUTES[player.route]["length"]):
            raise ValueError("cannot advance past the end of a route")
        player.depth += 1
        player.heat += 1
        event.update(_danger_event(player, rng))
    elif action_name == "dig":
        if player.location != "route" or player.route is None:
            raise ValueError("dig requires a route")
        site = route_site(player.route, player.depth)
        if site in player.dug_sites:
            raise ValueError("site has already been dug this expedition")
        treasure = int(ROUTES[player.route]["treasure"][player.depth - 1])
        player.cargo += treasure
        player.dug_sites.append(site)
        player.heat += 2
        event["cargo_delta"] = treasure
        event.update(_danger_event(player, rng))
    elif action_name == "return":
        if player.location != "route":
            raise ValueError("return requires a route")
        event["banked_delta"] = player.cargo
        player.banked += player.cargo
        player.reset_expedition()
    elif action_name == "rest":
        if player.location != "route":
            raise ValueError("rest requires a route")
        player.heat = max(0, player.heat - 3)
    else:
        raise ValueError(f"unknown action: {action_name}")

    if event.get("bust"):
        lost_cargo = player.cargo
        player.busts += 1
        player.reset_expedition()
        event["lost_cargo"] = lost_cargo

    event["after"] = player.public_dict()
    return event


def determine_winner(players: list[PlayerState]) -> int | None:
    scores = [(player.banked, player.cargo, -player.busts) for player in players]
    best = max(scores)
    if scores.count(best) != 1:
        return None
    return scores.index(best)


def run_game(
    players: tuple[PlayerPort, PlayerPort, PlayerPort, PlayerPort],
    *,
    seed: int | None = None,
    max_actions: int = DEFAULT_MAX_ACTIONS,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> GameResult:
    rng = Random(seed)
    states = [PlayerState() for _ in players]
    actions: list[ActionRecord] = []
    events: list[dict[str, Any]] = []

    def emit(event: dict[str, Any]) -> None:
        event = {"event_index": len(events), **event}
        events.append(event)
        if on_event is not None:
            on_event(event)

    for index, player in enumerate(players):
        player.request(protocol.make_hello_request(index, PLAYER_COLORS[index]))

    current_player = 0
    completed = False
    winner_index: int | None = None
    emit({"type": "game_start", "players": [player.name for player in players], "colors": list(PLAYER_COLORS)})

    while len(actions) < max_actions and not completed:
        player = players[current_player]
        state = public_state(states, current_player, len(actions))
        player.notify({"type": protocol.TURN_START, "player_index": current_player, "state": state})
        emit({"type": "turn_start", "player_index": current_player, "player_name": player.name, "state": state})

        choices = legal_actions(states, current_player)
        response = player.request(
            protocol.make_choose_action_request(
                current_player,
                public_state(states, current_player, len(actions)),
                [dict(action) for action in choices],
            )
        )
        action = protocol.parse_choose_action_response(response, choices)
        event = apply_action(states, current_player, action, rng)
        event["player_name"] = player.name
        event["state"] = public_state(states, current_player, len(actions) + 1)
        emit(event)
        actions.append(ActionRecord(current_player, player.name, action, event))

        for target in players:
            target.notify(event)
        if event.get("bust"):
            for target in players:
                target.notify({**event, "type": protocol.BUST})
        if action.get("action") == "return":
            for target in players:
                target.notify({**event, "type": protocol.RETURN})

        if any(state.banked >= TARGET_BANKED for state in states):
            completed = True
            winner_index = determine_winner(states)
            break
        current_player = (current_player + 1) % len(players)

    if winner_index is None:
        winner_index = determine_winner(states)

    results = tuple(
        PlayerResult(
            final_result="win" if index == winner_index else "lose",
            banked=state.banked,
            cargo=state.cargo,
            busts=state.busts,
        )
        for index, state in enumerate(states)
    )
    final_state = public_state(states, current_player, len(actions))
    final_message = {
        "type": protocol.FINAL,
        "winner_index": winner_index,
        "winner_name": players[winner_index].name if winner_index is not None else None,
        "state": final_state,
        "completed": completed,
    }
    for player in players:
        player.notify(final_message)
    emit({**final_message, "type": "game_end"})

    return GameResult(
        players=tuple(player.name for player in players),
        results=results,
        winner_index=winner_index,
        actions=tuple(actions),
        events=tuple(events),
        final_state=final_state,
        completed=completed,
    )
