from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

FREECIV_REWARD_SCHEMA = GameRewardSchema(
    game="freeciv",
    world_type="wargames.games.freeciv.world.FreeCivWorld",
    tick_rate=1,
    fields={
        "tick": RewardField("tick", "int", "track", "Freeciv turn number."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Victory state."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Defeat state."),
        "game.turn": RewardField("game.turn", "int", "track", "Freeciv turn number."),
        "game.year": RewardField("game.year", "int | None", "track", "Calendar year."),
        "game.server_state": RewardField(
            "game.server_state", "str", "track", "Freeciv server state."
        ),
        "game.ruleset": RewardField("game.ruleset", "str", "track", "Ruleset id."),
        "us.gold": RewardField("us.gold", "int", "maximize", "Player treasury."),
        "us.city_count": RewardField("us.city_count", "int", "maximize", "Player cities."),
        "us.unit_count": RewardField("us.unit_count", "int", "maximize", "Player units."),
        "us.known_tiles": RewardField(
            "us.known_tiles", "int", "maximize", "Known map tiles from the save file."
        ),
        "us.science_rate": RewardField(
            "us.science_rate", "int", "track", "Science tax allocation percentage."
        ),
        "us.tax_rate": RewardField(
            "us.tax_rate", "int", "track", "Tax allocation percentage."
        ),
        "players": RewardField("players", "tuple[PlayerState, ...]", "track", "All players."),
        "enemies": RewardField("enemies", "tuple[PlayerState, ...]", "track", "Alive enemies."),
    },
    primitives={
        "terminal": RewardPrimitiveSpec(
            "terminal",
            ("mission.finished", "mission.failed"),
            1.0,
            "terminal",
            "Success/failure outcome.",
        ),
        "delta_city_count": RewardPrimitiveSpec(
            "delta_city_count",
            ("us.city_count",),
            1.0,
            "per_step",
            "Increase in player city count.",
        ),
        "delta_unit_count": RewardPrimitiveSpec(
            "delta_unit_count",
            ("us.unit_count",),
            1.0,
            "per_step",
            "Increase in player unit count.",
        ),
        "delta_gold": RewardPrimitiveSpec(
            "delta_gold",
            ("us.gold",),
            1.0,
            "per_step",
            "Increase in player treasury.",
        ),
        "delta_known_tiles": RewardPrimitiveSpec(
            "delta_known_tiles",
            ("us.known_tiles",),
            1.0,
            "per_step",
            "New map knowledge from exploration.",
        ),
        "turn_progress": RewardPrimitiveSpec(
            "turn_progress",
            ("game.turn",),
            1.0,
            "per_step",
            "Advancement to later turns.",
        ),
    },
)
