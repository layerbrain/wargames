from __future__ import annotations

from wargames.evaluation.profile import ProfileRegistry, RewardProfile, profile_registry
from wargames.evaluation.profile_loader import load_profile_dir, resolve_scenarios_root
from wargames.games.redalert.reward_schema import REDALERT_REWARD_SCHEMA


def profiles() -> tuple[RewardProfile, ...]:
    path = resolve_scenarios_root() / "redalert" / "profiles"
    loaded = tuple(load_profile_dir(path, schema=REDALERT_REWARD_SCHEMA))
    if not loaded:
        raise FileNotFoundError(f"no Red Alert reward profiles found in {path}")
    return loaded


def register_profiles(
    registry: ProfileRegistry = profile_registry, *, replace: bool = True
) -> None:
    for profile in profiles():
        registry.register(profile, replace=replace)
