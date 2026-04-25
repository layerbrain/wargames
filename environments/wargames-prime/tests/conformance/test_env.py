from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wargames_prime import load_environment


class PrimeConformanceTests(unittest.TestCase):
    def test_load_environment_returns_tasks(self) -> None:
        env = load_environment(split="debug", reward_profile="standard")

        self.assertTrue(env.dataset())
        self.assertEqual("standard", env.profile_id)
