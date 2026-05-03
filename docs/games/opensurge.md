# Open Surge

Open Surge is the fast side-scrolling momentum platformer environment in
WarGames.

Missions launch built-in Open Surge acts directly. The agent has to accelerate,
jump, roll, keep rings, and clear the act while the level keeps running.
WarGames captures the rendered frames and game audio inside the runtime; it does
not open a game window or viewer on the host desktop.

Rewards use trusted Open Surge state from a WarGames exporter compiled into the
engine: level timer, act completion, player position, speed, ground speed,
rings, score, lives, and movement state.

![Open Surge control proof](../assets/opensurge-control-proof.gif)

WarGames uses the upstream [Open Surge project](https://github.com/alemart/opensurge).
Open Surge is GPL-3.0-or-later. The bundled game assets are authored by the
Open Surge project and carry their upstream notices in the source tree.

## Run It

```bash
wargames install --game opensurge
wargames missions --game opensurge
wargames run \
  --game opensurge \
  --mission opensurge.level.sunshine-1.normal \
  --agent scripted-wait \
  --record summary_only \
  --audio chunks
```

The game runs inside the Open Surge Docker runtime image. `wargames install`
clones the pinned Open Surge source into the Docker cache volume, builds
SurgeScript, compiles the WarGames state exporter into Open Surge, and records
the install manifest.

## Missions

WarGames exports built-in Open Surge level files as missions.

| Difficulty | Missions |
|---|---:|
| Easy | 11 |
| Normal | 11 |
| Hard | 11 |
| Total | 33 |

```bash
wargames missions --game opensurge
```

Mission IDs use the level slug and difficulty, for example
`opensurge.level.sunshine-1.normal` and `opensurge.level.waterworks-zone-3.hard`.

## Live Control

Open Surge uses the same keyboard and mouse action format as the other games:

```bash
printf '%s\n' \
  '[{"name":"key_down","arguments":{"key":"ArrowRight"}},{"name":"wait","arguments":{"ms":450}},{"name":"key_down","arguments":{"key":"Space"}},{"name":"wait","arguments":{"ms":120}},{"name":"key_up","arguments":{"key":"Space"}},{"name":"key_up","arguments":{"key":"ArrowRight"}}]' \
  | wargames control \
      --game opensurge \
      --mission opensurge.level.sunshine-1.normal \
      --actions -
```

Useful controls:

| Action | Control |
|---|---|
| Move | Arrow keys |
| Jump | `Space` |
| Roll/crouch | `ArrowDown` |
| Look up | `ArrowUp` |
| Action | `Control` |
| Let the level advance | Send `wait` |

## Rewards

Rewards are scored from hidden Open Surge state after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| `player.x` | Forward progress through the act. |
| `player.speed` / `player.gsp` | Momentum and ground speed. |
| `player.rings` | Ring collection and survival buffer. |
| `player.score` | Enemy, item, and bonus scoring. |
| `player.dying` | Death state. |
| `mission.finished` / `mission.failed` | Final outcome. |

Reward profiles:

| Reward profile | Use |
|---|---|
| `standard` | Move forward quickly, collect rings, increase score, and clear the act |

```bash
wargames reward-profile list --game opensurge
```

The Open Surge profile files live in `scenarios/opensurge/profiles/`. The full
reward profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Agent Setup

An agent is just a program that stays running. WarGames writes one observation
JSON line to stdin, waits for one turn JSON line on stdout, applies that turn to
Open Surge, and repeats.

```python
import json
import sys

for line in sys.stdin:
    observation = json.loads(line)
    turn = [
        {"name": "key_down", "arguments": {"key": "ArrowRight"}},
        {"name": "wait", "arguments": {"ms": 450}},
        {"name": "key_down", "arguments": {"key": "Space"}},
        {"name": "wait", "arguments": {"ms": 120}},
        {"name": "key_up", "arguments": {"key": "Space"}},
        {"name": "key_up", "arguments": {"key": "ArrowRight"}},
    ]
    print(json.dumps(turn), flush=True)
```

```yaml
id: my-opensurge-agent
kind: subprocess
command: ["python", "my_agent.py"]
```
