from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_public_events(run_dir: Path) -> tuple[dict[str, Any], ...]:
    events: list[dict[str, Any]] = []
    for name in ("events.jsonl", "rewards.jsonl"):
        path = run_dir / name
        if not path.exists():
            continue
        events.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return tuple(events)
