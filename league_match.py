from __future__ import annotations

import argparse
import ast
import itertools
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from cant_stop.master import read_player_header


ROOT_DIR = Path(__file__).resolve().parent
PLAYER_DIR = ROOT_DIR / "cant_stop" / "players"
MASTER_PATH = ROOT_DIR / "cant_stop" / "master.py"
SAVE_DIR = ROOT_DIR / ".save"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Can't Stop league match.")
    parser.add_argument("--players", nargs=4, required=True, help="Four player .py files.")
    parser.add_argument("--round", type=int, default=1, help="Number of seed rounds. Defaults to 1.")
    parser.add_argument("--casual_match", action="store_true", help="Pass --casual_match to master.py.")
    parser.add_argument("--no_result_json", action="store_true", help="Pass --no_result_json to master.py.")
    args = parser.parse_args()
    if args.round < 1:
        parser.error("--round must be at least 1")
    return args


def resolve_player_path(value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    candidate = PLAYER_DIR / value
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(f"player file not found: {value}")


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def print_player_info(headers) -> None:
    for header in headers:
        rate = (header.win * 1000 // header.play_times) / 10 if header.play_times > 0 else 0.0
        print(f"{header.player_name} (ver.{read_player_version(header.path)}): WIN_RATE {rate}%")


def read_player_version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^VERSION\s*=\s*(.+)$", line)
        if match:
            return str(ast.literal_eval(match.group(1)))
    return ""


def move_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.move(str(source), str(destination))


def prepare_workspace() -> None:
    if SAVE_DIR.exists():
        raise FileExistsError(f"{SAVE_DIR} already exists; restore or remove it before running")
    SAVE_DIR.mkdir()
    move_if_exists(ROOT_DIR / "game.log", SAVE_DIR / "game.log")
    move_if_exists(ROOT_DIR / "results", SAVE_DIR / "results")
    (ROOT_DIR / "results").mkdir()


def restore_previous_outputs() -> None:
    current_log = ROOT_DIR / "game.log"
    current_results = ROOT_DIR / "results"
    if current_log.exists():
        current_log.unlink()
    if current_results.exists():
        shutil.rmtree(current_results)
    move_if_exists(SAVE_DIR / "game.log", ROOT_DIR / "game.log")
    move_if_exists(SAVE_DIR / "results", ROOT_DIR / "results")
    if SAVE_DIR.exists():
        SAVE_DIR.rmdir()


def run_master(players: tuple[Path, ...], seed: int, casual_match: bool, no_result_json: bool) -> None:
    command = [
        sys.executable,
        str(MASTER_PATH),
        "--player1",
        str(players[0]),
        "--player2",
        str(players[1]),
        "--player3",
        str(players[2]),
        "--player4",
        str(players[3]),
        "--seed",
        str(seed),
        "--silent",
    ]
    if casual_match:
        command.append("--casual_match")
    if no_result_json:
        command.append("--no_result_json")
    completed = subprocess.run(command, cwd=ROOT_DIR, text=True, capture_output=True)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"master.py failed with exit code {completed.returncode}")


def run_league(player_paths: list[Path], rounds: int, casual_match: bool, no_result_json: bool) -> None:
    for round_index in range(rounds):
        for order in itertools.permutations(player_paths):
            print(".", end="", flush=True)
            run_master(order, round_index, casual_match, no_result_json)
        print()


def aggregate_results(player_names: list[str]) -> dict[str, dict[str, int]]:
    totals = {name: {"wins": 0, "points": 0} for name in player_names}
    log_path = ROOT_DIR / "game.log"
    if not log_path.exists():
        return totals

    for line in log_path.read_text(encoding="utf-8").splitlines():
        for name in player_names:
            if f"winner: {name} " in line:
                totals[name]["wins"] += 1
            match = re.search(rf"{re.escape(name)}\s+(\d+)(?:\s+vs\.|$)", line)
            if match:
                totals[name]["points"] += int(match.group(1))
    return totals


def tournament_winners(headers, totals: dict[str, dict[str, int]]) -> list[str]:
    best = max((totals[header.player_name]["wins"], totals[header.player_name]["points"]) for header in headers)
    return [header.player_name for header in headers if (totals[header.player_name]["wins"], totals[header.player_name]["points"]) == best]


def archive_tournament_outputs(started_at: str) -> Path:
    archive_dir = ROOT_DIR / f"tournament_results_{started_at}"
    if archive_dir.exists():
        raise FileExistsError(f"{archive_dir} already exists")
    archive_dir.mkdir()
    move_if_exists(ROOT_DIR / "results", archive_dir / "results")
    move_if_exists(ROOT_DIR / "game.log", archive_dir / "game.log")
    return archive_dir


def main() -> int:
    args = parse_args()
    try:
        player_paths = [resolve_player_path(value) for value in args.players]
        if len(set(player_paths)) != len(player_paths):
            raise ValueError("--players must contain four different player files")
        headers = [read_player_header(path) for path in player_paths]
        started_at = timestamp()

        print(f"League-Match start {started_at}")
        print_player_info(headers)

        prepare_workspace()
        try:
            run_league(player_paths, args.round, args.casual_match, args.no_result_json)
            totals = aggregate_results([header.player_name for header in headers])
            for header in headers:
                print(f"{header.player_name} gets {totals[header.player_name]['points']} point, {totals[header.player_name]['wins']} win")
            winners = tournament_winners(headers, totals)
            print(f"%% Winner is {', '.join(winners)} %%")
            archive_tournament_outputs(started_at)
        finally:
            restore_previous_outputs()

        print(f"League-Match done")
    except Exception as exc:
        print(f"League-Match failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
