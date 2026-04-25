from __future__ import annotations

from wargames_openreward.env_redalert import WarGamesRedAlert

try:
    from fastapi import FastAPI
except Exception:  # pragma: no cover - optional runtime dependency
    FastAPI = None  # type: ignore[assignment]


if FastAPI is not None:
    app = FastAPI(title="WarGames OpenReward")

    @app.get("/splits")
    async def splits() -> list[dict[str, str]]:
        return WarGamesRedAlert.list_splits()

    @app.get("/variants")
    async def variants() -> list[dict[str, str]]:
        return WarGamesRedAlert.list_variants()

    @app.get("/tasks/{split}")
    async def tasks(split: str) -> list[dict[str, object]]:
        return WarGamesRedAlert.list_tasks(split)

    @app.get("/tools")
    async def tools() -> list[str]:
        return WarGamesRedAlert.list_tools()
else:
    app = None
