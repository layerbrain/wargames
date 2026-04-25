from unittest import TestCase

from wargames.core.missions.spec import MissionSpec


class MissionSpecTests(TestCase):
    def test_uses_id_and_nested_game_namespace(self) -> None:
        mission = MissionSpec(id="core-test.scout", title="Scout", game="core-test", source="mock")
        self.assertEqual(mission.id, "core-test.scout")
        self.assertFalse(hasattr(mission, "scenario" + "_id"))
