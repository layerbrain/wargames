from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Callable

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
from wargames.evaluation.profile import profile_registry
from wargames.evaluation.splits import TaskCatalog
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.games.redalert import GAME
from wargames.games.redalert.config import RedAlertConfig


ConfigFactory = Callable[[], WarGamesConfig]


class WarGamesPrimeEnv(vf.MultiTurnEnv):
    def __init__(
        self,
        *,
        tasks: tuple[TaskSpec, ...],
        split: str,
        profile_id: str,
        run_config: RunConfig,
        game_descriptor: GameDescriptor = GAME,
        config_factory: ConfigFactory = RedAlertConfig.from_env,
        max_turns: int = -1,
    ) -> None:
        self.tasks = tasks
        self.split = split
        self.profile_id = profile_id
        self.run_config = run_config
        self.game_descriptor = game_descriptor
        self.config_factory = config_factory
        dataset = _dataset(tasks)
        super().__init__(
            dataset=dataset,
            eval_dataset=dataset,
            rubric=build_prime_rubric(split=split),
            tool_defs=_tool_defs(),
            max_turns=max_turns,
            env_id="layerbrain/wargames",
        )

    async def setup_state(self, state: vf.State) -> vf.State:
        info = state.get("info", {})
        task = TaskSpec.from_mapping(dict(info["task_spec"]))
        profile = profile_registry.get(task.game, task.reward_profile)
        if task.split == "test" and profile.train_only:
            raise ValueError(f"test split cannot use train-only profile: {profile.id}")

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
                    task.prompt or "Play the Red Alert mission through the available computer-control tools.",
                    first_frame,
                )
            )
        ]
        return state

    async def env_response(self, messages: vf.Messages, state: vf.State, **kwargs: object) -> vf.Messages:
        ctrl: EpisodeController = state["ctrl"]
        call = _latest_tool_call(messages)
        if call is None:
            await ctrl.finish("agent_stop")
            state["final_env_response"] = [UserMessage(content="Episode stopped because the model did not call a CUA tool.")]
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
    split: str = "train",
    game: str = "redalert",
    reward_profile: str = "standard",
    recorder_mode: str = "none",
    max_turns: int = -1,
    game_descriptor: GameDescriptor | None = None,
    config_factory: ConfigFactory | None = None,
    **kwargs: object,
) -> vf.Environment:
    tasks = tuple(
        replace(task, reward_profile=reward_profile)
        for task in TaskCatalog.load("scenarios").tasks(game=game, split=split)
    )
    profile = profile_registry.get(game, reward_profile)
    if split == "test" and profile.train_only:
        raise ValueError(f"test split cannot use train-only profile: {profile.id}")
    return WarGamesPrimeEnv(
        tasks=tasks,
        split=split,
        profile_id=reward_profile,
        run_config=RunConfig(recorder_mode=recorder_mode),
        game_descriptor=game_descriptor or GAME,
        config_factory=config_factory or RedAlertConfig.from_env,
        max_turns=max_turns,
    )


def build_prime_rubric(*, split: str) -> vf.Rubric:
    is_train = split in {"train", "curriculum"}

    def episode_reward(state: vf.State) -> float:
        ctrl = state.get("ctrl")
        if ctrl is None:
            return 0.0
        if is_train:
            return float(ctrl.total_reward)
        return float(ctrl.total_breakdown.get("terminal", 0.0))

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


def _dataset(tasks: tuple[TaskSpec, ...]) -> Dataset:
    return Dataset.from_list(
        [
            {
                "prompt": [{"role": "user", "content": task.prompt or "Play the Red Alert mission."}],
                "answer": "",
                "task": task.id,
                "info": {"task_spec": task.to_mapping()},
            }
            for task in tasks
        ]
    )


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
