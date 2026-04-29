# WarGames For Prime RL

Use this package when you want Prime RL or Prime eval to run WarGames episodes.
Prime receives screen frames from WarGames and returns the same primitive
actions as any other agent: `move_mouse`, `mouse_down`, `mouse_up`, `key_down`,
`key_up`, `scroll`, and `wait`.

```bash
# from the WarGames repo root
uv pip install -e ./environments/prime
```

Run any shipped eval config:

```bash
prime eval run wargames \
  --config environments/prime/configs/freeciv/eval-earth-small.toml \
  -n 1 -r 1
```

## Configs

| Game | Eval config | RL config |
|---|---|---|
| Red Alert | `environments/prime/configs/redalert/eval-soviet-01.toml` | `environments/prime/configs/redalert/rl-soviet-01.toml` |
| FlightGear | `environments/prime/configs/flightgear/eval-c172p-takeoff.toml` | `environments/prime/configs/flightgear/rl-c172p-takeoff.toml` |
| SuperTuxKart | `environments/prime/configs/supertuxkart/eval-lighthouse.toml` | `environments/prime/configs/supertuxkart/rl-lighthouse.toml` |
| 0 A.D. | `environments/prime/configs/zeroad/eval-arcadia.toml` | `environments/prime/configs/zeroad/rl-arcadia.toml` |
| Freeciv | `environments/prime/configs/freeciv/eval-earth-small.toml` | `environments/prime/configs/freeciv/rl-earth-small.toml` |

Reward profiles are the behavior dial. Every game ships a `standard` profile;
Red Alert also ships `dense`, `protective`, `terminal`, `speedrun`, and
`aggressive_stress_test`. You can point `reward_profile` at any profile in
`scenarios/<game>/profiles/`.

```toml
game = "redalert"
mission = "redalert.soviet-01.normal"
reward_profile = "protective"
recorder_mode = "none"
max_steps = 500
rollouts_per_example = 8
```

The full YAML schema is in [`../../docs/reward_profiles.md`](../../docs/reward_profiles.md).
