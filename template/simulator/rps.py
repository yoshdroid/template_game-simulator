from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


VALID_HANDS = ("rock", "scissors", "paper")
WIN_TABLE = {
    ("rock", "scissors"),
    ("scissors", "paper"),
    ("paper", "rock"),
}


class PlayerPort(Protocol):
    name: str

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        ...

    def notify(self, message: dict[str, Any]) -> None:
        ...


@dataclass(frozen=True)
class PlayerResult:
    final_result: str
    wins: int


@dataclass(frozen=True)
class RoundRecord:
    number: int
    p1_hand: str
    p2_hand: str
    p1_result: str
    p2_result: str
    p1_wins: int
    p2_wins: int


@dataclass(frozen=True)
class RPSMatchResult:
    p1_name: str
    p2_name: str
    p1_result: PlayerResult
    p2_result: PlayerResult
    rounds: tuple[RoundRecord, ...] = field(default_factory=tuple)
    completed: bool = True

    @property
    def winner_name(self) -> str | None:
        if self.p1_result.final_result == "win":
            return self.p1_name
        if self.p2_result.final_result == "win":
            return self.p2_name
        return None


def judge(p1_hand: str, p2_hand: str) -> tuple[str, str]:
    if p1_hand not in VALID_HANDS:
        return ("lose", "win") if p2_hand in VALID_HANDS else ("draw", "draw")
    if p2_hand not in VALID_HANDS:
        return "win", "lose"
    if p1_hand == p2_hand:
        return "draw", "draw"
    if (p1_hand, p2_hand) in WIN_TABLE:
        return "win", "lose"
    return "lose", "win"


def _choice(port: PlayerPort, round_number: int, scores: dict[str, int]) -> str:
    response = port.request(
        {
            "type": "choice",
            "prompt": "hand",
            "valid": list(VALID_HANDS),
            "round": round_number,
            "scores": scores,
        }
    )
    return str(response.get("hand", response.get("choice", ""))).strip()


def _final_results(p1_wins: int, p2_wins: int, target_wins: int, completed: bool) -> tuple[str, str]:
    if completed and p1_wins >= target_wins:
        return "win", "lose"
    if completed and p2_wins >= target_wins:
        return "lose", "win"
    if p1_wins > p2_wins:
        return "win", "lose"
    if p2_wins > p1_wins:
        return "lose", "win"
    return "draw", "draw"


def run_match(
    p1: PlayerPort,
    p2: PlayerPort,
    *,
    target_wins: int = 10,
    step: int | None = None,
) -> RPSMatchResult:
    if target_wins < 1:
        raise ValueError("target_wins must be at least 1")
    if step is not None and step < 1:
        raise ValueError("step must be at least 1")

    p1.request({"type": "hello"})
    p2.request({"type": "hello"})

    p1_wins = 0
    p2_wins = 0
    round_number = 0
    records: list[RoundRecord] = []

    while p1_wins < target_wins and p2_wins < target_wins:
        if step is not None and round_number >= step:
            break

        round_number += 1
        scores = {p1.name: p1_wins, p2.name: p2_wins}
        p1_hand = _choice(p1, round_number, scores)
        p2_hand = _choice(p2, round_number, scores)
        p1_round_result, p2_round_result = judge(p1_hand, p2_hand)

        if p1_round_result == "win":
            p1_wins += 1
        elif p2_round_result == "win":
            p2_wins += 1

        p1.notify({"type": "result", "result": p1_round_result, "your_hand": p1_hand, "opponent_hand": p2_hand})
        p2.notify({"type": "result", "result": p2_round_result, "your_hand": p2_hand, "opponent_hand": p1_hand})

        records.append(
            RoundRecord(
                number=round_number,
                p1_hand=p1_hand,
                p2_hand=p2_hand,
                p1_result=p1_round_result,
                p2_result=p2_round_result,
                p1_wins=p1_wins,
                p2_wins=p2_wins,
            )
        )

    completed = p1_wins >= target_wins or p2_wins >= target_wins
    p1_final, p2_final = _final_results(p1_wins, p2_wins, target_wins, completed)
    p1.notify({"type": "final", "result": p1_final, "wins": p1_wins, "opponent_wins": p2_wins})
    p2.notify({"type": "final", "result": p2_final, "wins": p2_wins, "opponent_wins": p1_wins})

    return RPSMatchResult(
        p1_name=p1.name,
        p2_name=p2.name,
        p1_result=PlayerResult(final_result=p1_final, wins=p1_wins),
        p2_result=PlayerResult(final_result=p2_final, wins=p2_wins),
        rounds=tuple(records),
        completed=completed,
    )
