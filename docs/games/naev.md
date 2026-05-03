# Naev

Naev is the 2D space trading and combat RPG environment in WarGames.

Missions launch upstream Naev mission scripts from the packaged game data. The
agent starts in a fresh campaign, sees the rendered game frames, hears game
audio captured inside the runtime, and controls the ship with normal keyboard
and mouse input. The runtime does not open a game window or viewer on the host
desktop.

Rewards use trusted Naev state from a Lua exporter loaded by the game: ship
system, position, velocity, credits, wealth, fuel, armour, shields, target, and
mission completion state. That trusted state is used for scoring and is not
included in the public observation payload.

![Naev control proof](../assets/naev-control-proof.gif)

WarGames uses the upstream [Naev project](https://github.com/naev/naev). Naev
code is GPL-3.0-or-later. Game data and media retain the upstream notices
listed by the Naev project and the packaged runtime.

## Run It

```bash
wargames install --game naev
wargames missions --game naev
wargames run \
  --game naev \
  --mission naev.mission.missions-tutorial-tutorial.easy \
  --agent scripted-wait \
  --record summary_only \
  --audio chunks
```

The game runs inside the Naev Docker runtime image. `wargames install` records
the packaged Naev binary and copies the packaged data into the WarGames cache
volume so each mission can start from a clean generated campaign.

## Missions

WarGames exports one mission per upstream Naev mission script in the packaged
game data.

| Difficulty | Missions |
|---|---:|
| Easy | 6 |
| Normal | 47 |
| Hard | 75 |
| Total | 128 |

```bash
wargames missions --game naev
```

Mission IDs use the mission script path and WarGames difficulty, for example
`naev.mission.missions-neutral-cargo.easy` and
`naev.mission.missions-dvaered-assault-on-unicorn.hard`.

## Live Control

Naev uses keyboard flight and combat controls:

```bash
printf '%s\n' \
  '[{"name":"key_down","arguments":{"key":"w"}},{"name":"wait","arguments":{"ms":600}},{"name":"key_down","arguments":{"key":"a"}},{"name":"wait","arguments":{"ms":200}},{"name":"key_up","arguments":{"key":"a"}},{"name":"key_down","arguments":{"key":"Space"}},{"name":"wait","arguments":{"ms":200}},{"name":"key_up","arguments":{"key":"Space"}},{"name":"key_up","arguments":{"key":"w"}}]' \
  | wargames control \
      --game naev \
      --mission naev.mission.missions-tutorial-tutorial.easy \
      --actions -
```

Useful native actions:

| Action | Control |
|---|---|
| `forward` / `reverse` | `W` / `S` thrust |
| `turn_left` / `turn_right` | `A` / `D` turn |
| `fire_primary` / `fire_secondary` | `Space` / `Shift` fire |
| `target_nearest` / `target_hostile` | `T` / `R` target selection |
| `face_target` | `Q` |
| `land_or_approach` | `L` |
| `jump` / `autonav` | `J` / `Control+J` |
| `map` | `M` |
| `cancel` | `Escape` |
| `wait` | Let the game advance |

## Rewards

Rewards are scored from hidden Naev state after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| `mission.completed_count` | Mission completion events. |
| `player.credits` / `player.wealth` | Trade, delivery, and reward progress. |
| `player.fuel` | Long-range navigation resource. |
| `player.armour` / `player.shield` | Ship survival. |
| `player.speed` / `player.system` | Navigation and travel state. |
| `player.target` / `player.target_distance` | Combat and approach context. |
| `mission.finished` / `mission.failed` | Final outcome. |

Reward profiles:

| Reward profile | Use |
|---|---|
| `standard` | Complete missions, earn resources, and preserve the ship |

```bash
wargames reward-profile list --game naev
```

The Naev profile files live in `scenarios/naev/profiles/`. The full reward
profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Agent Setup

An agent is just a program that stays running. WarGames writes one observation
JSON line to stdin, waits for one turn JSON line on stdout, applies that turn to
Naev, and repeats.

```python
import json
import sys

for line in sys.stdin:
    observation = json.loads(line)
    turn = [
        {"name": "key_down", "arguments": {"key": "w"}},
        {"name": "wait", "arguments": {"ms": 400}},
        {"name": "key_down", "arguments": {"key": "Space"}},
        {"name": "wait", "arguments": {"ms": 100}},
        {"name": "key_up", "arguments": {"key": "Space"}},
        {"name": "key_up", "arguments": {"key": "w"}},
    ]
    print(json.dumps(turn), flush=True)
```

```yaml
id: my-naev-agent
kind: subprocess
command: ["python", "my_agent.py"]
```
