# WarGames For Prime RL

This package publishes WarGames as a Prime Intellect Verifiers environment.
Prime starts an episode, receives the current game frame, calls the normal
computer-control tools, and receives the next frame plus the reward scored by
WarGames.

The same game catalog, mission IDs, reward profiles, and trusted scoring probes
used by the local runner are used here.

```bash
# from the WarGames repo root
uv pip install -e ./environments/prime
```

Run any shipped eval config:

```bash
prime eval run wargames \
  --config environments/prime/configs/doom/eval-map01.toml \
  -n 1 -r 1
```

## Supported Games

| Game | Missions | Eval config | RL config |
|---|---:|---|---|
| Red Alert | 297 | `configs/redalert/eval-soviet-01.toml` | `configs/redalert/rl-soviet-01.toml` |
| FlightGear | 14 | `configs/flightgear/eval-c172p-takeoff.toml` | `configs/flightgear/rl-c172p-takeoff.toml` |
| SuperTuxKart | 63 | `configs/supertuxkart/eval-lighthouse.toml` | `configs/supertuxkart/rl-lighthouse.toml` |
| 0 A.D. | 390 | `configs/zeroad/eval-arcadia.toml` | `configs/zeroad/rl-arcadia.toml` |
| Freeciv | 12 | `configs/freeciv/eval-earth-small.toml` | `configs/freeciv/rl-earth-small.toml` |
| Doom | 204 | `configs/doom/eval-map01.toml` | `configs/doom/rl-map01.toml` |
| SuperTux | 321 | `configs/supertux/eval-welcome-antarctica.toml` | `configs/supertux/rl-welcome-antarctica.toml` |
| Mindustry | 27 | `configs/mindustry/eval-veins.toml` | `configs/mindustry/rl-veins.toml` |
| Craftium | 96 | `configs/craftium/eval-chop-tree.toml` | `configs/craftium/rl-chop-tree.toml` |
| IKEMEN GO | 9 | `configs/ikemen/eval-kfm.toml` | `configs/ikemen/rl-kfm.toml` |
| Open Surge | 33 | `configs/opensurge/eval-sunshine-1.toml` | `configs/opensurge/rl-sunshine-1.toml` |
| Quaver | 70 | `configs/quaver/eval-crossover-beginner.toml` | `configs/quaver/rl-crossover-beginner.toml` |
| Naev | 128 | `configs/naev/eval-tutorial.toml` | `configs/naev/rl-tutorial.toml` |

The full game docs live under [`../../docs/games`](../../docs/games).

## Config Format

Prime configs select the WarGames task:

```toml
game = "redalert"
mission = "redalert.soviet-01.normal"
reward_profile = "protective"
recorder_mode = "none"
max_steps = 500
rollouts_per_example = 8
```

| Field | Meaning |
|---|---|
| `game` | WarGames game ID. |
| `mission` | Mission ID from `scenarios/<game>/missions/`. |
| `reward_profile` | Reward profile ID from `scenarios/<game>/profiles/`. |
| `recorder_mode` | `none`, `summary_only`, or `full`. Use `none` for high-throughput RL. |
| `max_steps` | Episode step budget. Budget stops are marked as truncated. |
| `rollouts_per_example` | Prime rollout count for training configs. |

Every game ships `standard`. Red Alert also ships `dense`, `protective`,
`terminal`, `speedrun`, and `aggressive_stress_test`.

Reward profile schema and per-game fields:
[`../../docs/reward_profiles.md`](../../docs/reward_profiles.md).

## Runtime Contract

For each turn:

1. Prime sends a model response.
2. WarGames reads the latest computer-control tool call.
3. WarGames applies it to the live game.
4. WarGames returns a JSON status block, the latest frame, and the updated
   reward.

The model sees rendered game output and the public tool/action history. Trusted
game state stays inside WarGames and is only used by the reward profile.

Supported tool calls are the normal WarGames computer controls:

```text
move_mouse
mouse_down
mouse_up
key_down
key_up
scroll
wait
```

## Publishing

The environment package depends on the current WarGames `main` branch:

```toml
wargames @ https://github.com/layerbrain/wargames/archive/refs/heads/main.zip
```

Publish after `main` contains the adapter changes:

```bash
make -C environments/prime publish
```

The publish target runs the WarGames harness/evaluation tests, Prime conformance
tests, and then pushes the public `layerbrain/wargames` environment.
