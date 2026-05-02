from __future__ import annotations

import argparse
import ast
import json
import os
import queue
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from simulator.rps import RPSMatchResult, run_match


HEADER_KEYS = ("PLAYER_NAME", "VERSION", "FIRST_GAME_DATE", "LAST_GAME_DATE", "PLAY_TIMES", "WIN", "POINT")
ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PlayerHeader:
    path: Path
    player_name: str
    play_times: int
    win: int
    point: int


class PlayerProcessPort:
    def __init__(self, path: Path, seed: int, timeout_seconds: float = 5.0) -> None:
        self.path = path
        self.name = read_player_header(path).player_name
        self.timeout_seconds = timeout_seconds
        self.process = subprocess.Popen(
            [sys.executable, str(path), "--seed", str(seed)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._responses.put(json.loads(line))
            except json.JSONDecodeError:
                self._responses.put({"type": "error", "error": f"invalid json from {self.path.name}: {line}"})

    def request(self, message: dict[str, Any]) -> dict[str, Any]:
        self.notify(message)
        try:
            response = self._responses.get(timeout=self.timeout_seconds)
        except queue.Empty as exc:
            raise TimeoutError(f"{self.path} did not respond to {message.get('type')}") from exc
        if response.get("type") == "error":
            raise RuntimeError(str(response.get("error")))
        return response

    def notify(self, message: dict[str, Any]) -> None:
        if self.process.poll() is not None:
            raise RuntimeError(f"{self.path} already exited")
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a template game simulator match.")
    parser.add_argument("--casual_match", action="store_true", help="Do not update player header records.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed. Defaults to current datetime.")
    parser.add_argument("--step", type=int, default=None, help="Stop simulator after this many rounds.")
    parser.add_argument("--round", type=int, default=10, dest="target_wins", help="Wins required to finish.")
    args, unknown = parser.parse_known_args(argv)
    players: dict[int, str] = {}
    index = 0
    while index < len(unknown):
        token = unknown[index]
        match = re.fullmatch(r"--player(\d+)", token)
        if not match:
            parser.error(f"unknown argument: {token}")
        if index + 1 >= len(unknown):
            parser.error(f"{token} requires a path")
        players[int(match.group(1))] = unknown[index + 1]
        index += 2
    args.players = [Path(players[key]) for key in sorted(players)]
    if len(args.players) < 2:
        parser.error("at least --player1 and --player2 are required")
    if len(args.players) > 2:
        parser.error("this simulator currently supports exactly two players")
    return args


def read_player_header(path: Path) -> PlayerHeader:
    values: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Z_]+)\s*=\s*(.+)$", line)
        if not match:
            continue
        key, raw_value = match.groups()
        if key in HEADER_KEYS:
            values[key] = ast.literal_eval(raw_value)
        if {"PLAYER_NAME", "PLAY_TIMES", "WIN", "POINT"}.issubset(values):
            break
    missing = {"PLAYER_NAME", "PLAY_TIMES", "WIN", "POINT"} - set(values)
    if missing:
        raise ValueError(f"{path} is missing header keys: {', '.join(sorted(missing))}")
    return PlayerHeader(
        path=path,
        player_name=str(values["PLAYER_NAME"]),
        play_times=int(values["PLAY_TIMES"]),
        win=int(values["WIN"]),
        point=int(values["POINT"]),
    )


def update_player_header(path: Path, now_text: str, result: str, point_delta: int) -> None:
    text = path.read_text(encoding="utf-8")
    replacements = {
        "LAST_GAME_DATE": repr(now_text),
        "PLAY_TIMES": lambda value: str(int(value) + 1),
        "WIN": lambda value: str(int(value) + (1 if result == "win" else 0)),
        "POINT": lambda value: str(int(value) + point_delta),
    }

    def replace_line(match: re.Match[str]) -> str:
        key = match.group(1)
        current = match.group(2)
        replacement = replacements[key]
        new_value = replacement(current) if callable(replacement) else replacement
        return f"{key} = {new_value}"

    updated = re.sub(r"^(LAST_GAME_DATE|PLAY_TIMES|WIN|POINT)\s*=\s*(.+)$", replace_line, text, flags=re.MULTILINE)
    path.write_text(updated, encoding="utf-8")


def write_result_file(result: RPSMatchResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    data = {
        "p1": {"name": result.p1_name, "result": result.p1_result.final_result, "wins": result.p1_result.wins},
        "p2": {"name": result.p2_name, "result": result.p2_result.final_result, "wins": result.p2_result.wins},
        "completed": result.completed,
        "rounds": [record.__dict__ for record in result.rounds],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def append_game_log(now: datetime, result: RPSMatchResult) -> None:
    log_path = ROOT_DIR / "game.log"
    winner = result.winner_name or "draw"
    line = (
        f"{now.strftime('%Y%m%d_%H%M%S')} {winner} win: "
        f"{result.p1_name} {result.p1_result.wins} vs. {result.p2_name} {result.p2_result.wins}\n"
    )
    log_path.open("a", encoding="utf-8").write(line)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    now = datetime.now()
    seed = args.seed if args.seed is not None else int(now.strftime("%Y%m%d%H%M%S"))
    player_paths = [path.resolve() for path in args.players]

    for path in player_paths:
        if not path.exists():
            print(f"player file not found: {path}", file=sys.stderr)
            return 2

    headers = [read_player_header(path) for path in player_paths]
    casual_match = args.casual_match or len(set(player_paths)) != len(player_paths)
    ports = [PlayerProcessPort(path, seed) for path in player_paths]
    try:
        result = run_match(ports[0], ports[1], target_wins=args.target_wins, step=args.step)
        result_path = write_result_file(result, ROOT_DIR / "results")
        ports[0].request({"type": "bye"})
        ports[1].request({"type": "bye"})
    except Exception as exc:
        print(f"match failed: {exc}", file=sys.stderr)
        return 1
    finally:
        for port in ports:
            port.close()

    if not casual_match:
        now_text = now.strftime("%Y/%m/%d %H:%M")
        update_player_header(headers[0].path, now_text, result.p1_result.final_result, result.p1_result.wins)
        update_player_header(headers[1].path, now_text, result.p2_result.final_result, result.p2_result.wins)

    append_game_log(now, result)
    print(f"result: {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
