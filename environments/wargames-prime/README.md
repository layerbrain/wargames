# WarGames Prime

Prime Intellect Verifiers surface for WarGames Red Alert.

```bash
uv pip install -e .
prime eval run wargames-prime --config configs/eval-debug.toml -n 1 -r 1
```

Configs:

- `configs/eval-debug.toml`: quick local eval
- `configs/eval-test.toml`: held-out terminal-only eval
- `configs/rl-redalert-dense.toml`: dense train split for RL
- `configs/rl-redalert-curriculum.toml`: curriculum train split for RL

Publish under the Layerbrain team:

```bash
make publish
```

The publish target runs:

```bash
prime env push --team layerbrain --visibility PUBLIC
```
