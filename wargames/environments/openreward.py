from __future__ import annotations

from dataclasses import replace
from typing import Any, ClassVar, Literal

from openreward.environments import Environment, ImageBlock, Split, TextBlock, ToolOutput, tool
from pydantic import BaseModel, Field

from wargames.core.config import WarGamesConfig
from wargames.core.runtime.arena import GameDescriptor, WarGames
from wargames.episode.controller import EpisodeController, StepOutcome
from wargames.episode.media import frame_base64
from wargames.evaluation.profile import profile_registry
from wargames.evaluation.splits import TaskCatalog
from wargames.evaluation.task import RunConfig, TaskSpec
from wargames.games.redalert import GAME
from wargames.games.redalert.config import RedAlertConfig


Button = Literal["left", "right", "middle"]


class ClickParams(BaseModel):
    x: int
    y: int
    button: Button = "left"


class MoveMouseParams(BaseModel):
    x: int
    y: int


class DoubleClickParams(BaseModel):
    x: int
    y: int
    button: Button = "left"


class DragParams(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    button: Button = "left"


class KeyParams(BaseModel):
    key: str
    modifiers: list[str] = Field(default_factory=list)


class TypeTextParams(BaseModel):
    text: str


class ScrollParams(BaseModel):
    dx: int
    dy: int


class WarGamesRedAlert(Environment):
    env_id = "Layerbrain/WarGamesRedAlert"
    reward_profile: ClassVar[str] = "standard"
    game_descriptor: ClassVar[GameDescriptor] = GAME
    config_cls: ClassVar[type[WarGamesConfig]] = RedAlertConfig

    def __init__(
        self,
        task_spec: dict[str, Any] | None = None,
        secrets: dict[str, str] | None = None,
    ) -> None:
        super().__init__(task_spec=task_spec or {}, secrets=secrets or {})
        self.task: TaskSpec | None = None
        self.wg: WarGames | None = None
        self.ctrl: EpisodeController | None = None
        self.first_frame = None

    @classmethod
    def name(cls) -> str:
        return "wargamesredalert" if cls is WarGamesRedAlert else cls.reward_profile

    @classmethod
    def list_splits(cls) -> list[Split]:
        return [
            Split(name="debug", type="validation"),
            Split(name="train", type="train"),
            Split(name="validation", type="validation"),
            Split(name="test", type="test"),
            Split(name="curriculum", type="train"),
        ]

    @classmethod
    def list_tasks(cls, split: str) -> list[dict[str, Any]]:
        tasks = TaskCatalog.load("scenarios").tasks(game="redalert", split=split)
        return [replace(task, reward_profile=cls.reward_profile).to_mapping() for task in tasks]

    async def setup(self) -> None:
        if not self.task_spec:
            raise ValueError("WarGamesRedAlert requires a task_spec")
        task = TaskSpec.from_mapping(dict(self.task_spec))
        task = replace(task, reward_profile=self.reward_profile)
        profile = profile_registry.get(task.game, task.reward_profile)
        if task.split == "test" and profile.train_only:
            raise ValueError(f"test split cannot use train-only profile: {profile.id}")

        config_factory = getattr(self.config_cls, "from_env", self.config_cls)
        config = config_factory()
        self.wg = await WarGames.for_game(self.game_descriptor, config).__aenter__()
        self.task = task
        self.ctrl = EpisodeController(
            task=task,
            run_config=RunConfig(recorder_mode="summary_only", video_mode="none"),
            wg=self.wg,
        )
        self.first_frame = await self.ctrl.start(agent_id="openreward")

    async def teardown(self) -> None:
        if self.ctrl is not None:
            await self.ctrl.finish(self.ctrl.end_reason)
            await self.ctrl.close()
        if self.wg is not None:
            await self.wg.__aexit__(None, None, None)

    def get_prompt(self):
        if self.ctrl is None:
            raise RuntimeError("environment has not been set up")
        prompt = (
            self.task.prompt
            if self.task is not None and self.task.prompt
            else "Play the Red Alert mission through the available computer-control tools."
        )
        blocks = [TextBlock(text=prompt)]
        image = _image_block(self.first_frame)
        if image is not None:
            blocks.append(image)
        return blocks

    @tool
    async def click(self, params: ClickParams) -> ToolOutput:
        """Click a window-local pixel coordinate."""
        return self._to_tool_output(await self._apply("click", params.model_dump()))

    @tool
    async def move_mouse(self, params: MoveMouseParams) -> ToolOutput:
        """Move the visible pointer to a window-local pixel coordinate."""
        return self._to_tool_output(await self._apply("move_mouse", params.model_dump()))

    @tool
    async def double_click(self, params: DoubleClickParams) -> ToolOutput:
        """Double-click a window-local pixel coordinate."""
        return self._to_tool_output(await self._apply("double_click", params.model_dump()))

    @tool
    async def drag(self, params: DragParams) -> ToolOutput:
        """Drag between two window-local pixel coordinates."""
        return self._to_tool_output(await self._apply("drag", params.model_dump()))

    @tool
    async def key(self, params: KeyParams) -> ToolOutput:
        """Press a key, optionally with modifiers."""
        payload = params.model_dump()
        payload["modifiers"] = tuple(payload["modifiers"])
        return self._to_tool_output(await self._apply("key", payload))

    @tool
    async def type_text(self, params: TypeTextParams) -> ToolOutput:
        """Type text into the target window."""
        return self._to_tool_output(await self._apply("type_text", params.model_dump()))

    @tool
    async def scroll(self, params: ScrollParams) -> ToolOutput:
        """Scroll the target window."""
        return self._to_tool_output(await self._apply("scroll", params.model_dump()))

    @tool
    async def wait(self) -> ToolOutput:
        """Wait for exactly one game tick."""
        return self._to_tool_output(await self._apply("wait", {}))

    async def _apply(self, name: str, arguments: dict[str, object]) -> StepOutcome:
        if self.ctrl is None:
            raise RuntimeError("environment has not been set up")
        return await self.ctrl.apply_tool_call(name, arguments)

    def _to_tool_output(self, outcome: StepOutcome) -> ToolOutput:
        blocks = [
            TextBlock(
                text=(
                    f"step={outcome.step} reward={outcome.reward:.6f} "
                    f"total={self.ctrl.total_reward if self.ctrl else outcome.reward:.6f} "
                    f"finished={outcome.finished or outcome.truncated}"
                )
            )
        ]
        image = _image_block(outcome.frame)
        if image is not None:
            blocks.append(image)
        return ToolOutput(
            blocks=blocks,
            reward=outcome.reward,
            finished=outcome.finished or outcome.truncated,
            metadata={
                "step": outcome.step,
                "tick": outcome.tick,
                "game_seconds": outcome.game_seconds,
                "breakdown": dict(outcome.breakdown.entries),
                "end_reason": outcome.end_reason,
            },
        )


def _image_block(frame: object | None) -> ImageBlock | None:
    data = frame_base64(frame)
    if data is None:
        return None
    mime = getattr(frame, "mime", "image/png")
    return ImageBlock(data=data, mimeType=mime)


def _variant_class(profile_id: str) -> type[WarGamesRedAlert]:
    return type(
        f"WarGamesRedAlert{profile_id.title().replace('_', '')}",
        (WarGamesRedAlert,),
        {"reward_profile": profile_id, "__module__": __name__},
    )


WarGamesRedAlertTerminal = _variant_class("terminal")
WarGamesRedAlertStandard = _variant_class("standard")
WarGamesRedAlertDense = _variant_class("dense")
WarGamesRedAlertSpeedrun = _variant_class("speedrun")
WarGamesRedAlertProtective = _variant_class("protective")
WarGamesRedAlertAggressiveStressTest = _variant_class("aggressive_stress_test")

OPENREWARD_ENVIRONMENTS: tuple[type[WarGamesRedAlert], ...] = (
    WarGamesRedAlert,
    WarGamesRedAlertTerminal,
    WarGamesRedAlertStandard,
    WarGamesRedAlertDense,
    WarGamesRedAlertSpeedrun,
    WarGamesRedAlertProtective,
    WarGamesRedAlertAggressiveStressTest,
)
