from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

ZEROAD_REWARD_SCHEMA = GameRewardSchema(
    game="zeroad",
    world_type="wargames.games.zeroad.world.ZeroADWorld",
    tick_rate=5,
    fields={
        "tick": RewardField("tick", "int", "track", "0 A.D. simulation turn."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Victory state."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Defeat state."),
        "mission.elapsed_ticks": RewardField(
            "mission.elapsed_ticks", "int", "minimize", "Elapsed simulation turns."
        ),
        "mission.elapsed_seconds": RewardField(
            "mission.elapsed_seconds", "float", "minimize", "Elapsed game seconds."
        ),
        "us.population": RewardField("us.population", "int", "maximize", "Player population."),
        "us.population_limit": RewardField(
            "us.population_limit", "int", "track", "Player population cap."
        ),
        "us.resources": RewardField(
            "us.resources", "dict[str, int] | None", "maximize", "Player resource stockpile."
        ),
        "us.enemy_units_killed": RewardField(
            "us.enemy_units_killed", "int", "maximize", "Enemy units killed by the player."
        ),
        "us.enemy_buildings_destroyed": RewardField(
            "us.enemy_buildings_destroyed",
            "int",
            "maximize",
            "Enemy buildings destroyed by the player.",
        ),
        "enemies": RewardField("enemies", "tuple[PlayerState, ...]", "track", "Active enemies."),
        "entities": RewardField(
            "entities", "tuple[EntityState, ...]", "track", "Visible full-state entity data."
        ),
        "map_size": RewardField("map_size", "int", "track", "Map size reported by 0 A.D."),
        "victory_conditions": RewardField(
            "victory_conditions", "tuple[str, ...]", "track", "Configured victory conditions."
        ),
    },
    primitives={
        "terminal": RewardPrimitiveSpec(
            "terminal",
            ("mission.finished", "mission.failed"),
            1.0,
            "terminal",
            "Success/failure outcome.",
        ),
        "delta_resources": RewardPrimitiveSpec(
            "delta_resources",
            ("us.resources",),
            1.0,
            "per_step",
            "Increase in player resource stockpile.",
        ),
        "delta_population": RewardPrimitiveSpec(
            "delta_population",
            ("us.population",),
            1.0,
            "per_step",
            "Increase in player population.",
        ),
        "enemy_damage": RewardPrimitiveSpec(
            "enemy_damage",
            ("entities",),
            1.0,
            "per_step",
            "Damage dealt to enemy-owned entities.",
        ),
    },
)
