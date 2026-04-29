from unittest import TestCase

from wargames.games.freeciv.missions import FreeCivMissionSpec
from wargames.games.freeciv.world import parse_freeciv_save, world_from_save_text


SAVE_TEXT = """
[game]
server_state="S_S_RUNNING"
turn=12
year=-3450
rulesetdir="civ2civ3"

[player0]
name="Suryavarman I"
username="wargames"
nation="Khmer"
government_name="Despotism"
is_alive=TRUE
gold=77
rates.tax=40
rates.science=60
rates.luxury=0
ncities=1
nunits=2
map_t0000="uupg"
u={"id","x","y","type_by_name","hp","moves","activity","done_moving"
101,4,5,"Settlers",20,6,"ACTIVITY_IDLE",FALSE
102,5,5,"Workers",10,3,"ACTIVITY_ROAD",TRUE
}
c={"id","name","x","y","size"
201,"Angkor",4,5,1
}

[player1]
name="Hammurabi"
username="Unassigned"
nation="Babylonian"
government_name="Despotism"
flags="ai"
is_alive=TRUE
gold=50
ncities=0
nunits=1
"""


class FreeCivWorldTests(TestCase):
    def test_parses_save_sections_and_tables(self) -> None:
        save = parse_freeciv_save(SAVE_TEXT)

        self.assertEqual(save["game"]["turn"], 12)
        self.assertEqual(save["player0"]["name"], "Suryavarman I")
        self.assertEqual(len(save["player0"]["u"]), 2)

    def test_builds_world_state_from_save(self) -> None:
        mission = FreeCivMissionSpec(
            id="freeciv.test",
            title="T",
            game="freeciv",
            source="builtin",
            time_limit_ticks=200,
            scenario_file="test.sav.gz",
        )

        world = world_from_save_text(SAVE_TEXT, mission)

        self.assertEqual(world.tick, 12)
        self.assertEqual(world.game.year, -3450)
        self.assertEqual(world.us.gold, 77)
        self.assertEqual(world.us.city_count, 1)
        self.assertEqual(world.us.known_tiles, 2)
        self.assertEqual(world.us.units[0].type, "Settlers")
        self.assertEqual(world.us.cities[0].name, "Angkor")
        self.assertEqual(len(world.enemies), 1)
        self.assertFalse(world.mission.finished)
        self.assertFalse(world.mission.failed)

    def test_marks_defeat_when_player_is_dead(self) -> None:
        mission = FreeCivMissionSpec(
            id="freeciv.test",
            title="T",
            game="freeciv",
            source="builtin",
            scenario_file="test.sav.gz",
        )
        text = SAVE_TEXT.replace("is_alive=TRUE", "is_alive=FALSE", 1)

        world = world_from_save_text(text, mission)

        self.assertTrue(world.mission.failed)
