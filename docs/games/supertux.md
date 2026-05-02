# SuperTux

SuperTux is the side-scrolling platformer environment in WarGames.

Missions cover official SuperTux levels with movement, jumping, enemies,
collectibles, checkpoint progress, and level completion.

Rewards use trusted state from a WarGames exporter compiled into SuperTux:
position, velocity, coins, enemies, checkpoint progress, death state, and level
completion.

![SuperTux control proof](../assets/supertux-control-proof.mp4)

## Run It

```bash
wargames install --game supertux
wargames missions --game supertux
wargames run \
  --game supertux \
  --mission supertux.level.world1.welcome-antarctica.normal \
  --agent scripted-wait \
  --record summary_only
```

The game runs inside the SuperTux Docker runtime image. `wargames install`
clones SuperTux into the SuperTux Docker cache volume, builds the WarGames
state exporter into the binary, and uses the official SuperTux data files from
that checkout.

## Missions

WarGames exports official SuperTux level files as missions.

| Difficulty | Missions |
|---|---:|
| Easy | 107 |
| Normal | 107 |
| Hard | 107 |
| Total | 321 |

```bash
wargames missions --game supertux
```

Mission IDs use the level set, level file name, and difficulty, for example
`supertux.level.world1.welcome-antarctica.normal`.

## Live Control

Send actions as JSON lines:

```bash
printf '%s\n' \
  '[{"name":"key_down","arguments":{"key":"ArrowRight"}},{"name":"wait","arguments":{"ms":1000}},{"name":"key_up","arguments":{"key":"ArrowRight"}}]' \
  | wargames control \
      --game supertux \
      --mission supertux.level.world1.welcome-antarctica.normal \
      --actions - \
      --watch
```

Useful controls:

| Action | Control |
|---|---|
| Move | Hold `ArrowLeft` or `ArrowRight` |
| Jump | Press or hold `Space` |
| Duck | Hold `ArrowDown` |
| Enter doors / climb | Press or hold `ArrowUp` |
| Pause menu | Press `Escape` |

## Rewards

Rewards are scored from hidden SuperTux state after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| `level.coins` | Coin collection progress. |
| `level.secrets` | Exploration progress. |
| `level.elapsed_ticks` | Time pressure. |
| `player.x/y` | Position through the level. |
| `player.vx/vy` | Movement and jump dynamics. |
| `player.bonus` | Current power-up state. |
| `player.dead` | Failure and death penalty. |
| `mission.finished` / `mission.failed` | Final outcome. |

Profiles:

| Profile | Use |
|---|---|
| `standard` | Move right, collect coins and secrets, stay alive, and finish |

```bash
wargames profile list --game supertux
```

The SuperTux profile files live in `scenarios/supertux/profiles/`. The full
profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Agent Setup

An agent is just a program that stays running. WarGames writes one observation
JSON line to stdin, waits for one turn JSON line on stdout, applies that turn to
SuperTux, and repeats.

```python
import json
import sys

for line in sys.stdin:
    observation = json.loads(line)
    turn = [
        {"name": "key_down", "arguments": {"key": "ArrowRight"}},
        {"name": "wait", "arguments": {"ms": 500}},
        {"name": "key_up", "arguments": {"key": "ArrowRight"}},
    ]
    print(json.dumps(turn), flush=True)
```

```yaml
id: my-supertux-agent
kind: subprocess
command: ["python", "my_agent.py"]
```
