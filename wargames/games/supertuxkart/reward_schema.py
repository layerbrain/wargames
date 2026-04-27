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
