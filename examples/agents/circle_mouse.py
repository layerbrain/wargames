from __future__ import annotations

import json
import math
import sys


def main() -> None:
    for step, _line in enumerate(sys.stdin):
        angle = step * 0.35
        x = int(640 + 180 * math.cos(angle))
        y = int(360 + 120 * math.sin(angle))
        action = {"name": "move_mouse", "arguments": {"x": x, "y": y}}
        print(json.dumps(action), flush=True)


if __name__ == "__main__":
    main()
