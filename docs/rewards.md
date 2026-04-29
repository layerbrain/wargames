# Rewards

WarGames keeps reward computation outside the runtime. `Rubric` and
`RubricEntry` remain available as evaluator utilities: each entry receives the
previous and current game snapshots and returns a scalar reward.

See [`docs/reward_profiles.md`](reward_profiles.md) for the full YAML schema,
per-game reward fields, built-in primitives, and Prime RL training examples.
