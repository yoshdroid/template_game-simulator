from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .gui import show_board
except ImportError:
    from gui import show_board


def main() -> int:
    parser = argparse.ArgumentParser(description="Show a Can't Stop result board.")
    parser.add_argument("result_json", type=Path)
    args = parser.parse_args()
    data = json.loads(args.result_json.read_text(encoding="utf-8"))
    show_board(data["final_board"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
