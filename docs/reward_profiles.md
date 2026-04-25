# Reward Profiles

Reward profiles are the training and evaluation contract. A profile says which
hidden-state measurements become reward, when they are emitted, and how strongly
they count. Agents still see only pixels and CUA tools; the profile runs inside
the trusted environment after each action.

Profiles live in `scenarios/<game>/profiles/*.yaml`. Tasks reference them by
ID through `reward_profile`. Prime RL, Prime eval, OpenReward, and the local
runner all use the same profile loader and evaluator.

## Full Profile Example

This is a complete Red Alert profile with every supported profile field shown.
It trains defensive play: finish the mission, preserve friendly units and
buildings, avoid collateral damage, still reward enemy kills, and cap per-step
reward so one lucky event does not dominate training.

```yaml
id: defensive_rl
game: redalert
description: "RL profile for defensive Red Alert play: win while preserving friendly force."

# Per-step reward clamps. These apply only to entries with when: per_step.
# Use caps for RL so a single step cannot create an unstable gradient.
step_reward_min: -0.50
step_reward_max: 0.10

# Multipliers applied after individual entry weights.
# terminal_reward_weight affects when: terminal entries.
# dense_reward_weight affects when: per_step entries.
terminal_reward_weight: 1.0
dense_reward_weight: 1.0

# true means the profile is allowed on train/curriculum only.
# The catalog rejects train_only profiles on test.
train_only: true

entries:
  - id: terminal
    fn: wargames.core.missions.rewards.terminal
    args:
      defeat_weight: -1.0
    weight: 1.0
    when: terminal

  - id: friendly_force_preservation
    fn: wargames.games.redalert.rewards.friendly_force_preservation
    weight: 0.02
    when: per_step

  - id: collateral_damage_avoidance
    fn: wargames.games.redalert.rewards.collateral_damage_avoidance
    weight: 0.01
    when: per_step

  - id: delta_units_killed
    fn: wargames.games.redalert.rewards.delta_units_killed
    weight: 0.005
    when: per_step

  - id: scout_distance
    fn: wargames.games.redalert.rewards.scout_distance
    weight: 0.0001
    when: per_step
```

## Profile Fields

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `id` | string | yes | Profile ID used by tasks, CLI, Prime configs, and OpenReward variants. Unique per game. |
| `game` | string | yes | Game namespace. Red Alert uses `redalert`. |
| `description` | string | no | Human description shown in docs and profile listings. |
| `step_reward_min` | float/null | no | Lower clamp for the total reward from `per_step` entries on one step. |
| `step_reward_max` | float/null | no | Upper clamp for the total reward from `per_step` entries on one step. |
| `terminal_reward_weight` | float | no | Multiplier applied to all terminal entries after entry weights. Defaults to `1.0`. |
| `dense_reward_weight` | float | no | Multiplier applied to all per-step entries after entry weights. Defaults to `1.0`. |
| `train_only` | bool | no | If `true`, blocked from `test` split. Use for shaping-heavy RL profiles. |
| `entries` | list | yes | Reward entries. Each entry becomes a `RubricEntry`. |

## Entry Fields

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `id` | string | yes | Entry name inside the profile. Must be unique. Appears in reward breakdowns. |
| `fn` | dotted path | yes | Python function or factory. It must return a `RubricEntry` or a callable scorer. |
| `args` | mapping | no | Keyword args passed to `fn`. Use this for objective IDs or custom primitive settings. |
| `weight` | float | no | Entry multiplier. Defaults to `1.0`. |
| `when` | `per_step`/`terminal` | yes | `per_step` runs after each tool call. `terminal` runs once in `finish()`. |

## Red Alert Reward Fields

These are the hidden-state fields available to Red Alert reward code. They are
never shown to the model.

| Field | Direction | Meaning |
|---|---|---|
| `tick` | track | Precise game tick. |
| `us.cash` | maximize | Player resources. |
| `us.power_generated` | track | Generated base power. |
| `us.power_consumed` | track | Consumed base power. |
| `us.tech_level` | maximize | Tech progression. |
| `us.units_killed` | maximize | Enemy units destroyed by the player. |
| `us.buildings_lost` | minimize | Friendly buildings lost. |
| `enemy.cash` | track | Enemy resources. |
| `enemy.units_killed` | track | Enemy kill counter. |
| `enemy.buildings_lost` | track | Enemy building losses. |
| `mission.elapsed_ticks` | track | Mission elapsed game ticks. |
| `mission.objectives` | maximize | Objective completion state. |
| `mission.finished` | maximize | Mission success. |
| `mission.failed` | minimize | Mission failure. |
| `units` | track | Unit id/type/owner/x/y/health/visible. |
| `buildings` | track | Building id/type/owner/x/y/health/visible. |
| `resources` | track | Known resources. |
| `visible_tiles` | maximize | Scouted map tiles. |

## Built-In Red Alert Primitives

| Primitive | Default weight | Timing | Uses | Behavior |
|---|---:|---|---|---|
| `terminal` | `1.0` | terminal | `mission.finished`, `mission.failed` | `+1` on success, negative on failure. |
| `objective.<id>` | `1.0` | per-step | `mission.objectives` | Positive when a named objective flips to complete. |
| `delta_cash` | `0.001` | per-step | `us.cash` | Rewards resource increase. |
| `delta_units_killed` | `0.01` | per-step | `us.units_killed` | Rewards newly destroyed enemy units. |
| `delta_buildings_lost` | `-0.02` | per-step | `us.buildings_lost` | Penalizes friendly building losses. |
| `scout_distance` | `0.0001` | per-step | `visible_tiles`, `units` | Rewards new scouting information. |
| `friendly_force_preservation` | `0.02` | per-step | `units`, `buildings` | Penalizes loss of friendly health. |
| `collateral_damage_avoidance` | `0.01` | per-step | `buildings` | Penalizes neutral/civilian building damage. |

## Train, Eval, And RL

Use dense shaping for training and sparse or mild profiles for reporting.

```toml
# environments/prime/configs/rl-redalert-dense.toml
split = "train"
reward_profile = "dense"
recorder_mode = "none"
max_steps = 500
rollouts_per_example = 8
```

For defensive RL, point a Prime config at `protective` or a custom profile:

```toml
split = "train"
reward_profile = "protective"
recorder_mode = "none"
max_steps = 500
rollouts_per_example = 8
```

For held-out reporting, use `test` with an eval-grade profile:

```toml
split = "test"
reward_profile = "terminal"
recorder_mode = "summary_only"
```

The same profile IDs are exposed as OpenReward variants where registered:

```bash
firehorse --env layerbrain/wargames --variant protective --split train ...
firehorse --env layerbrain/wargames --variant standard --split test ...
```

## Validate Before Training

```bash
wargames profile validate scenarios/redalert/profiles/protective.yaml
python -m unittest tests.evaluation.test_profiles -v
```

Validation catches duplicate entry IDs, bad `when` values, invalid dotted
paths, invalid factory args, and invalid reward caps before a long rollout.

