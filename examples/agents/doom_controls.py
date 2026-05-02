from __future__ import annotations

import json
import sys


def main() -> None:
    for raw_line in sys.stdin:
        observation = json.loads(raw_line)
        step = int(observation["step_index"])
        event = _event_for_step(step)
        print(json.dumps(event), flush=True)


def _event_for_step(step: int) -> dict[str, object]:
    schedule: dict[int, tuple[str, dict[str, object]]] = {
        0: ("key_down", {"key": "ArrowUp"}),
        45: ("key_down", {"key": "Control"}),
        58: ("key_up", {"key": "Control"}),
        90: ("key_down", {"key": "ArrowRight"}),
        155: ("key_up", {"key": "ArrowRight"}),
        185: ("key_down", {"key": "Space"}),
        195: ("key_up", {"key": "Space"}),
        225: ("key_down", {"key": "ArrowLeft"}),
        275: ("key_up", {"key": "ArrowLeft"}),
        305: ("key_down", {"key": "Control"}),
        320: ("key_up", {"key": "Control"}),
        360: ("key_up", {"key": "ArrowUp"}),
    }
    if step >= 375:
        return {"stop": True, "reason": "proof_complete"}
    if step in schedule:
        name, arguments = schedule[step]
        return {"name": name, "arguments": arguments}
    return {"name": "wait", "arguments": {"ms": 16}}


if __name__ == "__main__":
    main()
