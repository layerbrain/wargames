from __future__ import annotations

from wargames.core.runtime.arena import GameDescriptor

SUPPORTED_GAMES = (
    "redalert",
    "flightgear",
    "supertuxkart",
    "zeroad",
    "freeciv",
    "doom",
    "supertux",
    "mindustry",
    "craftium",
    "ikemen",
    "opensurge",
    "quaver",
    "naev",
)


def load_game(id: str) -> GameDescriptor:
    if id == "redalert":
        from wargames.games.redalert import GAME

        return GAME
    if id == "flightgear":
        from wargames.games.flightgear import GAME

        return GAME
    if id == "supertuxkart":
        from wargames.games.supertuxkart import GAME

        return GAME
    if id == "zeroad":
        from wargames.games.zeroad import GAME

        return GAME
    if id == "freeciv":
        from wargames.games.freeciv import GAME

        return GAME
    if id == "doom":
        from wargames.games.doom import GAME

        return GAME
    if id == "supertux":
        from wargames.games.supertux import GAME

        return GAME
    if id == "mindustry":
        from wargames.games.mindustry import GAME

        return GAME
    if id == "craftium":
        from wargames.games.craftium import GAME

        return GAME
    if id == "ikemen":
        from wargames.games.ikemen import GAME

        return GAME
    if id == "opensurge":
        from wargames.games.opensurge import GAME

        return GAME
    if id == "quaver":
        from wargames.games.quaver import GAME

        return GAME
    if id == "naev":
        from wargames.games.naev import GAME

        return GAME
    raise ValueError(f"unknown game: {id}")
