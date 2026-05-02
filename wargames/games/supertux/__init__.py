from wargames.core.runtime.arena import GameDescriptor
from wargames.games.supertux.backend import SuperTuxBackend
from wargames.games.supertux.config import SuperTuxConfig
from wargames.games.supertux.missions import SuperTuxMissionSpec
from wargames.games.supertux.profiles import register_profiles

GAME = GameDescriptor(id="supertux", backend_cls=SuperTuxBackend, config_cls=SuperTuxConfig)
register_profiles()

__all__ = ["GAME", "SuperTuxBackend", "SuperTuxConfig", "SuperTuxMissionSpec"]
