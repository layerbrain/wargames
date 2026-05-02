from __future__ import annotations

from wargames.evaluation.profile import ProfileRegistry, RewardProfile, profile_registry
from wargames.evaluation.profile_loader import load_profile_dir, resolve_scenarios_root
from wargames.games.mindustry.reward_schema import MINDUSTRY_REWARD_SCHEMA


def register_profiles(registry: ProfileRegistry = profile_registry) -> list[RewardProfile]:
    path = resolve_scenarios_root() / "mindustry" / "profiles"
    profiles = load_profile_dir(path, schema=MINDUSTRY_REWARD_SCHEMA)
    for profile in profiles:
        registry.register(profile, replace=True)
    return profiles
