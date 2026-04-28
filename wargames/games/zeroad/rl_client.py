from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib import error, parse, request


class ZeroADRLClient:
    def __init__(self, *, host: str, port: int, timeout: float = 10.0) -> None:
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    async def wait_ready(self, timeout: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            if await asyncio.to_thread(self._is_ready):
                return
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("0 A.D. RL interface did not become ready")
            await asyncio.sleep(0.05)

    async def reset(
        self,
        scenario_config: Mapping[str, Any],
        *,
        player_id: int,
        save_replay: bool = False,
    ) -> dict[str, Any]:
        query = {"playerID": str(player_id)}
        if save_replay:
            query["saveReplay"] = "1"
        body = json.dumps(scenario_config, separators=(",", ":"))
        payload = await asyncio.to_thread(
            self._post_text, f"reset?{parse.urlencode(query)}", body
        )
        return _json_object(payload)

    async def step(
        self, commands: Sequence[tuple[int, Mapping[str, Any]]] = ()
    ) -> dict[str, Any]:
        body = "\n".join(
            f"{player_id};{json.dumps(command, separators=(',', ':'))}"
            for player_id, command in commands
        )
        payload = await asyncio.to_thread(self._post_text, "step", body)
        return _json_object(payload)

    def _is_ready(self) -> bool:
        try:
            self._post_text("step", "")
        except RuntimeError as exc:
            return "HTTP " in str(exc)
        except OSError:
            return False
        return True

    def _post_text(self, route: str, body: str) -> str:
        req = request.Request(
            f"{self.base_url}/{route}",
            data=body.encode("utf-8"),
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                return response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"0 A.D. RL request failed: HTTP {exc.code}: {detail}") from exc


def _json_object(payload: str) -> dict[str, Any]:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("0 A.D. RL interface returned a non-object JSON payload")
    return data
