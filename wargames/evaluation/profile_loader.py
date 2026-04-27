from __future__ import annotations

import importlib
import inspect
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from wargames.core.missions.rubric import Rubric, RubricEntry
from wargames.evaluation.profile import RewardProfile
from wargames.evaluation.schema import GameRewardSchema


def resolve_scenarios_root(root: str | Path = "scenarios") -> Path:
    root_path = Path(root)
    if root_path.exists() or root_path != Path("scenarios"):
        return root_path

    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / "scenarios", parent.parent / "scenarios"):
            if candidate.exists():
                return candidate
    return root_path


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_profile_yaml(path: Path, *, schema: GameRewardSchema | None = None) -> RewardProfile:
    data = load_yaml(path)
    if schema is not None and str(data["game"]) != schema.game:
        raise ValueError(f"{path}: profile game {data['game']} does not match schema {schema.game}")
    entries: list[RubricEntry] = []
    per_step: list[str] = []
    terminal: list[str] = []
    seen: set[str] = set()
    for raw_entry in data.get("entries", ()):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"{path}: profile entries must be mappings")
        id = str(raw_entry["id"])
        if id in seen:
            raise ValueError(f"{path}: duplicate profile entry id: {id}")
        seen.add(id)
        when = str(raw_entry["when"])
        if when not in {"per_step", "terminal"}:
            raise ValueError(f"{path}: invalid reward timing for {id}: {when}")
        if schema is not None:
            primitive = schema.primitive(id)
            if primitive.when != when:
                raise ValueError(f"{path}: reward primitive {id} must use timing {primitive.when}")
        entry = _build_entry(id, raw_entry)
        entries.append(entry)
        if when == "per_step":
            per_step.append(id)
        else:
            terminal.append(id)
    step_min = _optional_float(data.get("step_reward_min"))
    step_max = _optional_float(data.get("step_reward_max"))
    if step_min is not None and step_max is not None and step_min > step_max:
        raise ValueError(f"{path}: step_reward_min must be <= step_reward_max")
    return RewardProfile(
        id=str(data["id"]),
        game=str(data["game"]),
        rubric=Rubric(entries),
        per_step_entries=tuple(per_step),
        terminal_entries=tuple(terminal),
        step_reward_min=step_min,
        step_reward_max=step_max,
        terminal_reward_weight=float(data.get("terminal_reward_weight", 1.0)),
        dense_reward_weight=float(data.get("dense_reward_weight", 1.0)),
        description=str(data.get("description", "")),
    )


def load_profile_dir(path: Path, *, schema: GameRewardSchema | None = None) -> list[RewardProfile]:
    return [
        load_profile_yaml(profile_path, schema=schema)
        for profile_path in sorted(path.glob("*.yaml"))
    ]


def resolve_dotted_path(path: str) -> object:
    module_name, sep, attr = path.partition(":")
    if not sep:
        module_name, sep, attr = path.rpartition(".")
    if not module_name or not attr:
        raise ValueError(f"invalid dotted path: {path}")
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def _build_entry(id: str, data: dict[str, Any]) -> RubricEntry:
    fn = resolve_dotted_path(str(data["fn"]))
    weight = float(data.get("weight", 1.0))
    args = dict(data.get("args", {}))
    if not callable(fn):
        raise ValueError(f"reward entry fn is not callable: {data['fn']}")
    signature = inspect.signature(fn)
    if "weight" in signature.parameters and "weight" not in args:
        args["weight"] = weight
    value = fn(**args)
    if isinstance(value, RubricEntry):
        return replace(value, id=id, weight=weight)
    if callable(value):
        return RubricEntry(id=id, fn=value, weight=weight)
    raise ValueError(f"reward entry fn must return RubricEntry or callable: {data['fn']}")


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)
