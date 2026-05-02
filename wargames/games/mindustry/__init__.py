from wargames.core.runtime.arena import GameDescriptor
from wargames.games.mindustry.backend import MindustryBackend
from wargames.games.mindustry.config import MindustryConfig
from wargames.games.mindustry.missions import MindustryMissionSpec
from wargames.games.mindustry.profiles import register_profiles

GAME = GameDescriptor(id="mindustry", backend_cls=MindustryBackend, config_cls=MindustryConfig)
register_profiles()

__all__ = ["GAME", "MindustryBackend", "MindustryConfig", "MindustryMissionSpec"]
