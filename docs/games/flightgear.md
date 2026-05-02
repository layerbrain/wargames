# FlightGear

FlightGear is the C172P flight simulator environment in WarGames. Missions cover
takeoff, traffic-pattern flying, approach control, and landing.

Rewards use FlightGear telemetry such as altitude, airspeed, heading, position,
vertical speed, runway alignment, and touchdown state.

![FlightGear control demo](../assets/flightgear-c172p-control-demo.gif)

## Run It

```bash
wargames install --game flightgear
wargames missions --game flightgear
wargames run \
  --game flightgear \
  --mission flightgear.c172p.tutorial.takeoff \
  --agent scripted-wait \
  --record summary_only
```

The game runs inside the FlightGear Docker runtime image. FlightGear data is
cached in the FlightGear Docker volume.

## Missions

WarGames exports FlightGear's C172P tutorials as missions.

| Difficulty | Missions |
|---|---:|
| Easy | 7 |
| Normal | 4 |
| Hard | 3 |
| Total | 14 |

```bash
wargames missions --game flightgear
```

These missions cover preflight, startup, taxiing, runup, radios, altimeter,
takeoff, landing, securing the aircraft, pattern work, engine failure, and
amphibious operations.

## Live Control

Send actions as JSON lines:

```bash
printf '%s\n' \
  '{"name":"key_down","arguments":{"key":"PageUp"}}' \
  '{"name":"wait","arguments":{}}' \
  '{"name":"key_up","arguments":{"key":"PageUp"}}' \
  | wargames control \
      --game flightgear \
      --mission flightgear.c172p.tutorial.takeoff \
      --actions - \
      --watch
```

Useful C172P keys:

| Key | Action |
|---|---|
| `PageUp` / `PageDown` | Throttle up / down |
| `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight` | Pitch and roll |
| `[` / `]` | Flaps |
| `g` | Gear |
| `b` | Brakes |
| `x` / `Shift+x` | Zoom |

## Rewards

Rewards are scored from FlightGear telemetry after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| Altitude | Stay airborne and descend safely. |
| Airspeed | Avoid stalls and overspeed. |
| Pitch and roll | Keep the plane stable. |
| Vertical speed | Detect hard landings and bad descents. |
| Crash / stall flags | End failed runs. |

Profiles:

| Profile | Use |
|---|---|
| `standard` | Complete the route while keeping the aircraft stable |

```bash
wargames profile list --game flightgear
```

The FlightGear profile files live in `scenarios/flightgear/profiles/`. The full
profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Agent Setup

An agent is just a program that stays running.

WarGames starts `python my_agent.py`, writes one observation JSON line to stdin,
waits for one turn JSON line on stdout, applies that turn to FlightGear, and
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
and applies it to FlightGear.

One line can also contain a short planned sequence:

```python
turn = [
    {"name": "key_down", "arguments": {"key": "PageUp"}},
    {"name": "wait", "arguments": {"ms": 250}},
    {"name": "key_up", "arguments": {"key": "PageUp"}},
]
print(json.dumps(turn), flush=True)
```

```yaml
id: my-flightgear-agent
kind: subprocess
command: ["python", "my_agent.py"]
```

```bash
wargames run \
  --game flightgear \
  --mission flightgear.c172p.tutorial.takeoff \
  --profile standard \
  --agent my-flightgear-agent \
  --agent-dir .
```

Send FlightGear controls as primitive events:

```json
{"name":"key_down","arguments":{"key":"PageUp"}}
{"name":"key_up","arguments":{"key":"PageUp"}}
{"name":"key_down","arguments":{"key":"ArrowLeft"}}
{"name":"key_up","arguments":{"key":"ArrowLeft"}}
{"name":"wait","arguments":{}}
```

## Prime RL

```bash
uv pip install -e ./environments/prime

prime eval run wargames \
  --config environments/prime/configs/flightgear/eval-c172p-takeoff.toml \
  -n 1 -r 1
```
