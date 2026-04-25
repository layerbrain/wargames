# WarGames For Prime

Prime Intellect Verifiers surface for WarGames Red Alert. The public Prime
environment is `layerbrain/wargames`. The implementation lives in
`wargames.environments.prime`; this folder is only the publish wrapper.

```bash
uv pip install -e .
prime eval run wargames --config configs/eval-debug.toml -n 1 -r 1
```

Configs:

- `configs/eval-debug.toml`: quick local eval
- `configs/eval-test.toml`: held-out terminal-only eval
- `configs/rl-redalert-dense.toml`: dense train split for RL
- `configs/rl-redalert-curriculum.toml`: curriculum train split for RL

Reward profiles are the RL behavior dial. Set `reward_profile = "dense"` for
general warmup, `reward_profile = "protective"` to prioritize friendly-force
preservation and collateral avoidance, or point at a custom profile in
`scenarios/redalert/profiles/`.

```toml
split = "train"
reward_profile = "protective"
recorder_mode = "none"
max_steps = 500
rollouts_per_example = 8
```

The full YAML schema and Red Alert reward fields are in
[`../../docs/reward_profiles.md`](../../docs/reward_profiles.md).

Publish under the Layerbrain team:

```bash
make publish
```

The publish target runs:

```bash
prime env push --name wargames --team layerbrain --visibility PUBLIC
```
