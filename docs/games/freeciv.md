# Freeciv

Freeciv is the low-memory, long-horizon turn-based strategy environment in
WarGames.

WarGames captures the GTK client window as pixels, applies standard keyboard
and mouse actions, and scores rewards from authoritative Freeciv server save
snapshots: turn, year, players, cities, units, treasury, tax rates, map
knowledge, and victory/defeat state.

![Freeciv control demo](../assets/freeciv-control-demo.gif)

## Run It

```bash
wargames install --game freeciv
wargames missions --game freeciv
wargames run \
  --game freeciv \
  --mission freeciv.duel.tiny.easy \
  --agent scripted-wait \
  --record summary_only
```

The game runs inside the Freeciv Docker runtime image. `wargames install`
registers the packaged Freeciv server and GTK client in the Freeciv Docker
cache volume.

## Missions

WarGames ships 30 Freeciv missions across easy, normal, and hard difficulties.
They are curated for long-horizon strategy while keeping map sizes small enough
for low runtime memory.

| Mission | Difficulty | Setup |
|---|---|---|
| `freeciv.duel.tiny.easy` | easy | Tiny two-player duel |
| `freeciv.builder.tiny.easy` | easy | Small builder opening with extra start units |
| `freeciv.scout-contact.tiny.easy` | easy | Two-player exploration opener |
| `freeciv.settler-race.tiny.easy` | easy | Fast settlement race |
| `freeciv.coastal-opening.tiny.easy` | easy | Coastal expansion start |
| `freeciv.frontier-three.small.easy` | easy | Three-player frontier map |
| `freeciv.research-start.small.easy` | easy | Early research advantage |
| `freeciv.expansion-small.easy` | easy | Small expansion race |
| `freeciv.sparse-duel.small.easy` | easy | Wider two-player exploration |
| `freeciv.compact-three.tiny.easy` | easy | Compact three-player opener |
| `freeciv.continents.small.normal` | normal | Four-player exploration game |
| `freeciv.science.small.normal` | normal | Four-player science-focused opening |
| `freeciv.frontier.small.normal` | normal | Three-player frontier game |
| `freeciv.trade-triangle.small.normal` | normal | Three-player economy start |
| `freeciv.four-way-contact.small.normal` | normal | Four-player contact map |
| `freeciv.republic-race.small.normal` | normal | Government and science race |
| `freeciv.long-game.small.normal` | normal | Longer small-map game |
| `freeciv.open-map.small.normal` | normal | Wider four-player map |
| `freeciv.compact-four.small.normal` | normal | Compact four-player pressure |
| `freeciv.builder-four.small.normal` | normal | Four-player builder opening |
| `freeciv.crowded-empire.hard` | hard | Six-player crowded empire game |
| `freeciv.domination.standard.hard` | hard | Seven-player standard domination game |
| `freeciv.seven-fronts.standard.hard` | hard | Seven-player contact pressure |
| `freeciv.science-pressure.standard.hard` | hard | Six-player science pressure |
| `freeciv.expansion-pressure.standard.hard` | hard | Expansion under pressure |
| `freeciv.survival-small.hard` | hard | Small crowded survival map |
| `freeciv.recovery-small.hard` | hard | Lean recovery start |
| `freeciv.wide-standard.hard` | hard | Wider six-player map |
| `freeciv.compact-brawl.hard` | hard | Compact seven-player brawl |
| `freeciv.marathon-standard.hard` | hard | Long-horizon standard game |

Mission JSON lives in `scenarios/freeciv/missions/<difficulty>/`.

## Live Control

Send actions as JSON lines:

```bash
printf '%s\n' \
  '[{"name":"move_mouse","arguments":{"x":620,"y":420}},{"name":"mouse_down","arguments":{"button":"left"}},{"name":"mouse_up","arguments":{"button":"left"}}]' \
  | wargames control \
      --game freeciv \
      --mission freeciv.duel.tiny.easy \
      --actions - \
      --watch
```

Useful controls:

| Action | Control |
|---|---|
| Select unit or city | Left click |
| Move selected unit | Arrow keys, numpad, or map click depending on active mode |
| End turn | Turn Done button or `Shift+Return` |
| Open menus | Standard Freeciv GTK menu shortcuts |

## Rewards

Rewards are scored from Freeciv save state after each action.

Useful signals:

| Signal | Why it matters |
|---|---|
| `game.turn` | Long-horizon progress through turns. |
| `us.city_count` | Settlement growth. |
| `us.unit_count` | Unit production and force size. |
| `us.gold` | Treasury management. |
| `us.known_tiles` | Exploration and map knowledge. |
| `enemies` | Alive opponent player state. |
| `mission.finished` / `mission.failed` | Final outcome. |

Profiles:

| Profile | Use |
|---|---|
| `standard` | Explore, settle cities, grow units and gold, and win |

```bash
wargames profile list --game freeciv
```

The Freeciv profile files live in `scenarios/freeciv/profiles/`. The full
profile spec is in [`../reward_profiles.md`](../reward_profiles.md).

## Prime RL

```bash
uv pip install -e ./environments/prime

prime eval run wargames \
  --config environments/prime/configs/freeciv/eval-duel.toml \
  -n 1 -r 1
```
