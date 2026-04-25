from __future__ import annotations

import unittest
from pathlib import Path

from wargames.evaluation.profile_loader import load_profile_yaml
from wargames.games.redalert.profiles import profiles
from wargames.games.redalert.reward_schema import REDALERT_REWARD_SCHEMA


class RewardProfileTests(unittest.TestCase):
    def test_builtin_profiles_include_protective_and_aggressive(self) -> None:
        ids = {profile.id for profile in profiles()}

        self.assertIn("protective", ids)
        self.assertIn("aggressive_stress_test", ids)

    def test_shipped_yaml_profiles_load(self) -> None:
        paths = sorted(Path("scenarios/redalert/profiles").glob("*.yaml"))

        loaded = [load_profile_yaml(path).id for path in paths]

        self.assertIn("standard", loaded)
        self.assertIn("protective", loaded)

    def test_redalert_reward_schema_knows_protective_primitives(self) -> None:
        REDALERT_REWARD_SCHEMA.validate_primitive("friendly_force_preservation")
        REDALERT_REWARD_SCHEMA.validate_primitive("collateral_damage_avoidance")
