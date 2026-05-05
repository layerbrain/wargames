from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Callable, cast

import verifiers as vf
from datasets import Dataset
from verifiers.types import (
    ImageUrlContentPart,
    ImageUrlSource,
    TextContentPart,
    Tool,
    ToolMessage,
    UserMessage,
)

from wargames.core.config import WarGamesConfig
from wargames.core.control.tools import CUA_TOOL_SPECS
from wargames.core.runtime.arena import GameDescriptor, WarGames
from wargames.episode.controller import EpisodeController
from wargames.episode.media import frame_data_url
from wargames.evaluation.task import RunConfig, TaskSpec, canonical_task_id
from wargames.games.redalert import GAME
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.registry import load_game


ConfigFactory = Callable[[], WarGamesConfig]


class WarGamesPrimeEnv(vf.MultiTurnEnv):
    def __init__(
        self,
        *,
        tasks: tuple[TaskSpec, ...],
        profile_id: str,
        run_config: RunConfig,
        game_descriptor: GameDescriptor = GAME,
        config_factory: ConfigFactory = RedAlertConfig.from_env,
        max_turns: int = -1,
    ) -> None:
        self.tasks = tasks
        self.profile_id = profile_id
        self.run_config = run_config
        self.game_descriptor = game_descriptor
        self.config_factory = config_factory
        dataset = _dataset(tasks)
        super().__init__(
            dataset=dataset,
            eval_dataset=dataset,
            rubric=build_prime_rubric(),
            tool_defs=_tool_defs(),
            max_turns=max_turns,
            env_id="layerbrain/wargames",
        )

    async def setup_state(self, state: vf.State) -> vf.State:
        info = state.get("info", {})
        task = TaskSpec.from_mapping(dict(info["task_spec"]))

        wg = await WarGames.for_game(
            self.game_descriptor,
            replace(self.config_factory(), capture_frames=True),
        ).__aenter__()
        ctrl = EpisodeController(task=task, run_config=self.run_config, wg=wg)
        first_frame = await ctrl.start(agent_id="prime")

        state["wg"] = wg
        state["ctrl"] = ctrl
        state["wargames_trace"] = [
            {"step": 0, "tick": 0, "game_seconds": 0.0, "reward": 0.0, "finished": False}
        ]
        state["prompt"] = [
            UserMessage(
                content=_content(
                    task.prompt or "Play the mission through the available computer-control tools.",
                    first_frame,
                )
            )
        ]
        return state

    async def env_response(
        self, messages: vf.Messages, state: vf.State, **kwargs: object
    ) -> vf.Messages:
        ctrl: EpisodeController = state["ctrl"]
        call = _latest_tool_call(messages)
        if call is None:
            await ctrl.finish("agent_stop")
            state["final_env_response"] = [
                UserMessage(content="Episode stopped because the model did not call a CUA tool.")
            ]
            return state["final_env_response"]

        name, arguments, call_id = call
        outcome = await ctrl.apply_tool_call(name, arguments)
        state["wargames_trace"].append(
            {
                "step": outcome.step,
                "tick": outcome.tick,
                "game_seconds": outcome.game_seconds,
                "reward": outcome.reward,
                "finished": outcome.finished,
                "truncated": outcome.truncated,
                "breakdown": dict(outcome.breakdown.entries),
            }
        )
        if outcome.finished or outcome.truncated:
            await ctrl.finish(outcome.end_reason)

        content = _content(
            json.dumps(
                {
                    "step": outcome.step,
                    "reward": outcome.reward,
                    "total_reward": ctrl.total_reward,
                    "finished": outcome.finished or outcome.truncated,
                    "end_reason": outcome.end_reason,
                    "breakdown": dict(outcome.breakdown.entries),
                },
                sort_keys=True,
            ),
            outcome.frame,
        )
        return [ToolMessage(tool_call_id=call_id, content=content)]

    @vf.stop
    async def wargames_episode_done(self, state: vf.State) -> bool:
        ctrl = state.get("ctrl")
        return bool(
            ctrl
            and (
                ctrl.finished
                or ctrl.truncated
                or ctrl.end_reason in {"agent_stop", "max_steps", "wall_timeout"}
            )
        )

    @vf.cleanup
    async def close_wargames(self, state: vf.State) -> None:
        ctrl = state.get("ctrl")
        if ctrl is not None:
            await ctrl.finish(ctrl.end_reason)
            await ctrl.close()
        wg = state.get("wg")
        if wg is not None:
            await wg.__aexit__(None, None, None)


def load_environment(
    game: str = "redalert",
    mission: str | None = None,
    missions: tuple[str, ...] | list[str] | None = None,
    seed: int = 0,
    seeds: tuple[int, ...] | list[int] | None = None,
    reward_profile: str = "standard",
    recorder_mode: str = "none",
    max_steps: int | None = None,
    max_turns: int = -1,
    game_descriptor: GameDescriptor | None = None,
    config_factory: ConfigFactory | None = None,
    **kwargs: object,
) -> vf.Environment:
    default_game_descriptor, default_config_factory = _game_runtime(game)
    runtime = game_descriptor or default_game_descriptor
    runtime_config = config_factory or default_config_factory
    mission_ids = _selected_missions(runtime, runtime_config, mission=mission, missions=missions)
    seed_values = tuple(int(value) for value in (seeds or (seed,)))
    tasks = tuple(
        TaskSpec(
            id=canonical_task_id(game, mission_id, seed_value),
            game=game,
            mission_id=mission_id,
            seed=seed_value,
            reward_profile=reward_profile,
            max_steps=max_steps if max_steps is not None else 512,
            prompt=f"Play {mission_id} through the available computer-control tools.",
        )
        for mission_id in mission_ids
        for seed_value in seed_values
    )
    return WarGamesPrimeEnv(
        tasks=tasks,
        profile_id=reward_profile,
        run_config=RunConfig(recorder_mode=recorder_mode),
        game_descriptor=runtime,
        config_factory=runtime_config,
        max_turns=max_turns,
    )


def build_prime_rubric() -> vf.Rubric:
    def episode_reward(state: vf.State) -> float:
        ctrl = state.get("ctrl")
        if ctrl is None:
            return 0.0
        return float(ctrl.total_reward)

    def dense_breakdown(state: vf.State) -> float:
        ctrl = state.get("ctrl")
        if ctrl is None:
            return 0.0
        return float(sum(value for key, value in ctrl.total_breakdown.items() if key != "terminal"))

    def elapsed_game_seconds(state: vf.State) -> float:
        trace = state.get("wargames_trace") or ()
        if not trace:
            return 0.0
        return float(trace[-1].get("game_seconds", 0.0))

    return vf.Rubric(
        funcs=[episode_reward, dense_breakdown, elapsed_game_seconds],
        weights=[1.0, 0.0, 0.0],
    )


def _selected_missions(
    game: GameDescriptor,
    config_factory: ConfigFactory,
    *,
    mission: str | None,
    missions: tuple[str, ...] | list[str] | None,
) -> tuple[str, ...]:
    if mission and missions:
        raise ValueError("use mission or missions, not both")
    if mission:
        return (mission,)
    if missions:
        return tuple(str(item) for item in missions)
    available = game.backend_cls(config_factory()).missions()
    if not available:
        raise ValueError(f"game has no missions: {game.id}")
    return (available[0].id,)


def _dataset(tasks: tuple[TaskSpec, ...]) -> Dataset:
    return Dataset.from_list(
        [
            {
                "prompt": [{"role": "user", "content": task.prompt or "Play the mission."}],
                "answer": "",
                "mission": task.mission_id,
                "info": {"task_spec": task.to_mapping()},
            }
            for task in tasks
        ]
    )


def _game_runtime(game: str) -> tuple[GameDescriptor, ConfigFactory]:
    runtime = load_game(game)
    from_env = getattr(runtime.config_cls, "from_env", None)
    if not callable(from_env):
        raise ValueError(f"game config has no from_env: {game}")
    return runtime, cast(ConfigFactory, from_env)


def _tool_defs() -> list[Tool]:
    return [
        Tool(name=tool.name, description=tool.description, parameters=tool.parameters, strict=True)
        for tool in CUA_TOOL_SPECS
    ]


def _content(text: str, frame: object | None) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [TextContentPart(text=text).model_dump()]
    image_url = frame_data_url(frame)
    if image_url is not None:
        parts.append(ImageUrlContentPart(image_url=ImageUrlSource(url=image_url)).model_dump())
    return parts


def _latest_tool_call(messages: vf.Messages) -> tuple[str, dict[str, object], str] | None:
    if not messages:
        return None
    message = messages[-1]
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls is None and isinstance(message, dict):
        tool_calls = message.get("tool_calls")
    if not tool_calls:
        return None
    tool_call = tool_calls[0]
    name = getattr(tool_call, "name", None)
    arguments = getattr(tool_call, "arguments", None)
    call_id = getattr(tool_call, "id", "wargames-tool-call")
    if isinstance(tool_call, dict):
        name = tool_call.get("name") or tool_call.get("function", {}).get("name")
        arguments = tool_call.get("arguments") or tool_call.get("function", {}).get("arguments")
        call_id = str(tool_call.get("id") or call_id)
    if not name:
        return None
    if isinstance(arguments, str):
        payload = json.loads(arguments or "{}")
    elif isinstance(arguments, dict):
        payload = arguments
    else:
        payload = {}
    return str(name), dict(payload), str(call_id)
