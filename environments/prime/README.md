# WarGames For Prime RL

Use this package when you want Prime RL or Prime eval to run WarGames episodes.
Prime receives screen frames from WarGames and returns the same primitive
actions as any other agent: `move_mouse`, `mouse_down`, `mouse_up`, `key_down`,
`key_up`, `scroll`, and `wait`.

```bash
# from the WarGames repo root
uv pip install -e ./environments/prime

prime eval run wargames \
  --config environments/prime/configs/redalert/eval-soviet-01.toml \
  -n 1 -r 1
```

Configs:

- `environments/prime/configs/redalert/eval-soviet-01.toml`: Red Alert eval run
- `environments/prime/configs/redalert/rl-soviet-01.toml`: Red Alert RL run
- `environments/prime/configs/flightgear/eval-c172p-takeoff.toml`: FlightGear eval run
- `environments/prime/configs/flightgear/rl-c172p-takeoff.toml`: FlightGear RL run
- `environments/prime/configs/supertuxkart/eval-lighthouse.toml`: SuperTuxKart eval run
- `environments/prime/configs/supertuxkart/rl-lighthouse.toml`: SuperTuxKart RL run
- `environments/prime/configs/zeroad/eval-arcadia.toml`: 0 A.D. eval run
- `environments/prime/configs/zeroad/rl-arcadia.toml`: 0 A.D. RL run
- `environments/prime/configs/freeciv/eval-earth-small.toml`: Freeciv eval run
- `environments/prime/configs/freeciv/rl-earth-small.toml`: Freeciv RL run

Reward profiles are the behavior dial. Set `reward_profile = "dense"` for
general Red Alert warmup, `reward_profile = "protective"` to prioritize
friendly-force preservation and collateral avoidance, or point at a custom
profile in `scenarios/<game>/profiles/`.

```toml
game = "redalert"
mission = "redalert.soviet-01.normal"
reward_profile = "protective"
recorder_mode = "none"
max_steps = 500
rollouts_per_example = 8
```

The full YAML schema is in [`../../docs/reward_profiles.md`](../../docs/reward_profiles.md).
