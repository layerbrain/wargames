# WarGames OpenReward

OpenReward surface for WarGames Red Alert.

```bash
uv pip install -e .
uvicorn wargames_openreward.app:app --port 8001
```

Smoke:

```bash
curl http://127.0.0.1:8001/splits
curl http://127.0.0.1:8001/tasks/debug
curl http://127.0.0.1:8001/tools
```

The environment exposes only WarGames CUA tools:

- `click`
- `move_mouse`
- `double_click`
- `drag`
- `key`
- `type_text`
- `scroll`
- `wait`

OpenReward publishing is through the OpenReward web UI and GitHub deployment.
Run local gates first:

```bash
make prepublish
```
