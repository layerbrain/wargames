from __future__ import annotations

from wargames.evaluation.profile import ProfileRegistry, RewardProfile, profile_registry
from wargames.evaluation.profile_loader import load_profile_dir, resolve_scenarios_root


def profiles() -> tuple[RewardProfile, ...]:
    path = resolve_scenarios_root() / "redalert" / "profiles"
    loaded = tuple(load_profile_dir(path))
    if not loaded:
        raise FileNotFoundError(f"no Red Alert reward profiles found in {path}")
    return loaded


def register_profiles(registry: ProfileRegistry = profile_registry, *, replace: bool = True) -> None:
    for profile in profiles():
        registry.register(profile, replace=replace)
