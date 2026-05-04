from __future__ import annotations

from pathlib import Path

import league_match


def test_resolve_player_path_uses_cant_stop_players_directory():
    path = league_match.resolve_player_path("random_player.py")

    assert path.name == "random_player.py"
    assert path.parent.name == "players"


def test_read_player_version_reads_version_literal():
    assert league_match.read_player_version(Path("cant_stop/players/random_player.py"))


def test_aggregate_results_counts_wins_and_points(monkeypatch):
    root = Path("tests/_tmp_league_match")
    root.mkdir(exist_ok=True)
    log_path = root / "game.log"
    try:
        monkeypatch.setattr(league_match, "ROOT_DIR", root)
        log_path.write_text(
            "\n".join(
                [
                    "20260504_100000 cant_stop winner: Alice Alice 3 vs. Bob 1 vs. C 0 vs. D 2",
                    "20260504_100001 cant_stop winner: Bob Bob 3 vs. Alice 2 vs. C 1 vs. D 0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        totals = league_match.aggregate_results(["Alice", "Bob"])

        assert totals["Alice"] == {"wins": 1, "points": 5}
        assert totals["Bob"] == {"wins": 1, "points": 4}
    finally:
        log_path.unlink(missing_ok=True)
        root.rmdir()
