from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from wargames.evaluation.profile_loader import load_profile_yaml
from wargames.games.flightgear.profiles import register_profiles as register_flightgear_profiles
from wargames.games.flightgear.reward_schema import FLIGHTGEAR_REWARD_SCHEMA
from wargames.games.craftium.profiles import register_profiles as register_craftium_profiles
from wargames.games.craftium.reward_schema import CRAFTIUM_REWARD_SCHEMA
from wargames.games.freeciv.profiles import register_profiles as register_freeciv_profiles
from wargames.games.freeciv.reward_schema import FREECIV_REWARD_SCHEMA
from wargames.games.ikemen.profiles import register_profiles as register_ikemen_profiles
from wargames.games.ikemen.reward_schema import IKEMEN_REWARD_SCHEMA
from wargames.games.opensurge.profiles import register_profiles as register_opensurge_profiles
from wargames.games.opensurge.reward_schema import OPENSURGE_REWARD_SCHEMA
from wargames.games.redalert.profiles import profiles
from wargames.games.redalert.reward_schema import REDALERT_REWARD_SCHEMA
from wargames.games.supertuxkart.profiles import (
    register_profiles as register_supertuxkart_profiles,
)
from wargames.games.supertuxkart.reward_schema import SUPERTUXKART_REWARD_SCHEMA
from wargames.games.zeroad.profiles import register_profiles as register_zeroad_profiles
from wargames.games.zeroad.reward_schema import ZEROAD_REWARD_SCHEMA


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

    def test_flightgear_profiles_are_loaded_from_shipped_yaml(self) -> None:
        loaded = register_flightgear_profiles()

        self.assertEqual(["standard"], [profile.id for profile in loaded])

    def test_flightgear_reward_schema_declares_terminal_profile(self) -> None:
        FLIGHTGEAR_REWARD_SCHEMA.validate_primitive("terminal")

        profile = load_profile_yaml(
            Path("scenarios/flightgear/profiles/standard.yaml"), schema=FLIGHTGEAR_REWARD_SCHEMA
        )

        self.assertEqual("standard", profile.id)

    def test_profile_schema_rejects_unknown_primitive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.yaml"
            path.write_text(
                "\n".join(
                    [
                        "id: bad",
                        "game: flightgear",
                        "entries:",
                        "  - id: unknown",
                        "    fn: wargames.core.missions.rewards.terminal",
                        "    weight: 1.0",
                        "    when: terminal",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unknown reward primitive"):
                load_profile_yaml(path, schema=FLIGHTGEAR_REWARD_SCHEMA)

    def test_supertuxkart_profiles_are_loaded_from_shipped_yaml(self) -> None:
        loaded = register_supertuxkart_profiles()

        self.assertEqual(["standard"], [profile.id for profile in loaded])
        SUPERTUXKART_REWARD_SCHEMA.validate_primitive("terminal")

    def test_zeroad_profiles_are_loaded_from_shipped_yaml(self) -> None:
        loaded = register_zeroad_profiles()

        self.assertEqual(["standard"], [profile.id for profile in loaded])
        ZEROAD_REWARD_SCHEMA.validate_primitive("enemy_damage")

    def test_freeciv_profiles_are_loaded_from_shipped_yaml(self) -> None:
        loaded = register_freeciv_profiles()

        self.assertEqual(["standard"], [profile.id for profile in loaded])
        FREECIV_REWARD_SCHEMA.validate_primitive("delta_known_tiles")

    def test_craftium_profiles_are_loaded_from_shipped_yaml(self) -> None:
        loaded = register_craftium_profiles()

        self.assertEqual(["standard"], [profile.id for profile in loaded])
        CRAFTIUM_REWARD_SCHEMA.validate_primitive("delta_reward")

    def test_ikemen_profiles_are_loaded_from_shipped_yaml(self) -> None:
        loaded = register_ikemen_profiles()

        self.assertEqual(["standard"], [profile.id for profile in loaded])
        IKEMEN_REWARD_SCHEMA.validate_primitive("damage_dealt")

    def test_opensurge_profiles_are_loaded_from_shipped_yaml(self) -> None:
        loaded = register_opensurge_profiles()

        self.assertEqual(["standard"], [profile.id for profile in loaded])
        OPENSURGE_REWARD_SCHEMA.validate_primitive("delta_rings")
