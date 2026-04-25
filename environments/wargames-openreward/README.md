# WarGames For OpenReward

OpenReward surface for WarGames Red Alert. The public OpenReward environment is
`layerbrain/wargames`. The implementation lives in
`wargames.environments.openreward`; this folder is only the publish wrapper.

```bash
uv pip install -e .
uvicorn wargames_openreward.app:app --port 8001
```

Smoke the OpenReward protocol:

```bash
curl http://127.0.0.1:8001/list_environments
curl http://127.0.0.1:8001/wargames/tools
curl http://127.0.0.1:8001/standard/splits
curl -X POST http://127.0.0.1:8001/standard/tasks \
  -H 'content-type: application/json' \
  -d '{"split":"debug"}'
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

Publish to the `layerbrain/wargames` OpenReward environment:

```bash
make prepublish
make publish
```
