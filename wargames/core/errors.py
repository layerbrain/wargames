class WarGamesError(Exception):
    """Base exception for recoverable WarGames failures."""


class ConfigError(WarGamesError):
    pass


class GameNotInstalled(WarGamesError):
    pass


class ProbeNotInstalled(WarGamesError):
    pass


class ProbeError(WarGamesError):
    pass


class WindowNotFound(WarGamesError):
    pass


class DependencyMissing(WarGamesError):
    pass


class UnsupportedAction(WarGamesError):
    pass


class MissionNotFound(WarGamesError):
    pass


class NotYourTurn(WarGamesError):
    pass


class LobbyFull(WarGamesError):
    pass


class LobbyStateError(WarGamesError):
    pass
