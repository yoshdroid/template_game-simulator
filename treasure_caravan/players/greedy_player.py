from __future__ import annotations

try:
    from .bot_base import player_state, run_player
except ImportError:
    from bot_base import player_state, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "Caravan Greedy"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/05 22:21'
LAST_GAME_DATE = '2026/05/05 22:21'
PLAY_TIMES = 1
WIN = 0
POINT = 0


def _has_action(actions, name):
    return next((action for action in actions if action.get("action") == name), None)


def strategy(message):
    actions = [dict(action) for action in message.get("legal_actions", [])]
    me = player_state(message)
    if me.get("location") == "base":
        for route in ("mirage", "ruins", "oasis"):
            action = {"action": "depart", "route": route}
            if action in actions:
                return action

    cargo = int(me.get("cargo", 0))
    if cargo >= 20 and _has_action(actions, "return"):
        return _has_action(actions, "return")
    return _has_action(actions, "dig") or _has_action(actions, "advance") or _has_action(actions, "return") or actions[0]


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
