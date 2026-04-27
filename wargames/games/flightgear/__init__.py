from wargames.core.runtime.arena import GameDescriptor
from wargames.games.flightgear.backend import FlightGearBackend
from wargames.games.flightgear.config import FlightGearConfig
from wargames.games.flightgear.missions import FlightGearMissionSpec
from wargames.games.flightgear.profiles import register_profiles

GAME = GameDescriptor(id="flightgear", backend_cls=FlightGearBackend, config_cls=FlightGearConfig)
register_profiles()

__all__ = ["GAME", "FlightGearBackend", "FlightGearConfig", "FlightGearMissionSpec"]
