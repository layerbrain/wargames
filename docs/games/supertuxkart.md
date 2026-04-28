# SuperTuxKart

SuperTuxKart is the kart-racing environment in WarGames.

The agent sees the race window as pixels. It controls the kart with keyboard
and mouse events. WarGames reads race metadata and process state only for
rewards. The agent does not see that hidden state.

![A model drives SuperTuxKart](../assets/supertuxkart-control-demo.gif)

## Run It

```bash
wargames install --game supertuxkart
wargames missions --game supertuxkart
wargames run \
  --game supertuxkart \
  --mission supertuxkart.race.lighthouse.normal \
  --agent scripted-wait \
  --record summary_only
```

The game runs inside the WarGames Docker runtime. SuperTuxKart and its data
come from the Linux runtime image.

## Missions

WarGames exports official SuperTuxKart race tracks as missions.

| Difficulty | Missions |
|---|---:|
| Easy | 21 |
| Normal | 21 |
| Hard | 21 |
| Total | 63 |

```bash
wargames missions --game supertuxkart
```

Easy races use one lap and fewer karts. Normal and hard races use the track's
default lap count with more opponents.

## Live Control

Send actions as JSON lines:

```bash
printf '%s\n' \
  '[{"name":"key_down","arguments":{"key":"ArrowUp"}},{"name":"wait","arguments":{"ms":1000}},{"name":"key_up","arguments":{"key":"ArrowUp"}}]' \
  | wargames control \
      --game supertuxkart \
      --mission supertuxkart.race.lighthouse.normal \
      --actions - \
      --watch
```

Useful controls:

| Action | Control |
|---|---|
| Accelerate | Hold `ArrowUp` |
| Brake / reverse | Hold `ArrowDown` |
| Steer | Hold `ArrowLeft` or `ArrowRight` |
| Use item | Press `Space` |
| Nitro | Press or hold `n` |
| Rescue/reset | Press `r` |

## Rewards

Rewards are scored from hidden SuperTuxKart mission state after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| Mission complete / failed | Main outcome. |
| Track | Identifies which race is running. |
| Laps and kart count | Tracks the race setup. |
| Elapsed ticks | Measures time spent in the race. |

Profiles:

| Profile | Use |
|---|---|
| `standard` | Complete the race without process failure |

```bash
wargames profile list --game supertuxkart
```

The SuperTuxKart profile files live in `scenarios/supertuxkart/profiles/`. The
full profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Agent Setup

An agent is just a program that stays running.

WarGames starts `python my_agent.py`, writes one observation JSON line to stdin,
waits for one turn JSON line on stdout, applies that turn to SuperTuxKart, and
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
    observation = json.loads(line)
    turn = [
        {"name": "key_down", "arguments": {"key": "ArrowUp"}},
        {"name": "wait", "arguments": {"ms": 500}},
        {"name": "key_up", "arguments": {"key": "ArrowUp"}},
    ]
    print(json.dumps(turn), flush=True)
```

The `print(..., flush=True)` line is the whole send path. Your agent does not
call a WarGames API. WarGames is already watching stdout, reads that one line,
and applies it to SuperTuxKart.

```yaml
id: my-supertuxkart-agent
kind: subprocess
command: ["python", "my_agent.py"]
```

```bash
wargames run \
  --game supertuxkart \
  --mission supertuxkart.race.lighthouse.normal \
  --profile standard \
  --agent my-supertuxkart-agent \
  --agent-dir .
```

Send SuperTuxKart controls as primitive events:

```json
{"name":"key_down","arguments":{"key":"ArrowUp"}}
{"name":"key_up","arguments":{"key":"ArrowUp"}}
{"name":"key_down","arguments":{"key":"ArrowLeft"}}
{"name":"key_up","arguments":{"key":"ArrowLeft"}}
{"name":"wait","arguments":{"ms":250}}
```

## Prime RL

```bash
uv pip install -e ./environments/prime

prime eval run wargames \
  --config environments/prime/configs/supertuxkart/eval-lighthouse.toml \
  -n 1 -r 1
```
