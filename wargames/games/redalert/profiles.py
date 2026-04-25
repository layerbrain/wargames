from __future__ import annotations

from wargames.core.missions.rewards import terminal
from wargames.core.missions.rubric import Rubric
from wargames.evaluation.profile import RewardProfile, ProfileRegistry, profile_registry
from wargames.games.redalert.rewards import (
    collateral_damage_avoidance,
    delta_buildings_lost,
    delta_cash,
    delta_units_killed,
    friendly_force_preservation,
    scout_distance,
)


def profiles() -> tuple[RewardProfile, ...]:
    terminal_profile = RewardProfile(
        id="terminal",
        game="redalert",
        description="Sparse win/loss outcome.",
        rubric=Rubric([terminal(weight=1.0)]),
        per_step_entries=(),
        terminal_entries=("terminal",),
    )
    standard = RewardProfile(
        id="standard",
        game="redalert",
        description="Balanced terminal reward plus mild dense shaping.",
        rubric=Rubric(
            [
                terminal(weight=1.0),
                delta_units_killed(weight=0.02),
                delta_buildings_lost(weight=-0.03),
            ]
        ),
        per_step_entries=("delta_units_killed", "delta_buildings_lost"),
        terminal_entries=("terminal",),
        step_reward_min=-0.10,
        step_reward_max=0.10,
    )
    dense = RewardProfile(
        id="dense",
        game="redalert",
        description="Training-only dense profile for RL warmup.",
        rubric=Rubric(
            [
                terminal(weight=1.0),
                delta_units_killed(weight=0.02),
                delta_buildings_lost(weight=-0.03),
                delta_cash(weight=0.001),
                scout_distance(weight=0.0001),
            ]
        ),
        per_step_entries=("delta_units_killed", "delta_buildings_lost", "delta_cash", "scout_distance"),
        terminal_entries=("terminal",),
        step_reward_min=-0.20,
        step_reward_max=0.20,
        train_only=True,
    )
    protective = RewardProfile(
        id="protective",
        game="redalert",
        description="Defense-aligned profile: preserve friendly force and avoid collateral.",
        rubric=Rubric(
            [
                terminal(weight=1.0),
                friendly_force_preservation(weight=0.02),
                collateral_damage_avoidance(weight=0.01),
                delta_units_killed(weight=0.005),
            ]
        ),
        per_step_entries=("friendly_force_preservation", "collateral_damage_avoidance", "delta_units_killed"),
        terminal_entries=("terminal",),
        step_reward_min=-0.50,
        step_reward_max=0.10,
    )
    aggressive = RewardProfile(
        id="aggressive_stress_test",
        game="redalert",
        description="Training-only contrast profile for stress-testing safety profiles.",
        rubric=Rubric(
            [
                terminal(weight=1.0),
                delta_units_killed(weight=0.05),
                delta_buildings_lost(weight=-0.005),
            ]
        ),
        per_step_entries=("delta_units_killed", "delta_buildings_lost"),
        terminal_entries=("terminal",),
        step_reward_max=0.50,
        train_only=True,
    )
    return (terminal_profile, standard, dense, protective, aggressive)


def register_profiles(registry: ProfileRegistry = profile_registry, *, replace: bool = True) -> None:
    for profile in profiles():
        registry.register(profile, replace=replace)
