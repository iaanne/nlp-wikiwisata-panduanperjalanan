"""Bandingkan dua config dan cetak field yang berbeda."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wikiwisata.experiments.config import flatten, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Bandingkan dua config.")
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()

    left = flatten(load_config(args.left))
    right = flatten(load_config(args.right))
    keys = sorted(set(left) | set(right))
    changed = {
        key: {"left": left.get(key), "right": right.get(key)}
        for key in keys
        if left.get(key) != right.get(key)
    }
    print(json.dumps(changed, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
