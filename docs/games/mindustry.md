# Mindustry

Mindustry is the automation and base-defense environment in WarGames.

Missions cover survival maps with resource routing, construction, power,
turrets, wave defense, and base expansion.

Rewards use trusted state from a WarGames plugin loaded by the Mindustry
client: wave, core health, items, buildings, units, enemies, power, and
win/game-over state.

![Mindustry control proof](../assets/mindustry-control-proof.mp4)

## Run It

```bash
wargames install --game mindustry
wargames missions --game mindustry
wargames run \
  --game mindustry \
  --mission mindustry.survival.veins.normal \
  --agent scripted-wait \
  --record summary_only
```

The game runs inside the Mindustry Docker runtime image. `wargames install`
downloads the pinned Mindustry client and server jars into the Mindustry Docker
cache volume and builds the WarGames state plugin into the Mindustry mods
directory.

## Missions

WarGames ships survival missions across nine built-in maps and three
difficulties.

| Difficulty | Missions |
|---|---:|
| Easy | 9 |
| Normal | 9 |
| Hard | 9 |
| Total | 27 |

```bash
wargames missions --game mindustry
```

Mission IDs use the map slug and difficulty, for example
`mindustry.survival.veins.normal`. Easy missions target wave 10, normal targets
wave 20, and hard targets wave 40.

## Live Control

Mindustry uses the same pixel/action contract as the other games. Send keyboard
and mouse primitives to the rendered game window:

```bash
printf '%s\n' \
  '[{"name":"key_down","arguments":{"key":"d"}},{"name":"wait","arguments":{"ms":1000}},{"name":"key_up","arguments":{"key":"d"}}]' \
  | wargames control \
      --game mindustry \
      --mission mindustry.survival.veins.normal \
      --actions -
```

Useful controls:

| Action | Control |
|---|---|
| Pan camera | Hold `w`, `a`, `s`, or `d` |
| Select/place | Move mouse, then left click |
| Deselect/cancel | Right click or press `Escape` |
| Rotate block | Press `r` |
| Pause menu | Press `Escape` |
| Let factory run | Send `wait` |

## Rewards

Rewards are scored from hidden Mindustry game state after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| `game.wave` | Survival progress. |
| `game.enemies` | Enemy pressure. |
| `us.cores` | Base survival. |
| `us.units` | Unit production. |
| `us.buildings` | Factory expansion. |
| `us.items` | Resource accumulation. |
| `us.core_health` | Core health preservation. |
| `mission.finished` / `mission.failed` | Final outcome. |

Profiles:

| Profile | Use |
|---|---|
| `standard` | Survive waves, accumulate items, build infrastructure, and keep cores alive |

```bash
wargames profile list --game mindustry
```

The Mindustry profile files live in `scenarios/mindustry/profiles/`. The full
profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Agent Setup

An agent is just a program that stays running. WarGames writes one observation
JSON line to stdin, waits for one turn JSON line on stdout, applies that turn to
Mindustry, and repeats. The observation frame is a screenshot of the rendered
Mindustry window.

```python
import json
import sys

for line in sys.stdin:
    observation = json.loads(line)
    turn = [
        {"name": "key_down", "arguments": {"key": "d"}},
        {"name": "wait", "arguments": {"ms": 500}},
        {"name": "key_up", "arguments": {"key": "d"}},
    ]
    print(json.dumps(turn), flush=True)
```

```yaml
id: my-mindustry-agent
kind: subprocess
command: ["python", "my_agent.py"]
```
