from __future__ import annotations

import json
import sys


def main() -> None:
    for _line in sys.stdin:
        print(json.dumps({"name": "wait", "arguments": {}}), flush=True)


if __name__ == "__main__":
    main()
