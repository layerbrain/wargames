from wargames.core.runtime.arena import GameDescriptor
from wargames.games.redalert.backend import RedAlertBackend
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.missions import RedAlertMissionSpec
from wargames.games.redalert.profiles import register_profiles

GAME = GameDescriptor(id="redalert", backend_cls=RedAlertBackend, config_cls=RedAlertConfig)
register_profiles()

__all__ = ["GAME", "RedAlertBackend", "RedAlertConfig", "RedAlertMissionSpec"]
