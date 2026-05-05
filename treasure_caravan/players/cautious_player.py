from __future__ import annotations

try:
    from .bot_base import estimated_danger, player_state, run_player
except ImportError:
    from bot_base import estimated_danger, player_state, run_player


########################################
# Player Information & Records
########################################
PLAYER_NAME = "Caravan Cautious"
VERSION = "1.0"
FIRST_GAME_DATE = '2026/05/05 22:21'
LAST_GAME_DATE = '2026/05/05 22:21'
PLAY_TIMES = 1
WIN = 1
POINT = 6


def _has_action(actions, name):
    return next((action for action in actions if action.get("action") == name), None)


def strategy(message):
    actions = [dict(action) for action in message.get("legal_actions", [])]
    me = player_state(message)
    if me.get("location") == "base":
        for route in ("oasis", "ruins", "mirage"):
            action = {"action": "depart", "route": route}
            if action in actions:
                return action

    cargo = int(me.get("cargo", 0))
    if cargo >= 8 and _has_action(actions, "return"):
        return _has_action(actions, "return")

    risky_actions = [action for action in actions if action.get("action") in {"advance", "dig"}]
    safe_actions = [action for action in risky_actions if estimated_danger(message, action) < 9]
    if safe_actions:
        dig = _has_action(safe_actions, "dig")
        return dig or safe_actions[0]
    if _has_action(actions, "rest") and int(me.get("heat", 0)) > 0:
        return _has_action(actions, "rest")
    return _has_action(actions, "return") or actions[0]


if __name__ == "__main__":
    raise SystemExit(run_player(PLAYER_NAME, VERSION, strategy))
