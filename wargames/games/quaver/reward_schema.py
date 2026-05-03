from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

QUAVER_REWARD_SCHEMA = GameRewardSchema(
    game="quaver",
    world_type="wargames.games.quaver.world.QuaverWorld",
    tick_rate=60,
    fields={
        "tick": RewardField("tick", "int", "track", "WarGames step tick."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Chart completed."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Failed chart or runtime failure."),
        "chart.map_id": RewardField("chart.map_id", "int", "track", "Quaver map id."),
        "chart.title": RewardField("chart.title", "str", "track", "Song title."),
        "chart.artist": RewardField("chart.artist", "str", "track", "Song artist."),
        "chart.difficulty_name": RewardField("chart.difficulty_name", "str", "track", "Chart difficulty."),
        "chart.mode": RewardField("chart.mode", "str", "track", "Quaver game mode."),
        "chart.key_count": RewardField("chart.key_count", "int", "track", "Number of lanes."),
        "chart.total_judgements": RewardField("chart.total_judgements", "int", "track", "Scored note events."),
        "gameplay.song_time_ms": RewardField("gameplay.song_time_ms", "float", "maximize", "Current chart time."),
        "gameplay.health": RewardField("gameplay.health", "float", "maximize", "Current health."),
        "gameplay.score": RewardField("gameplay.score", "int", "maximize", "Current score."),
        "gameplay.accuracy": RewardField("gameplay.accuracy", "float", "maximize", "Current accuracy."),
        "gameplay.combo": RewardField("gameplay.combo", "int", "maximize", "Current combo."),
        "gameplay.max_combo": RewardField("gameplay.max_combo", "int", "maximize", "Best combo this run."),
        "gameplay.total_judgement_count": RewardField(
            "gameplay.total_judgement_count", "int", "maximize", "Judgements received so far."
        ),
        "judgements.marv": RewardField("judgements.marv", "int", "maximize", "Marvelous hits."),
        "judgements.perf": RewardField("judgements.perf", "int", "maximize", "Perfect hits."),
        "judgements.great": RewardField("judgements.great", "int", "maximize", "Great hits."),
        "judgements.good": RewardField("judgements.good", "int", "maximize", "Good hits."),
        "judgements.okay": RewardField("judgements.okay", "int", "track", "Okay hits."),
        "judgements.miss": RewardField("judgements.miss", "int", "minimize", "Missed notes."),
    },
    primitives={
        "terminal": RewardPrimitiveSpec(
            "terminal",
            ("mission.finished", "mission.failed"),
            1.0,
            "terminal",
            "Success/failure outcome.",
        ),
        "delta_score": RewardPrimitiveSpec(
            "delta_score",
            ("gameplay.score",),
            1.0,
            "per_step",
            "Reward score increases.",
        ),
        "delta_hits": RewardPrimitiveSpec(
            "delta_hits",
            ("judgements.marv", "judgements.perf", "judgements.great", "judgements.good"),
            1.0,
            "per_step",
            "Reward newly hit notes.",
        ),
        "delta_combo": RewardPrimitiveSpec(
            "delta_combo",
            ("gameplay.combo",),
            1.0,
            "per_step",
            "Reward combo growth.",
        ),
        "delta_accuracy": RewardPrimitiveSpec(
            "delta_accuracy",
            ("gameplay.accuracy",),
            1.0,
            "per_step",
            "Reward accuracy improvements.",
        ),
        "miss_penalty": RewardPrimitiveSpec(
            "miss_penalty",
            ("judgements.miss",),
            1.0,
            "per_step",
            "Penalty for new misses.",
        ),
        "health_loss_penalty": RewardPrimitiveSpec(
            "health_loss_penalty",
            ("gameplay.health",),
            1.0,
            "per_step",
            "Penalty for losing health.",
        ),
        "time_penalty": RewardPrimitiveSpec(
            "time_penalty",
            ("tick",),
            1.0,
            "per_step",
            "Small pressure to keep playing efficiently.",
        ),
    },
)
