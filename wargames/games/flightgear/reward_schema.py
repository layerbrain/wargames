from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

FLIGHTGEAR_REWARD_SCHEMA = GameRewardSchema(
    game="flightgear",
    world_type="wargames.games.flightgear.world.FlightGearWorld",
    tick_rate=30,
    fields={
        "tick": RewardField("tick", "int", "track", "WarGames step tick."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Mission success."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Mission failure."),
        "aircraft.id": RewardField("aircraft.id", "str", "track", "Aircraft identifier."),
        "aircraft.airport": RewardField("aircraft.airport", "str", "track", "Start airport."),
        "aircraft.runway": RewardField("aircraft.runway", "str | None", "track", "Start runway."),
        "aircraft.altitude_ft": RewardField(
            "aircraft.altitude_ft", "float | None", "maximize", "Altitude above mean sea level."
        ),
        "aircraft.airspeed_kt": RewardField(
            "aircraft.airspeed_kt", "float | None", "track", "Indicated airspeed."
        ),
        "aircraft.pitch_deg": RewardField(
            "aircraft.pitch_deg", "float | None", "track", "Pitch angle."
        ),
        "aircraft.roll_deg": RewardField(
            "aircraft.roll_deg", "float | None", "minimize", "Roll angle magnitude."
        ),
        "aircraft.heading_deg": RewardField(
            "aircraft.heading_deg", "float | None", "track", "Heading angle."
        ),
        "aircraft.vertical_speed_fps": RewardField(
            "aircraft.vertical_speed_fps", "float | None", "track", "Vertical speed."
        ),
        "aircraft.throttle": RewardField(
            "aircraft.throttle", "float | None", "track", "Engine throttle setting."
        ),
        "aircraft.crashed": RewardField(
            "aircraft.crashed", "bool | None", "minimize", "FlightGear crash flag."
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
    },
)
