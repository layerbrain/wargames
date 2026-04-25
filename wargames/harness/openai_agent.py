from __future__ import annotations

import json
import os
from typing import Any

from openai import BadRequestError, OpenAI, OpenAIError

from wargames.episode.media import frame_data_url
from wargames.harness.agent import AgentDecision, AgentObservation, ToolCall
from wargames.harness.agent_spec import AgentSpec

_INTEGER_ARGS = {"x", "y", "start_x", "start_y", "end_x", "end_y", "dx", "dy"}


class OpenAICompatibleAgent:
    def __init__(self, spec: AgentSpec) -> None:
        api_key = os.getenv(spec.api_key_env or "OPENAI_API_KEY")
        if not api_key:
            raise ValueError(f"agent {spec.id}: missing API key env {spec.api_key_env or 'OPENAI_API_KEY'}")
        self.id = spec.id
        self.model = spec.model or os.getenv("OPENAI_MODEL") or "kimi-k2.5"
        if bool(spec.config.get("reject_reasoning_models", True)) and _looks_like_reasoning_model(self.model):
            raise ValueError(f"agent {spec.id}: refusing reasoning model for smoke run: {self.model}")
        self.max_steps = int(spec.config.get("max_steps", 3))
        self.max_tokens = int(spec.config.get("max_tokens", 64))
        self.disable_reasoning = bool(spec.config.get("disable_reasoning", True))
        self.temperature = float(spec.config.get("temperature", 0.1))
        self.top_p = _optional_float(spec.config.get("top_p"))
        self.presence_penalty = _optional_float(spec.config.get("presence_penalty"))
        self.frequency_penalty = _optional_float(spec.config.get("frequency_penalty"))
        self.tool_choice = str(spec.config.get("tool_choice", "auto"))
        self.system_prompt = str(
            spec.config.get(
                "system_prompt",
                (
                    "You control a Red Alert game using only the provided computer-use tools. "
                    "Use a non-reasoning, short response. Play aggressively for this training smoke: "
                    "select combat units, issue attack/move commands, and scout toward the enemy. "
                    "Do not use wait during this smoke run. Prefer moving the mouse to a visible "
                    "screen coordinate, drag-selecting units, pressing the attack hotkey, or clicking "
                    "forward on the map. Return exactly one tool call."
                ),
            )
        )
        self.extra_body = _mapping(spec.config.get("extra_body"))
        self.reasoning_effort = _optional_string(spec.config.get("reasoning_effort"))
        self.client = OpenAI(
            api_key=api_key,
            base_url=_base_url(spec.base_url),
            timeout=float(spec.config.get("timeout_seconds", 12)),
            max_retries=int(spec.config.get("max_retries", 0)),
        )

    async def start(self, task: object) -> None:
        return None

    async def decide(self, obs: AgentObservation) -> AgentDecision:
        if obs.step_index >= self.max_steps:
            return AgentDecision(tool_call=None, stop=True, reason="model_smoke_complete")

        try:
            response = self._complete(obs, include_reasoning_disable=self.disable_reasoning)
        except BadRequestError:
            try:
                response = self._complete(obs, include_reasoning_disable=False)
            except OpenAIError:
                return AgentDecision(tool_call=_visible_fallback(obs.step_index), reason="model_api_error_visible_fallback")
        except OpenAIError:
            return AgentDecision(tool_call=_visible_fallback(obs.step_index), reason="model_api_error_visible_fallback")
        message = response.choices[0].message
        if message.tool_calls:
            call = message.tool_calls[0]
            tool_call = ToolCall(
                name=call.function.name,
                arguments=_normalize_arguments(json.loads(call.function.arguments or "{}")),
            )
            if tool_call.name == "wait":
                return AgentDecision(tool_call=_visible_fallback(obs.step_index), reason="model_wait_visible_fallback")
            return AgentDecision(
                tool_call=tool_call
            )
        parsed = _parse_json_tool_call(message.content or "")
        if parsed is not None:
            if parsed.name == "wait":
                return AgentDecision(tool_call=_visible_fallback(obs.step_index), reason="model_wait_visible_fallback")
            return AgentDecision(tool_call=parsed)
        return AgentDecision(tool_call=_visible_fallback(obs.step_index), reason="model_no_tool_call_visible_fallback")

    async def close(self) -> None:
        return None

    def _complete(self, obs: AgentObservation, *, include_reasoning_disable: bool):
        kwargs = self._completion_options(include_reasoning_disable=include_reasoning_disable)
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": _content(obs),
                },
            ],
            tools=[_tool_schema(tool.name, tool.description, tool.parameters) for tool in obs.tools],
            **kwargs,
        )

    def _completion_options(self, *, include_reasoning_disable: bool) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "tool_choice": self.tool_choice,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        if self.presence_penalty is not None:
            kwargs["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty is not None:
            kwargs["frequency_penalty"] = self.frequency_penalty
        extra_body = dict(self.extra_body)
        if include_reasoning_disable:
            extra_body = {
                "enable_thinking": False,
                "chat_template_kwargs": {"enable_thinking": False},
                "reasoning": {"effort": "none"},
                **extra_body,
            }
        if self.reasoning_effort:
            reasoning = _mapping(extra_body.get("reasoning"))
            reasoning["effort"] = self.reasoning_effort
            extra_body["reasoning"] = reasoning
        if extra_body:
            kwargs["extra_body"] = extra_body
        return kwargs


def create_agent(spec: AgentSpec) -> OpenAICompatibleAgent:
    return OpenAICompatibleAgent(spec)


def _base_url(value: str | None) -> str | None:
    if not value:
        return None
    clean = value.rstrip("/")
    if clean == "https://inference.do-ai.run":
        return f"{clean}/v1"
    return clean


def _looks_like_reasoning_model(model: str) -> bool:
    lowered = model.lower()
    markers = ("reasoner", "reasoning", "deepseek-r1", "r1-", "-r1", "o1", "o3", "o4-mini")
    return any(marker in lowered for marker in markers)


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _content(obs: AgentObservation) -> list[dict[str, Any]]:
    text = (
        f"Task: {obs.task.prompt or obs.task.id}\n"
        f"Step: {obs.step_index}\n"
        f"Elapsed seconds: {obs.elapsed_seconds:.2f}\n"
        f"Recent actions: {[event.tool_call.name for event in obs.history[-5:]]}\n"
        "Choose the next CUA tool."
    )
    blocks: list[dict[str, Any]] = [{"type": "text", "text": text}]
    image = frame_data_url(obs.frame)
    if image:
        blocks.append({"type": "image_url", "image_url": {"url": image}})
    return blocks


def _tool_schema(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def _parse_json_tool_call(content: str) -> ToolCall | None:
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        data = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return None
    name = data.get("name") or data.get("tool")
    if not isinstance(name, str):
        return None
    arguments = data.get("arguments") or data.get("input") or {}
    if not isinstance(arguments, dict):
        return None
    return ToolCall(name=name, arguments=_normalize_arguments(arguments))


def _visible_fallback(step_index: int) -> ToolCall:
    sequence = (
        ToolCall("drag", {"start_x": 420, "start_y": 330, "end_x": 780, "end_y": 620, "button": "left"}),
        ToolCall("key", {"key": "a", "modifiers": []}),
        ToolCall("click", {"x": 940, "y": 360, "button": "left"}),
    )
    return sequence[step_index % len(sequence)]


def _normalize_arguments(arguments: dict[str, object]) -> dict[str, object]:
    normalized = dict(arguments)
    for key in _INTEGER_ARGS & normalized.keys():
        value = normalized[key]
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            continue
        if isinstance(value, float):
            normalized[key] = int(round(value))
            continue
        if isinstance(value, str):
            try:
                normalized[key] = int(round(float(value)))
            except ValueError:
                pass
    return normalized
