from __future__ import annotations

import asyncio
from dataclasses import dataclass

from wargames.core.runtime.arena import WarGames
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.episode.controller import RunSummary
from wargames.harness.agent import Agent
from wargames.harness.runner import run_task


@dataclass(frozen=True)
class LobbyRunSummary:
    lobby_id: str
    slots: dict[str, RunSummary]
    total_reward: float


async def run_lobby(
    *,
    lobby_id: str,
    tasks: dict[str, TaskSpec],
    agents: dict[str, Agent],
    run_config: RunConfig,
    war_games: dict[str, WarGames],
) -> LobbyRunSummary:
    missing_agents = set(tasks) - set(agents)
    missing_wg = set(tasks) - set(war_games)
    if missing_agents:
        raise ValueError(f"missing agents for slots: {', '.join(sorted(missing_agents))}")
    if missing_wg:
        raise ValueError(f"missing WarGames instances for slots: {', '.join(sorted(missing_wg))}")
    pairs = {
        slot: run_task(task=task, run_config=run_config, wg=war_games[slot], agent=agents[slot])
        for slot, task in tasks.items()
    }
    results = await asyncio.gather(*pairs.values())
    summaries = dict(zip(pairs.keys(), results, strict=True))
    return LobbyRunSummary(
        lobby_id=lobby_id,
        slots=summaries,
        total_reward=sum(summary.total_reward for summary in summaries.values()),
    )
