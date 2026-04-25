from unittest import TestCase

from wargames.core.missions.registry import MissionRegistry
from wargames.core.missions.spec import MissionSpec


class MissionRegistryTests(TestCase):
    def test_rejects_duplicate_ids(self) -> None:
        registry = MissionRegistry()
        mission = MissionSpec(id="x.y", title="Y", game="x", source="mock")
        registry.add(mission)
        with self.assertRaises(ValueError):
            registry.add(mission)

    def test_get_returns_mission(self) -> None:
        mission = MissionSpec(id="x.y", title="Y", game="x", source="mock")
        registry = MissionRegistry((mission,))
        self.assertIs(registry.get("x.y"), mission)
