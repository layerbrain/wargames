from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

IKEMEN_REWARD_SCHEMA = GameRewardSchema(
    game="ikemen",
    world_type="wargames.games.ikemen.world.IkemenWorld",
    tick_rate=60,
    fields={
        "tick": RewardField("tick", "int", "track", "WarGames step tick."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Match won."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Match lost."),
        "match.round_state": RewardField("match.round_state", "int", "track", "IKEMEN round state."),
        "match.round_no": RewardField("match.round_no", "int", "track", "Current round number."),
        "match.fight_time": RewardField("match.fight_time", "int", "track", "Elapsed fight time."),
        "match.match_over": RewardField("match.match_over", "bool", "track", "Match-over flag."),
        "match.winner_team": RewardField("match.winner_team", "int", "maximize", "Winning team number."),
        "p1.life": RewardField("p1.life", "int", "maximize", "Player 1 life."),
        "p1.power": RewardField("p1.power", "int", "maximize", "Player 1 power."),
        "p1.x": RewardField("p1.x", "float | None", "track", "Player 1 x position."),
        "p1.y": RewardField("p1.y", "float | None", "track", "Player 1 y position."),
        "p1.state_no": RewardField("p1.state_no", "int", "track", "Player 1 state number."),
        "p2.life": RewardField("p2.life", "int", "minimize", "Player 2 life."),
        "p2.power": RewardField("p2.power", "int", "track", "Player 2 power."),
        "p2.x": RewardField("p2.x", "float | None", "track", "Player 2 x position."),
        "p2.y": RewardField("p2.y", "float | None", "track", "Player 2 y position."),
        "players": RewardField("players", "tuple[PlayerState, ...]", "track", "Player summaries."),
    },
    primitives={
        "terminal": RewardPrimitiveSpec(
            "terminal",
            ("mission.finished", "mission.failed"),
            1.0,
            "terminal",
            "Win/loss outcome.",
        ),
        "damage_dealt": RewardPrimitiveSpec(
            "damage_dealt",
            ("p2.life",),
            1.0,
            "per_step",
            "Reward reducing opponent life.",
        ),
        "damage_taken": RewardPrimitiveSpec(
            "damage_taken",
            ("p1.life",),
            1.0,
            "per_step",
            "Penalty for losing life.",
        ),
        "power_gain": RewardPrimitiveSpec(
            "power_gain",
            ("p1.power",),
            1.0,
            "per_step",
            "Reward gaining meter.",
        ),
        "time_penalty": RewardPrimitiveSpec(
            "time_penalty",
            ("tick",),
            1.0,
            "per_step",
            "Small pressure to engage efficiently.",
        ),
    },
)
