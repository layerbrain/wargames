from __future__ import annotations

from wargames.evaluation.schema import GameRewardSchema, RewardField, RewardPrimitiveSpec

CRAFTIUM_REWARD_SCHEMA = GameRewardSchema(
    game="craftium",
    world_type="wargames.games.craftium.world.CraftiumWorld",
    tick_rate=30,
    fields={
        "tick": RewardField("tick", "int", "track", "WarGames step tick."),
        "mission.finished": RewardField("mission.finished", "bool", "maximize", "Task success."),
        "mission.failed": RewardField("mission.failed", "bool", "minimize", "Task failure."),
        "mission.truncated": RewardField("mission.truncated", "bool", "track", "Step limit reached."),
        "player.position": RewardField("player.position", "tuple[float, float, float] | None", "track", "Player position."),
        "player.velocity": RewardField("player.velocity", "tuple[float, float, float] | None", "track", "Player velocity."),
        "player.pitch": RewardField("player.pitch", "float | None", "track", "Player pitch."),
        "player.yaw": RewardField("player.yaw", "float | None", "track", "Player yaw."),
        "voxel.available": RewardField("voxel.available", "bool", "track", "Voxel observation availability."),
        "voxel.shape": RewardField("voxel.shape", "tuple[int, ...]", "track", "Voxel observation shape."),
        "voxel.nonzero_nodes": RewardField("voxel.nonzero_nodes", "int", "maximize", "Non-empty nearby voxel nodes."),
        "reward": RewardField("reward", "float", "maximize", "Native Craftium reward for the latest step."),
        "total_reward": RewardField("total_reward", "float", "maximize", "Accumulated native Craftium reward."),
        "mt_dtime": RewardField("mt_dtime", "float | None", "track", "Luanti simulation delta time."),
    },
    primitives={
        "terminal": RewardPrimitiveSpec(
            "terminal",
            ("mission.finished", "mission.failed"),
            1.0,
            "terminal",
            "Success/failure outcome.",
        ),
        "delta_reward": RewardPrimitiveSpec(
            "delta_reward",
            ("reward",),
            1.0,
            "per_step",
            "Reward native Craftium task progress.",
        ),
        "total_reward": RewardPrimitiveSpec(
            "total_reward",
            ("total_reward",),
            1.0,
            "per_step",
            "Reward accumulated native Craftium progress.",
        ),
        "movement_delta": RewardPrimitiveSpec(
            "movement_delta",
            ("player.position",),
            1.0,
            "per_step",
            "Reward movement through the environment.",
        ),
        "voxel_discovery": RewardPrimitiveSpec(
            "voxel_discovery",
            ("voxel.nonzero_nodes",),
            1.0,
            "per_step",
            "Reward observing additional nearby voxel structure.",
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
