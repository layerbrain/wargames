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

Publish under the Layerbrain team:

```bash
make publish
```

The publish target runs:

```bash
prime env push --name wargames --team layerbrain --visibility PUBLIC
```
