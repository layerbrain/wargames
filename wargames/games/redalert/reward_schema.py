from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

REDALERT_REWARD_SCHEMA = GameRewardSchema(
    game="redalert",
    world_type="wargames.games.redalert.world.RedAlertWorld",
    tick_rate=30,
    fields={
        "tick": RewardField("tick", "int", "track", "Precise game tick."),
        "us.cash": RewardField("us.cash", "int", "maximize", "Player resources."),
        "us.power_generated": RewardField(
            "us.power_generated", "int", "track", "Generated base power."
        ),
        "us.power_consumed": RewardField(
            "us.power_consumed", "int", "track", "Consumed base power."
        ),
        "us.tech_level": RewardField("us.tech_level", "int", "maximize", "Tech progression."),
        "us.units_killed": RewardField(
            "us.units_killed", "int", "maximize", "Enemy units destroyed."
        ),
        "us.buildings_lost": RewardField(
            "us.buildings_lost", "int", "minimize", "Friendly buildings lost."
        ),
        "enemy.cash": RewardField("enemy.cash", "int", "track", "Enemy resources."),
        "enemy.units_killed": RewardField(
            "enemy.units_killed", "int", "track", "Enemy kill counter."
        ),
        "enemy.buildings_lost": RewardField(
            "enemy.buildings_lost", "int", "track", "Enemy building losses."
        ),
        "mission.elapsed_ticks": RewardField(
            "mission.elapsed_ticks", "int", "track", "Mission elapsed game ticks."
        ),
        "mission.objectives": RewardField(
            "mission.objectives", "tuple[Objective, ...]", "maximize", "Objective completion state."
        ),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Mission success."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Mission failure."),
        "units": RewardField(
            "units", "tuple[Unit, ...]", "track", "Unit state: id/type/owner/x/y/health/visible."
        ),
        "buildings": RewardField(
            "buildings",
            "tuple[Building, ...]",
            "track",
            "Building state: id/type/owner/x/y/health/visible.",
        ),
        "resources": RewardField("resources", "tuple[Resource, ...]", "track", "Known resources."),
        "visible_tiles": RewardField(
            "visible_tiles", "tuple[tuple[int, int], ...]", "maximize", "Scouted map tiles."
        ),
    },
    primitives={
        "terminal": RewardPrimitiveSpec(
            "terminal", ("mission.finished", "mission.failed"), 1.0, "terminal", "Win/loss outcome."
        ),
        "objective.<id>": RewardPrimitiveSpec(
            "objective.<id>",
            ("mission.objectives",),
            1.0,
            "per_step",
            "Objective completion delta.",
        ),
        "delta_cash": RewardPrimitiveSpec(
            "delta_cash", ("us.cash",), 0.001, "per_step", "Cash delta."
        ),
        "delta_units_killed": RewardPrimitiveSpec(
            "delta_units_killed", ("us.units_killed",), 0.01, "per_step", "Enemy unit kills delta."
        ),
        "delta_buildings_lost": RewardPrimitiveSpec(
            "delta_buildings_lost",
            ("us.buildings_lost",),
            -0.02,
            "per_step",
            "Friendly building losses delta.",
        ),
        "scout_distance": RewardPrimitiveSpec(
            "scout_distance",
            ("visible_tiles", "units"),
            0.0001,
            "per_step",
            "Exploration progress.",
        ),
        "friendly_force_preservation": RewardPrimitiveSpec(
            "friendly_force_preservation",
            ("units", "buildings"),
            0.02,
            "per_step",
            "Penalty when friendly force health falls.",
        ),
        "collateral_damage_avoidance": RewardPrimitiveSpec(
            "collateral_damage_avoidance",
            ("buildings",),
            0.01,
            "per_step",
            "Penalty when neutral/civilian building health falls.",
        ),
    },
)
