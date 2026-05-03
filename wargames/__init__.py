from wargames.core.config import WarGamesConfig
from wargames.core.runtime.arena import GameDescriptor, WarGames
from wargames.environments.native import WarGamesEnv


def load_environment(*args: object, **kwargs: object) -> object:
    from wargames.environments.prime import load_environment as load_prime_environment

    return load_prime_environment(*args, **kwargs)


__all__ = ["GameDescriptor", "WarGames", "WarGamesConfig", "WarGamesEnv", "load_environment"]
