from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from wargames.evaluation.profile_loader import load_profile_yaml
from wargames.games.redalert.profiles import profiles
from wargames.games.redalert.reward_schema import REDALERT_REWARD_SCHEMA


class RewardProfileTests(unittest.TestCase):
    def test_builtin_profiles_are_loaded_from_shipped_yaml(self) -> None:
        paths = sorted(Path("scenarios/redalert/profiles").glob("*.yaml"))
        yaml_ids = {load_profile_yaml(path).id for path in paths}

        self.assertEqual(yaml_ids, {profile.id for profile in profiles()})

    def test_shipped_yaml_profiles_load(self) -> None:
        paths = sorted(Path("scenarios/redalert/profiles").glob("*.yaml"))

        loaded = [load_profile_yaml(path).id for path in paths]

        self.assertIn("standard", loaded)
        self.assertIn("protective", loaded)

    def test_builtin_profile_loading_does_not_depend_on_cwd(self) -> None:
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                ids = {profile.id for profile in profiles()}
            finally:
                os.chdir(cwd)

        self.assertIn("protective", ids)
        self.assertIn("aggressive_stress_test", ids)

    def test_redalert_reward_schema_knows_protective_primitives(self) -> None:
        REDALERT_REWARD_SCHEMA.validate_primitive("friendly_force_preservation")
        REDALERT_REWARD_SCHEMA.validate_primitive("collateral_damage_avoidance")
