from unittest import TestCase

from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.missions import RedAlertMissionSpec
from wargames.games.redalert.process import openra_command, openra_environment


class RedAlertProcessTests(TestCase):
    def test_command_launches_directly_into_map(self) -> None:
        mission = RedAlertMissionSpec(id="redalert.soviet-01.normal", title="S", game="redalert", source="builtin", map="soviet-01")
        command = openra_command("/bin/openra", mission, RedAlertConfig())
        self.assertEqual(command[:3], ["/bin/openra", "Game.Mod=ra", "Launch.Map=soviet-01"])
        self.assertIn("Graphics.Mode=Windowed", command)
        self.assertIn("Graphics.FullscreenSize=1280,720", command)
        self.assertIn("Graphics.WindowedSize=1280,720", command)
        self.assertIn("Game.ViewportEdgeScroll=False", command)
        self.assertIn("Game.MouseScroll=Disabled", command)

    def test_environment_sets_dotnet_root_when_configured(self) -> None:
        env = openra_environment(RedAlertConfig(dotnet_root="/tmp/missing"), probe_socket="/tmp/p.sock")
        self.assertEqual(
            env,
            {
                "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
                "PROBE_SOCK": "/tmp/p.sock",
            },
        )
