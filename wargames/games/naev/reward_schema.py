from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

NAEV_REWARD_SCHEMA = GameRewardSchema(
    game="naev",
    world_type="wargames.games.naev.world.NaevWorld",
    tick_rate=4,
    fields={
        "tick": RewardField("tick", "int", "track", "WarGames state-export tick."),
        "mission.name": RewardField("mission.name", "str", "track", "Last completed mission."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Mission completed."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Mission failed."),
        "mission.completed_count": RewardField(
            "mission.completed_count", "int", "maximize", "Completed mission count."
        ),
        "mission.failed_count": RewardField(
            "mission.failed_count", "int", "minimize", "Failed mission count."
        ),
        "player.system": RewardField("player.system", "str", "track", "Current star system."),
        "player.landed": RewardField("player.landed", "bool", "track", "Landed state."),
        "player.x": RewardField("player.x", "float | None", "track", "Player x position."),
        "player.y": RewardField("player.y", "float | None", "track", "Player y position."),
        "player.vx": RewardField("player.vx", "float | None", "track", "Player x velocity."),
        "player.vy": RewardField("player.vy", "float | None", "track", "Player y velocity."),
        "player.speed": RewardField("player.speed", "float | None", "track", "Ship speed."),
        "player.credits": RewardField("player.credits", "float", "maximize", "Player credits."),
        "player.wealth": RewardField("player.wealth", "float", "maximize", "Player wealth."),
        "player.fuel": RewardField("player.fuel", "float | None", "maximize", "Ship fuel."),
        "player.armour": RewardField("player.armour", "float | None", "maximize", "Ship armour."),
        "player.shield": RewardField("player.shield", "float | None", "maximize", "Ship shield."),
        "player.disabled": RewardField(
            "player.disabled", "bool", "minimize", "Ship disabled state."
        ),
        "player.target": RewardField("player.target", "str", "track", "Current target."),
        "player.target_distance": RewardField(
            "player.target_distance", "float | None", "track", "Distance to current target."
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
        "delta_credits": RewardPrimitiveSpec(
            "delta_credits",
            ("player.credits",),
            1.0,
            "per_step",
            "Reward increases in credits.",
        ),
        "delta_wealth": RewardPrimitiveSpec(
            "delta_wealth",
            ("player.wealth",),
            1.0,
            "per_step",
            "Reward increases in total wealth.",
        ),
        "delta_mission_completed": RewardPrimitiveSpec(
            "delta_mission_completed",
            ("mission.completed_count",),
            1.0,
            "per_step",
            "Reward completed mission events.",
        ),
        "damage_penalty": RewardPrimitiveSpec(
            "damage_penalty",
            ("player.armour", "player.shield"),
            1.0,
            "per_step",
            "Penalize ship armour and shield loss.",
        ),
        "fuel_penalty": RewardPrimitiveSpec(
            "fuel_penalty",
            ("player.fuel",),
            1.0,
            "per_step",
            "Penalize fuel consumption.",
        ),
        "time_penalty": RewardPrimitiveSpec(
            "time_penalty",
            ("tick",),
            1.0,
            "per_step",
            "Small pressure to finish efficiently.",
        ),
    },
)
