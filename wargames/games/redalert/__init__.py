from wargames.core.runtime.arena import GameDescriptor
from wargames.games.redalert.backend import RedAlertBackend
from wargames.games.redalert.config import RedAlertConfig
from wargames.games.redalert.missions import RedAlertMissionSpec

GAME = GameDescriptor(id="redalert", backend_cls=RedAlertBackend, config_cls=RedAlertConfig)

__all__ = ["GAME", "RedAlertBackend", "RedAlertConfig", "RedAlertMissionSpec"]
