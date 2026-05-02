from wargames.core.runtime.arena import GameDescriptor
from wargames.games.doom.backend import DoomBackend
from wargames.games.doom.config import DoomConfig
from wargames.games.doom.missions import DoomMissionSpec
from wargames.games.doom.profiles import register_profiles

GAME = GameDescriptor(id="doom", backend_cls=DoomBackend, config_cls=DoomConfig)
register_profiles()

__all__ = ["GAME", "DoomBackend", "DoomConfig", "DoomMissionSpec"]
