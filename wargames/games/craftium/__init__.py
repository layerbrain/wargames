from wargames.core.runtime.arena import GameDescriptor
from wargames.games.craftium.backend import CraftiumBackend
from wargames.games.craftium.config import CraftiumConfig
from wargames.games.craftium.missions import CraftiumMissionSpec
from wargames.games.craftium.profiles import register_profiles

GAME = GameDescriptor(id="craftium", backend_cls=CraftiumBackend, config_cls=CraftiumConfig)
register_profiles()

__all__ = ["GAME", "CraftiumBackend", "CraftiumConfig", "CraftiumMissionSpec"]
