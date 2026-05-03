# Reward Profiles

Reward profiles are the training and evaluation contract. A reward profile says which
trusted game-state measurements become reward, when they are emitted, and how
strongly they count. Reward profiles run inside the trusted environment after each
action.

Reward profiles live in `scenarios/<game>/profiles/*.yaml`. Missions reference them by
ID through `reward_profile`. Prime RL, Prime eval, and the local runner all use
the same profile loader and evaluator.

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
| `id` | string | yes | Reward profile ID used by missions, CLI, and Prime configs. Unique per game. |
| `game` | string | yes | Game namespace. Red Alert uses `redalert`. |
| `description` | string | no | Human description shown in docs and reward profile listings. |
| `step_reward_min` | float/null | no | Lower clamp for the total reward from `per_step` entries on one step. |
| `step_reward_max` | float/null | no | Upper clamp for the total reward from `per_step` entries on one step. |
| `terminal_reward_weight` | float | no | Multiplier applied to all terminal entries after entry weights. Defaults to `1.0`. |
| `dense_reward_weight` | float | no | Multiplier applied to all per-step entries after entry weights. Defaults to `1.0`. |
| `entries` | list | yes | Reward entries. Each entry becomes a `RubricEntry`. |

## Entry Fields

| Field | Type | Required | Meaning |
|---|---:|---:|---|
| `id` | string | yes | Entry name inside the profile. Must be unique. Appears in reward breakdowns. |
| `fn` | dotted path | yes | Python function that returns a `RubricEntry` or callable scorer. |
| `args` | mapping | no | Keyword args passed to `fn`. Use this for objective IDs or custom primitive settings. |
| `weight` | float | no | Entry multiplier. Defaults to `1.0`. |
| `when` | `per_step`/`terminal` | yes | `per_step` runs after each input event. `terminal` runs once in `finish()`. |

## Red Alert Reward Fields

These are the trusted game-state fields available to Red Alert reward code.
They are used by evaluation and are separate from the observation payload.

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

## FlightGear Reward Fields

FlightGear profiles use the same profile format, but the state source is
aircraft telemetry.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Mission success. |
| `mission.failed` | minimize | Mission failure. |
| `aircraft.altitude_ft` | maximize | Altitude above mean sea level. |
| `aircraft.airspeed_kt` | track | Indicated airspeed. |
| `aircraft.pitch_deg` | track | Pitch angle. |
| `aircraft.roll_deg` | minimize | Roll angle magnitude. |
| `aircraft.heading_deg` | track | Heading angle. |
| `aircraft.vertical_speed_fps` | track | Vertical speed. |
| `aircraft.throttle` | track | Engine throttle setting. |
| `aircraft.crashed` | minimize | FlightGear crash flag. |

The shipped FlightGear profile starts sparse with `terminal`. Add shaping
entries only after declaring the primitive in
`wargames/games/flightgear/reward_schema.py`.

## SuperTuxKart Reward Fields

SuperTuxKart profiles use the same profile format. The shipped adapter exposes
race setup and process lifecycle state.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Race completed. |
| `mission.failed` | minimize | Race process failed. |
| `race.track` | track | Track identifier. |
| `race.laps` | track | Configured lap count. |
| `race.num_karts` | track | Number of karts in the race. |
| `race.elapsed_ticks` | minimize | Elapsed WarGames ticks. |

The shipped SuperTuxKart profile starts sparse with `terminal`. Add shaping
entries only after declaring the primitive in
`wargames/games/supertuxkart/reward_schema.py`.

## 0 A.D. Reward Fields

0 A.D. profiles use the same profile format. The shipped adapter exposes
player economy, population, enemy players, full entity state, and terminal
victory/defeat.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Victory state. |
| `mission.failed` | minimize | Defeat state. |
| `mission.elapsed_seconds` | minimize | Elapsed game seconds. |
| `us.population` | maximize | Player population. |
| `us.population_limit` | track | Player population cap. |
| `us.resources` | maximize | Player resource stockpile. |
| `us.enemy_units_killed` | maximize | Enemy units killed by the player. |
| `entities` | track | Full-state entity data from 0 A.D. |
| `enemies` | track | Active enemy player state. |

The shipped 0 A.D. profile includes `delta_resources`, `delta_population`,
`enemy_damage`, and `terminal`. Add shaping entries only after declaring the
primitive in `wargames/games/zeroad/reward_schema.py`.

## Freeciv Reward Fields

Freeciv profiles use the same profile format. The shipped adapter exposes
authoritative server save state after each action.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Victory state. |
| `mission.failed` | minimize | Defeat state. |
| `game.turn` | track | Freeciv turn number. |
| `game.year` | track | Calendar year. |
| `us.gold` | maximize | Player treasury. |
| `us.city_count` | maximize | Player cities. |
| `us.unit_count` | maximize | Player units. |
| `us.known_tiles` | maximize | Known map tiles from exploration. |
| `us.science_rate` | track | Science tax allocation percentage. |
| `enemies` | track | Alive opponent player state. |

The shipped Freeciv profile includes `delta_city_count`, `delta_unit_count`,
`delta_gold`, `delta_known_tiles`, and `terminal`. Add shaping entries only
after declaring the primitive in `wargames/games/freeciv/reward_schema.py`.

## Doom Reward Fields

Doom profiles use the same profile format. The shipped adapter exposes map
progress, player pose, inventory, combat totals, and terminal map outcome.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Map exit reached. |
| `mission.failed` | minimize | Player died or process failed. |
| `level.map` | track | Map identifier. |
| `level.elapsed_ticks` | minimize | Elapsed map ticks. |
| `level.kills` | maximize | Monsters killed by the player. |
| `level.items` | maximize | Items collected by the player. |
| `level.secrets` | maximize | Secrets found by the player. |
| `player.x` | track | Player x position. |
| `player.y` | track | Player y position. |
| `player.angle` | track | Player view angle. |
| `player.health` | maximize | Player health. |
| `player.armor` | maximize | Player armor. |
| `player.ammo` | track | Ammo by type. |
| `player.weapons` | track | Owned weapons. |
| `player.keys` | track | Owned keys. |
| `player.damage_taken` | minimize | Damage received this level. |
| `player.dead` | minimize | Player death state. |

The shipped Doom profile includes `delta_kills`, `delta_items`,
`delta_secrets`, `health_preservation`, `damage_penalty`, `time_penalty`, and
`terminal`. Add shaping entries only after declaring the primitive in
`wargames/games/doom/reward_schema.py`.

## SuperTux Reward Fields

SuperTux profiles use the same profile format. The shipped adapter exposes
level progress, player movement, coin/secrets collection, power-up state, and
terminal level outcome.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Level exit reached. |
| `mission.failed` | minimize | Player death or process failure. |
| `level.file` | track | Level file path. |
| `level.name` | track | Level display name. |
| `level.elapsed_ticks` | minimize | Elapsed level ticks. |
| `level.coins` | maximize | Collected coins. |
| `level.total_coins` | track | Available coins. |
| `level.secrets` | maximize | Found secrets. |
| `level.total_secrets` | track | Available secrets. |
| `player.x` | maximize | Horizontal level progress. |
| `player.y` | track | Vertical position. |
| `player.vx` | maximize | Horizontal velocity. |
| `player.vy` | track | Vertical velocity. |
| `player.coins` | maximize | Player wallet coins. |
| `player.bonus` | track | Current power-up. |
| `player.alive` | maximize | Player is alive. |
| `player.dead` | minimize | Player is dead. |
| `player.winning` | maximize | Player is in the win sequence. |

The shipped SuperTux profile includes `delta_coins`, `delta_secrets`,
`progress_x`, `velocity_x`, `death_penalty`, `time_penalty`, and `terminal`.
Add shaping entries only after declaring the primitive in
`wargames/games/supertux/reward_schema.py`.

## Mindustry Reward Fields

Mindustry profiles use the same profile format. The shipped adapter exposes
hidden game state from the rendered client: survival wave, enemy pressure, team
core state, items, buildings, units, and terminal victory/defeat.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Win wave reached or game won. |
| `mission.failed` | minimize | Core destroyed or game lost. |
| `game.map` | track | Map name. |
| `game.wave` | maximize | Survival wave. |
| `game.enemies` | minimize | Live enemy count. |
| `game.won` | maximize | Mindustry win flag. |
| `game.game_over` | track | Mindustry game-over flag. |
| `us.cores` | maximize | Player core count. |
| `us.units` | maximize | Player unit count. |
| `us.buildings` | maximize | Player building count. |
| `us.items` | maximize | Items stored in team cores. |
| `us.core_health` | maximize | Total core health. |
| `teams` | track | Active team summaries. |

The shipped Mindustry profile includes `delta_wave`, `delta_items`,
`delta_buildings`, `core_health`, `enemy_pressure`, `time_penalty`, and
`terminal`. Add shaping entries only after declaring the primitive in
`wargames/games/mindustry/reward_schema.py`.

## Craftium Reward Fields

Craftium profiles use the same profile format. The shipped adapter exposes
native Craftium task reward, player movement, view angles, voxel observation
summaries, and terminal task outcome.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Task success. |
| `mission.failed` | minimize | Task failure. |
| `mission.truncated` | track | Step limit reached. |
| `player.position` | track | Player position. |
| `player.velocity` | track | Player velocity. |
| `player.pitch` | track | Player pitch. |
| `player.yaw` | track | Player yaw. |
| `voxel.available` | track | Voxel observation availability. |
| `voxel.shape` | track | Voxel observation shape. |
| `voxel.nonzero_nodes` | maximize | Non-empty nearby voxel nodes. |
| `reward` | maximize | Native Craftium reward for the latest step. |
| `total_reward` | maximize | Accumulated native Craftium reward. |
| `mt_dtime` | track | Luanti simulation delta time. |

The shipped Craftium profile includes `delta_reward`, `movement_delta`,
`voxel_discovery`, `time_penalty`, and `terminal`. Add shaping entries only
after declaring the primitive in `wargames/games/craftium/reward_schema.py`.

## IKEMEN GO Reward Fields

IKEMEN GO profiles use the same profile format. The shipped adapter exposes
match phase, winner, player life and power, movement, state number, control
state, and terminal match outcome.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Match won. |
| `mission.failed` | minimize | Match lost. |
| `match.round_state` | track | IKEMEN round state. |
| `match.round_no` | track | Current round number. |
| `match.fight_time` | track | Elapsed fight time. |
| `match.match_over` | track | Match-over flag. |
| `match.winner_team` | maximize | Winning team number. |
| `p1.life` | maximize | Player 1 life. |
| `p1.power` | maximize | Player 1 power. |
| `p1.x` | track | Player 1 x position. |
| `p1.y` | track | Player 1 y position. |
| `p1.state_no` | track | Player 1 state number. |
| `p2.life` | minimize | Player 2 life. |
| `p2.power` | track | Player 2 power. |
| `p2.x` | track | Player 2 x position. |
| `p2.y` | track | Player 2 y position. |
| `players` | track | Player summaries. |

The shipped IKEMEN GO profile includes `damage_dealt`, `damage_taken`,
`power_gain`, `time_penalty`, and `terminal`. Add shaping entries only after
declaring the primitive in `wargames/games/ikemen/reward_schema.py`.

## Open Surge Fields

Open Surge rewards are computed from engine state exported each level tick.

| Field | Direction | Meaning |
|---|---|---|
| `mission.finished` | maximize | Act cleared. |
| `mission.failed` | minimize | Player death or runtime failure. |
| `level.elapsed_ticks` | minimize | Elapsed level ticks. |
| `level.width` | track | Level width. |
| `player.x` | track | Player x position. |
| `player.speed` | maximize | Player speed. |
| `player.gsp` | track | Ground speed. |
| `player.rings` | maximize | Current ring count. |
| `player.score` | maximize | Current score. |
| `player.lives` | maximize | Remaining lives. |
| `player.dying` | minimize | Death state. |

The shipped Open Surge profile includes `delta_rings`, `delta_score`,
`progress_x`, `speed`, `death_penalty`, `time_penalty`, and `terminal`. Add
shaping entries only after declaring the primitive in
`wargames/games/opensurge/reward_schema.py`.

## Eval And RL

Use dense shaping for training and sparse or mild profiles for reporting.

```toml
# environments/prime/configs/redalert/rl-soviet-01.toml
mission = "redalert.soviet-01.normal"
reward_profile = "dense"
recorder_mode = "none"
max_steps = 500
rollouts_per_example = 8
```

For defensive RL, point a Prime config at `protective` or a custom profile:

```toml
mission = "redalert.soviet-01.normal"
reward_profile = "protective"
recorder_mode = "none"
max_steps = 500
rollouts_per_example = 8
```

For reporting, use an eval-grade profile:

```toml
mission = "redalert.soviet-01.normal"
reward_profile = "terminal"
recorder_mode = "summary_only"
```

## Validate Before Training

```bash
wargames reward-profile validate scenarios/redalert/profiles/protective.yaml
wargames reward-profile validate scenarios/flightgear/profiles/standard.yaml --game flightgear
wargames reward-profile validate scenarios/supertuxkart/profiles/standard.yaml --game supertuxkart
wargames reward-profile validate scenarios/zeroad/profiles/standard.yaml --game zeroad
wargames reward-profile validate scenarios/freeciv/profiles/standard.yaml --game freeciv
wargames reward-profile validate scenarios/doom/profiles/standard.yaml --game doom
wargames reward-profile validate scenarios/supertux/profiles/standard.yaml --game supertux
wargames reward-profile validate scenarios/mindustry/profiles/standard.yaml --game mindustry
wargames reward-profile validate scenarios/craftium/profiles/standard.yaml --game craftium
wargames reward-profile validate scenarios/ikemen/profiles/standard.yaml --game ikemen
wargames reward-profile validate scenarios/opensurge/profiles/standard.yaml --game opensurge
python -m unittest tests.evaluation.test_profiles -v
```

Validation catches duplicate entry IDs, bad `when` values, invalid dotted
paths, invalid reward arguments, and invalid reward caps before a long rollout.
