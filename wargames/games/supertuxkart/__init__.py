from wargames.core.runtime.arena import GameDescriptor
from wargames.games.supertuxkart.backend import SuperTuxKartBackend
from wargames.games.supertuxkart.config import SuperTuxKartConfig
from wargames.games.supertuxkart.missions import SuperTuxKartMissionSpec
from wargames.games.supertuxkart.profiles import register_profiles

GAME = GameDescriptor(
    id="supertuxkart", backend_cls=SuperTuxKartBackend, config_cls=SuperTuxKartConfig
)
register_profiles()

__all__ = ["GAME", "SuperTuxKartBackend", "SuperTuxKartConfig", "SuperTuxKartMissionSpec"]
