from __future__ import annotations

import time

from wargames.core.runtime.arena import WarGames
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.episode.controller import EpisodeController, RunSummary
from wargames.harness.agent import Agent, AgentObservation


async def run_task(*, task: TaskSpec, run_config: RunConfig, wg: WarGames, agent: Agent) -> RunSummary:
    controller = EpisodeController(task=task, run_config=run_config, wg=wg)
    await controller.start(agent_id=agent.id)
    await agent.start(task)
    end_reason = "unknown"
    t0 = time.monotonic()
    try:
        while True:
            obs = AgentObservation(
                task=task,
                frame=await controller.observe(),
                tools=wg.tools,
                history=tuple(event.action_only() for event in controller.public_history),
                step_index=len(controller.public_history),
                elapsed_seconds=time.monotonic() - t0,
            )
            decision = await agent.decide(obs)
            if decision.stop or decision.tool_call is None:
                end_reason = decision.reason or "agent_stop"
                break
            outcome = await controller.apply_tool_call(decision.tool_call.name, decision.tool_call.arguments)
            if outcome.finished or outcome.truncated:
                end_reason = outcome.end_reason or ("finished" if outcome.finished else "truncated")
                break
            if outcome.step + 1 >= task.max_steps:
                end_reason = "max_steps"
                break
            if time.monotonic() - t0 >= task.max_wall_seconds:
                end_reason = "wall_timeout"
                break
        await controller.finish(end_reason)
        return controller.summary()
    except Exception:
        controller.end_reason = "error"
        raise
    finally:
        await agent.close()
        await controller.close()
