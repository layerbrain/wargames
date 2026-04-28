from wargames.core.runtime.arena import GameDescriptor
from wargames.games.zeroad.backend import ZeroADBackend
from wargames.games.zeroad.config import ZeroADConfig
from wargames.games.zeroad.missions import ZeroADMissionSpec
from wargames.games.zeroad.profiles import register_profiles

GAME = GameDescriptor(id="zeroad", backend_cls=ZeroADBackend, config_cls=ZeroADConfig)
register_profiles()

__all__ = ["GAME", "ZeroADBackend", "ZeroADConfig", "ZeroADMissionSpec"]
