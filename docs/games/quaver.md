# Quaver

Quaver is the keyboard rhythm game environment in WarGames.

Missions launch Quaver charts from the default chart archives shipped with the
upstream game. The agent has to time lane presses as notes reach the receptors,
hold long notes, avoid misses, preserve health, and finish the chart while the
song keeps playing. WarGames captures rendered frames and game audio inside the
runtime; it does not open a game window or viewer on the host desktop.

Rewards use trusted Quaver state from a WarGames exporter compiled into the
game: chart metadata, song time, score, accuracy, combo, health, judgement
counts, completion, and failure state.

![Quaver control proof](../assets/quaver-control-proof.gif)

WarGames uses the upstream [Quaver project](https://github.com/Quaver/Quaver).
Quaver source code is MPL-2.0. The default chart archives and game assets are
from the Quaver project and retain their upstream notices.

## Run It

```bash
wargames install --game quaver
wargames missions --game quaver
wargames run \
  --game quaver \
  --mission quaver.chart.hyun-feat-lyuu-crossover-beginner.1159.easy \
  --agent scripted-wait \
  --record summary_only \
  --audio chunks
```

The game runs inside the Quaver Docker runtime image. `wargames install` clones
the pinned Quaver source into the Docker cache volume, compiles the WarGames
state exporter into Quaver, builds the release runtime, and records the install
manifest.

## Missions

WarGames exports one mission per default Quaver chart.

| Difficulty | Missions |
|---|---:|
| Easy | 10 |
| Normal | 20 |
| Hard | 40 |
| Total | 70 |

```bash
wargames missions --game quaver
```

Mission IDs use the chart slug, Quaver map id, and WarGames difficulty, for
example `quaver.chart.hyun-feat-lyuu-crossover-beginner.1159.easy`.

## Controls

Quaver uses keyboard lane controls. WarGames actions are still ordinary
keyboard events, so an agent can press, release, or tap lanes.

| Lane | 4K key | 7K key |
|---:|---|---|
| 1 | `A` | `A` |
| 2 | `S` | `S` |
| 3 | `K` | `D` |
| 4 | `L` | `Space` |
| 5 | - | `J` |
| 6 | - | `K` |
| 7 | - | `L` |

Useful native actions:

| Action | Control |
|---|---|
| `lane_1_tap` through `lane_7_tap` | Tap one lane briefly |
| `lane_1_press` through `lane_7_press` | Start holding one lane |
| `lane_1_release` through `lane_7_release` | Release one lane |
| `pause` | `Escape` |
| `wait` | Let the chart advance |

## Rewards

Rewards are scored from hidden Quaver state after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| `gameplay.score` | Score increases from accurate hits. |
| `gameplay.accuracy` | Timing quality across the chart. |
| `gameplay.combo` / `gameplay.max_combo` | Consecutive successful hits. |
| `gameplay.health` | Misses and weak judgements reduce survivability. |
| `judgements.marv` / `judgements.perf` / `judgements.great` | High-quality hits. |
| `judgements.miss` | Missed notes. |
| `mission.finished` / `mission.failed` | Final outcome. |

Reward profiles:

| Reward profile | Use |
|---|---|
| `standard` | Hit notes accurately, grow combo, preserve health, and finish the chart |

```bash
wargames reward-profile list --game quaver
```

The Quaver profile files live in `scenarios/quaver/profiles/`. The full reward
profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Agent Setup

An agent is just a program that stays running. WarGames writes one observation
JSON line to stdin, waits for one turn JSON line on stdout, applies that turn to
Quaver, and repeats.

```python
import json
import sys

for line in sys.stdin:
    observation = json.loads(line)
    turn = [
        {"name": "key_down", "arguments": {"key": "a"}},
        {"name": "wait", "arguments": {"ms": 35}},
        {"name": "key_up", "arguments": {"key": "a"}},
    ]
    print(json.dumps(turn), flush=True)
```

```yaml
id: my-quaver-agent
kind: subprocess
command: ["python", "my_agent.py"]
```
