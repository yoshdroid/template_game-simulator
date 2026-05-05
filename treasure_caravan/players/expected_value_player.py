from __future__ import annotations

try:
    from .bot_base import estimated_danger, player_state, route_info, run_player
except ImportError:
    from bot_base import estimated_danger, player_state, route_info, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "Caravan EV"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/05 22:21'
LAST_GAME_DATE = '2026/05/05 22:21'
PLAY_TIMES = 1
WIN = 0
POINT = 0


def action_value(message, action):
    me = player_state(message)
    banked = int(me.get("banked", 0))
    cargo = int(me.get("cargo", 0))
    route = str(me.get("route"))
    name = action.get("action")

    if name == "depart":
        route_order = {"oasis": 2.0, "ruins": 4.0, "mirage": 5.0}
        return banked + route_order.get(action.get("route"), 0.0)
    if name == "return":
        return banked + cargo + 8.0
    if name == "rest":
        return banked + cargo * 0.88 + min(int(me.get("heat", 0)), 3) * 1.5

    score = estimated_danger(message, action)
    survival = max(0.0, (20 - score) / 20)
    depth_bonus = 0.0
    cargo_after = cargo
    if name == "advance":
        depth_bonus = 2.5
    elif name == "dig":
        treasure = route_info(message, route).get("treasure", [])
        depth = int(me.get("depth", 0))
        if 1 <= depth <= len(treasure):
            cargo_after += int(treasure[depth - 1])
        depth_bonus = 1.0
    return banked + cargo_after * survival + depth_bonus - (1.0 - survival) * max(4, cargo_after)


def strategy(message):
    actions = [dict(action) for action in message.get("legal_actions", [])]
    return max(actions, key=lambda action: action_value(message, action)) if actions else None


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
