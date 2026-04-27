from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from wargames.evaluation.profile_loader import load_yaml

AgentKind = Literal["openai", "python", "scripted-wait", "subprocess", "websocket"]


@dataclass(frozen=True)
class AgentSpec:
    id: str
    kind: AgentKind
    description: str = ""
    entrypoint: str | None = None
    command: tuple[str, ...] = ()
    url: str | None = None
    model: str | None = None
    provider: str | None = None
    api_key_env: str | None = None
    base_url: str | None = None
    env_file: str | None = None
    config: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AgentSpec":
        spec = cls(
            id=str(data["id"]),
            kind=_kind(str(data["kind"])),
            description=str(data.get("description", "")),
            entrypoint=_expand_optional(data.get("entrypoint")),
            command=tuple(str(item) for item in data.get("command", ())),
            url=_expand_optional(data.get("url")),
            model=_expand_optional(data.get("model")),
            provider=_expand_optional(data.get("provider")),
            api_key_env=str(data["api_key_env"]) if data.get("api_key_env") else None,
            base_url=_expand_optional(data.get("base_url")),
            env_file=str(data["env_file"]) if data.get("env_file") else None,
            config=_expand_config(dict(data.get("config", {}))),
        )
        spec.validate()
        return spec

    @classmethod
    def from_file(cls, path: Path) -> "AgentSpec":
        return cls.from_mapping(load_yaml(path))

    def validate(self) -> None:
        if self.kind == "python" and not self.entrypoint:
            raise ValueError(f"agent {self.id}: kind python requires entrypoint")
        if self.kind == "subprocess" and not self.command:
            raise ValueError(f"agent {self.id}: kind subprocess requires command")
        if self.kind == "websocket" and not self.url:
            raise ValueError(f"agent {self.id}: kind websocket requires url")
        if self.env_file and not _is_ignored_local_env(Path(self.env_file)):
            raise ValueError(f"agent {self.id}: env_file must be a local ignored dotenv file")


def _kind(value: str) -> AgentKind:
    if value not in {"openai", "python", "scripted-wait", "subprocess", "websocket"}:
        raise ValueError(f"invalid agent kind: {value}")
    return value  # type: ignore[return-value]


def _expand_optional(value: object) -> str | None:
    return None if value is None else os.path.expandvars(str(value))


def _expand_config(value: object) -> object:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_config(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_expand_config(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _expand_config(item) for key, item in value.items()}
    return value


def _is_ignored_local_env(path: Path) -> bool:
    return path.name.endswith(".env") or path.name == "local.env"
