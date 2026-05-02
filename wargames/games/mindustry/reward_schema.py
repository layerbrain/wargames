from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

MINDUSTRY_REWARD_SCHEMA = GameRewardSchema(
    game="mindustry",
    world_type="wargames.games.mindustry.world.MindustryWorld",
    tick_rate=60,
    fields={
        "tick": RewardField("tick", "int", "track", "WarGames step tick."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Win wave reached or game won."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Core destroyed or game lost."),
        "game.map": RewardField("game.map", "str", "track", "Map name."),
        "game.wave": RewardField("game.wave", "int", "maximize", "Survival wave."),
        "game.enemies": RewardField("game.enemies", "int", "minimize", "Live enemy count."),
        "game.won": RewardField("game.won", "bool", "maximize", "Mindustry win flag."),
        "game.game_over": RewardField("game.game_over", "bool", "track", "Mindustry game-over flag."),
        "us.cores": RewardField("us.cores", "int", "maximize", "Player core count."),
        "us.units": RewardField("us.units", "int", "maximize", "Player unit count."),
        "us.buildings": RewardField("us.buildings", "int", "maximize", "Player building count."),
        "us.items": RewardField("us.items", "int", "maximize", "Items in team cores."),
        "us.core_health": RewardField("us.core_health", "float", "maximize", "Total core health."),
        "teams": RewardField("teams", "tuple[TeamState, ...]", "track", "Active team summaries."),
    },
    primitives={
        "terminal": RewardPrimitiveSpec(
            "terminal",
            ("mission.finished", "mission.failed"),
            1.0,
            "terminal",
            "Success/failure outcome.",
        ),
        "delta_wave": RewardPrimitiveSpec(
            "delta_wave",
            ("game.wave",),
            1.0,
            "per_step",
            "Reward surviving new waves.",
        ),
        "delta_items": RewardPrimitiveSpec(
            "delta_items",
            ("us.items",),
            1.0,
            "per_step",
            "Reward item accumulation.",
        ),
        "delta_buildings": RewardPrimitiveSpec(
            "delta_buildings",
            ("us.buildings",),
            1.0,
            "per_step",
            "Reward factory/base expansion.",
        ),
        "core_health": RewardPrimitiveSpec(
            "core_health",
            ("us.core_health",),
            1.0,
            "per_step",
            "Reward keeping cores alive.",
        ),
        "enemy_pressure": RewardPrimitiveSpec(
            "enemy_pressure",
            ("game.enemies",),
            1.0,
            "per_step",
            "Penalty for unmanaged enemy pressure.",
        ),
        "time_penalty": RewardPrimitiveSpec(
            "time_penalty",
            ("tick",),
            1.0,
            "per_step",
            "Small pressure to progress efficiently.",
        ),
    },
)
