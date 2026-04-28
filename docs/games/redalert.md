# Red Alert

Red Alert is the first WarGames environment.

WarGames captures the OpenRA window as pixels, applies mouse and keyboard
actions, and reads OpenRA state for rewards.

![Red Alert control demo](../assets/redalert-control-demo.gif)

## Run It

```bash
wargames install --game redalert
wargames missions --game redalert
wargames run \
  --game redalert \
  --mission redalert.soviet-01.normal \
  --agent scripted-wait \
  --record summary_only
```

The game runs inside the Red Alert Docker runtime image. OpenRA and the Red
Alert content are cached in the Red Alert Docker volume.

## Missions

WarGames exports OpenRA Red Alert maps as missions.

| Difficulty | Missions |
|---|---:|
| Easy | 47 |
| Normal | 201 |
| Hard | 49 |
| Total | 297 |

```bash
wargames missions --game redalert
```

The missions include campaign maps, skirmish maps, base building, scouting,
resource management, and long real-time fights.

## Live Control

Send actions as JSON lines:

```bash
printf '%s\n' \
  '{"name":"move_mouse","arguments":{"x":640,"y":360}}' \
  '{"name":"mouse_down","arguments":{"button":"right"}}' \
  '{"name":"mouse_up","arguments":{"button":"right"}}' \
  '{"name":"key_down","arguments":{"key":"a"}}' \
  '{"name":"key_up","arguments":{"key":"a"}}' \
  | wargames control \
      --game redalert \
      --mission redalert.soviet-01.normal \
      --actions - \
      --watch
```

Useful controls:

| Action | Control |
|---|---|
| Select | Move pointer, left `mouse_down`, left `mouse_up` |
| Box select | Move pointer, left `mouse_down`, move pointer, left `mouse_up` |
| Move / attack | Move pointer, right `mouse_down`, right `mouse_up` |
| Pan camera | Arrow keys or screen edge |
| Control groups | Hold `Control`, press a number key, release both keys |
| Build | Move pointer to sidebar buttons and use mouse down/up |

## Rewards

Rewards are scored from hidden OpenRA state after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| Mission complete / failed | Main outcome. |
| Objectives | Measures progress before the final win. |
| Cash and power | Tracks economy. |
| Units killed | Tracks combat progress. |
| Friendly losses | Penalizes wasteful play. |
| Scouted tiles | Rewards exploration. |

Profiles:

| Profile | Use |
|---|---|
| `terminal` | Sparse final scoring |
| `standard` | General eval |
| `dense` | Training |
| `protective` | Training with stronger preservation reward |
| `speedrun` | Fast decisive play |
| `aggressive_stress_test` | Contrast profile for stress testing |

```bash
wargames profile list --game redalert
```

The Red Alert profile files live in `scenarios/redalert/profiles/`. The full
profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Agent Setup

An agent is just a program that stays running.

WarGames starts `python my_agent.py`, writes one observation JSON line to stdin,
waits for one turn JSON line on stdout, applies that turn to Red Alert, and
repeats.

The observation has `task`, `frame.image_b64`, `history`, `step_index`, and
`elapsed_seconds`. Your agent does not send that object back. It sends back
one primitive event or one array of primitive events. The action set is the
fixed WarGames keyboard + mouse set.

Trimmed observation your agent receives:

```json
{"frame":{"image_b64":"iVBORw0KGgo...","width":1280,"height":720},"history":[],"step_index":0,"elapsed_seconds":0.0}
```

```python
import json
import sys

for line in sys.stdin:
    observation = json.loads(line)  # RECEIVE one observation from WarGames
    turn = {"name": "wait", "arguments": {}}
    print(json.dumps(turn), flush=True)  # SEND one turn to WarGames
```

The `print(..., flush=True)` line is the whole send path. Your agent does not
call a WarGames API. WarGames is already watching stdout, reads that one line,
and applies it to Red Alert.

One line can also contain a short planned sequence:

```python
turn = [
    {"name": "key_down", "arguments": {"key": "Control"}},
    {"name": "key_down", "arguments": {"key": "1"}},
    {"name": "key_up", "arguments": {"key": "1"}},
    {"name": "key_up", "arguments": {"key": "Control"}},
]
print(json.dumps(turn), flush=True)
```

```yaml
id: my-redalert-agent
kind: subprocess
command: ["python", "my_agent.py"]
```

```bash
wargames run \
  --game redalert \
  --mission redalert.soviet-01.normal \
  --profile speedrun \
  --agent my-redalert-agent \
  --agent-dir .
```

Send Red Alert controls as primitive events:

```json
{"name":"move_mouse","arguments":{"x":640,"y":360}}
{"name":"mouse_down","arguments":{"button":"left"}}
{"name":"mouse_up","arguments":{"button":"left"}}
{"name":"key_down","arguments":{"key":"a"}}
{"name":"key_up","arguments":{"key":"a"}}
{"name":"wait","arguments":{}}
```

## Prime RL

```bash
uv pip install -e ./environments/prime

prime eval run wargames \
  --config environments/prime/configs/redalert/eval-soviet-01.toml \
  -n 1 -r 1
```
