from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

SUPERTUXKART_REWARD_SCHEMA = GameRewardSchema(
    game="supertuxkart",
    world_type="wargames.games.supertuxkart.world.SuperTuxKartWorld",
    tick_rate=30,
    fields={
        "tick": RewardField("tick", "int", "track", "WarGames step tick."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Race completed."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Race process failed."),
        "race.track": RewardField("race.track", "str", "track", "Track identifier."),
        "race.laps": RewardField("race.laps", "int", "track", "Configured lap count."),
        "race.num_karts": RewardField("race.num_karts", "int", "track", "Number of karts."),
        "race.elapsed_ticks": RewardField(
            "race.elapsed_ticks", "int", "minimize", "Elapsed run ticks."
        ),
        "race.elapsed_seconds": RewardField(
            "race.elapsed_seconds", "float", "minimize", "Elapsed race time."
        ),
        "race.phase": RewardField("race.phase", "str", "track", "Race phase."),
        "player.id": RewardField("player.id", "int", "track", "Player kart world id."),
        "player.kart": RewardField("player.kart", "str", "track", "Player kart identifier."),
        "player.rank": RewardField("player.rank", "int | None", "minimize", "Race rank."),
        "player.lap": RewardField("player.lap", "int | None", "maximize", "Current lap."),
        "player.distance": RewardField(
            "player.distance", "float | None", "maximize", "Total distance around the course."
        ),
        "player.distance_down_track": RewardField(
            "player.distance_down_track",
            "float | None",
            "track",
            "Distance from the current lap start.",
        ),
        "player.progress": RewardField(
            "player.progress", "float | None", "maximize", "Race progress from 0 to 1."
        ),
        "player.x": RewardField("player.x", "float | None", "track", "World x position."),
        "player.y": RewardField("player.y", "float | None", "track", "World y position."),
        "player.z": RewardField("player.z", "float | None", "track", "World z position."),
        "player.velocity_x": RewardField(
            "player.velocity_x", "float | None", "track", "World x velocity."
        ),
        "player.velocity_y": RewardField(
            "player.velocity_y", "float | None", "track", "World y velocity."
        ),
        "player.velocity_z": RewardField(
            "player.velocity_z", "float | None", "track", "World z velocity."
        ),
        "player.speed": RewardField(
            "player.speed", "float | None", "maximize", "Kart speed in meters per second."
        ),
        "player.heading": RewardField(
            "player.heading", "float | None", "track", "Kart heading."
        ),
        "player.pitch": RewardField("player.pitch", "float | None", "track", "Kart pitch."),
        "player.roll": RewardField("player.roll", "float | None", "track", "Kart roll."),
        "player.steering": RewardField(
            "player.steering", "float | None", "track", "Current steering input."
        ),
        "player.throttle": RewardField(
            "player.throttle", "float | None", "track", "Current throttle input."
        ),
        "player.braking": RewardField(
            "player.braking", "bool | None", "track", "Brake input state."
        ),
        "player.nitro": RewardField("player.nitro", "bool | None", "track", "Nitro input state."),
        "player.energy": RewardField(
            "player.energy", "float | None", "maximize", "Stored nitro energy."
        ),
        "player.powerup": RewardField(
            "player.powerup", "str | None", "track", "Held powerup type."
        ),
        "player.powerup_count": RewardField(
            "player.powerup_count", "int | None", "track", "Held powerup count."
        ),
        "player.on_ground": RewardField(
            "player.on_ground", "bool | None", "track", "Wheel contact state."
        ),
        "player.on_road": RewardField(
            "player.on_road", "bool | None", "maximize", "Road contact state."
        ),
        "player.finished": RewardField(
            "player.finished", "bool", "maximize", "Player finished the race."
        ),
        "player.eliminated": RewardField(
            "player.eliminated", "bool", "minimize", "Player eliminated state."
        ),
        "player.rescue": RewardField(
            "player.rescue", "bool | None", "track", "Rescue input state."
        ),
        "karts": RewardField(
            "karts",
            "tuple[KartState, ...]",
            "track",
            "All kart states with rank, lap, position, velocity, controls, and status.",
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
        "delta_progress": RewardPrimitiveSpec(
            "delta_progress",
            ("player.progress", "player.distance"),
            1.0,
            "per_step",
            "Increase in player race progress.",
        ),
        "speed": RewardPrimitiveSpec(
            "speed",
            ("player.speed",),
            1.0,
            "per_step",
            "Player kart speed.",
        ),
        "rank_gain": RewardPrimitiveSpec(
            "rank_gain",
            ("player.rank",),
            1.0,
            "per_step",
            "Reward passing other karts.",
        ),
        "off_road_penalty": RewardPrimitiveSpec(
            "off_road_penalty",
            ("player.on_road",),
            1.0,
            "per_step",
            "Penalty when the player is off road.",
        ),
    },
)
