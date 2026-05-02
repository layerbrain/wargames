# WarGames

WarGames turns real-time games into computer-use RL environments.

WarGames launches the game, captures pixels, applies mouse and keyboard
events, records the episode, and scores rewards from trusted per-game probes.
Bring your own trainer or use the Prime RL adapter in this repo.

![Red Alert control demo](docs/assets/redalert-control-demo.gif)

```text
                    +-----------------------------+
                    |        Game process         |
                    | OpenRA, FlightGear, STK,    |
                    | Freeciv, Doom, SuperTux,    |
                    | Mindustry                   |
                    +--------------+--------------+
                                   |
                 capture           |          scoring state
            +---------------+      |      +-------------------+
            | window pixels | <----+----> | probe: units,     |
            |   1280x720    |             | flight telemetry, |
            +-------+-------+             | gameplay state    |
                                           +---------+---------+
                    |                               |
                    v                               v
              +-----------+                  +-------------+
              |   Agent   |                  |  Evaluator  |
              | (model)   |                  | (profile)   |
              +-----+-----+                  +------+------+
                    |                               |
                    | action                        | reward
                    v                               v
              back to game                    to your trainer
```

The screen/action lane is the controller interface. The probe lane feeds the
evaluator, where a reward profile turns game-specific state into the scalar
reward your trainer consumes.

## Games

| Game | World | Missions | Docs |
|---|---|---:|---|
| Red Alert | OpenRA real-time strategy | 297 | [docs/games/redalert.md](docs/games/redalert.md) |
| FlightGear | First-person C172P flight sim | 14 | [docs/games/flightgear.md](docs/games/flightgear.md) |
| SuperTuxKart | Real-time 3D kart racing | 63 | [docs/games/supertuxkart.md](docs/games/supertuxkart.md) |
| 0 A.D. | Real-time ancient warfare | 390 | [docs/games/zeroad.md](docs/games/zeroad.md) |
| Freeciv | Low-memory turn-based empire strategy | 12 | [docs/games/freeciv.md](docs/games/freeciv.md) |
| Doom | First-person arcade combat | 204 | [docs/games/doom.md](docs/games/doom.md) |
| SuperTux | Side-scrolling platformer | 321 | [docs/games/supertux.md](docs/games/supertux.md) |
| Mindustry | Pixel-control factory survival | 27 | [docs/games/mindustry.md](docs/games/mindustry.md) |

A run is four pieces: a game, a mission, a reward profile, and an agent.

## Quickstart

Games run inside Docker. Nothing is installed on your host. Each game has its
own runtime image and cache volume, with a small shared base image for Python,
Xvfb, and window capture.

```bash
git clone https://github.com/layerbrain/wargames.git
cd wargames
python3 -m venv venv
source venv/bin/activate
pip install -e .

wargames install --game redalert
wargames install --game flightgear
wargames install --game supertuxkart
wargames install --game zeroad
wargames install --game freeciv
wargames install --game doom
wargames install --game supertux
wargames install --game mindustry
```

Run a SuperTuxKart episode:

```bash
wargames run \
  --game supertuxkart \
  --mission supertuxkart.race.lighthouse.normal \
  --agent scripted-wait \
  --record summary_only
```

List what ships:

```bash
wargames missions --game redalert
wargames missions --game flightgear
wargames missions --game supertuxkart
wargames missions --game zeroad
wargames missions --game freeciv
wargames missions --game doom
wargames missions --game supertux
wargames missions --game mindustry
```

## Run Your Own Model

The simplest path is an OpenAI-compatible model:

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-4o-mini

wargames run \
  --game redalert \
  --mission redalert.soviet-01.normal \
  --profile standard \
  --agent openai-quickstart \
  --record full
```

`openai-quickstart` is the included OpenAI-compatible agent. It reads the env
vars above and returns primitive keyboard and mouse events.

## Live Control

You can send actions to a live watched session as JSON lines. Each line can be
one primitive event or one array of primitive events.

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

That is the same action format a model uses.

## Observations

Each step, the agent gets one JSON object:

| Field | What it is |
|---|---|
| `task` | Mission id, game id, profile, limits, and prompt text for this run. |
| `frame.image_b64` | Latest game frame, PNG bytes base64-encoded. |
| `frame.width`, `frame.height` | Frame dimensions in pixels. Default 1280x720. |
| `history` | Public actions the agent has already sent this run. |
| `step_index` | Zero-based step counter. |
| `elapsed_seconds` | Wall-clock seconds since the run started. |

State used for scoring stays inside the evaluator and is not included in the
observation payload.

## Actions

The action set is shared across games. These are primitive input events. No
shortcut action combines pointer movement, button presses, or key presses.

| Action | What it does |
|---|---|
| `move_mouse` | Move the pointer to a window pixel. |
| `mouse_down` | Press a mouse button at the current pointer position. |
| `mouse_up` | Release a mouse button at the current pointer position. |
| `key_down` | Press one keyboard key. |
| `key_up` | Release one keyboard key. |
| `scroll` | Scroll the target window. |
| `wait` | Let the game advance without input. `{"ms":1000}` sleeps one second of wall-clock; default is `ms:0`. |

Coordinates are pixels inside the game window. Mouse buttons are `left`,
`right`, or `middle`.

Every primitive action your agent can send:

```json
{"name":"move_mouse","arguments":{"x":640,"y":360}}
{"name":"mouse_down","arguments":{"button":"left"}}
{"name":"mouse_up","arguments":{"button":"left"}}
{"name":"key_down","arguments":{"key":"PageUp"}}
{"name":"key_up","arguments":{"key":"PageUp"}}
{"name":"scroll","arguments":{"dx":0,"dy":-3}}
{"name":"wait","arguments":{}}
```

There is no shortcut `click` or `drag` action. To emulate a click, send
`move_mouse`, `mouse_down`, then `mouse_up`. To hold input, send the down
event, one or more `wait` events, then the up event.

Keys use WarGames names, not X11 names: lowercase letters, digits, common
symbol keys, `Control`, `Shift`, `Alt`, `Meta`, `Enter`, `Escape`, `Space`,
`Tab`, `Backspace`, `PageUp`, `PageDown`, `ArrowUp`, `ArrowDown`,
`ArrowLeft`, `ArrowRight`, and `F1` through `F12`.

## Missions

A mission is exported game content - a Red Alert map, a FlightGear C172P
tutorial, a SuperTuxKart race track, a 0 A.D. map, a Freeciv scenario, a Doom
map, a SuperTux level, or a Mindustry survival map - wrapped with a difficulty,
a step budget, a wall-clock budget, and a starting reward profile.
Mission IDs look like `redalert.soviet-01.normal`,
`flightgear.c172p.tutorial.takeoff`, `supertuxkart.race.lighthouse.normal`,
`zeroad.scenario.arcadia.normal`, `freeciv.scenario.earth-small`,
`doom.map.map01.easy`, `supertux.level.world1.welcome-antarctica.normal`, and
`mindustry.survival.veins.normal`. They are the same string you pass to
`--mission`, the WebSocket `create_session` op, and Prime RL configs.

```bash
wargames missions --game redalert --difficulty hard
wargames missions --game flightgear
wargames missions --game supertuxkart
wargames missions --game zeroad
wargames missions --game freeciv
wargames missions --game doom
wargames missions --game supertux
wargames missions --game mindustry
```

Mission JSON lives in `scenarios/<game>/missions/<difficulty>/`. Catalogs are
generated from installed game assets; when no game assets are available, the
game reports no missions.

## Profiles

A reward profile is the reward function for a run. It turns scoring state
into the scalar reward your trainer sees, with per-step shaping and a final
terminal score.

The YAML format is universal, but **each game ships its own schema**: the
state fields and reward primitives Red Alert exposes (`us.cash`,
`mission.objectives`, `delta_units_killed`, ...) are different from
FlightGear's (`aircraft.altitude_ft`, `aircraft.crashed`, ...). Profiles for
one game cannot be applied to another.

Shipped profiles:

| Game | Profiles |
|---|---|
| Red Alert | `terminal`, `standard`, `dense`, `protective`, `speedrun`, `aggressive_stress_test` |
| FlightGear | `standard` |
| SuperTuxKart | `standard` |
| 0 A.D. | `standard` |
| Freeciv | `standard` |
| Doom | `standard` |
| SuperTux | `standard` |
| Mindustry | `standard` |

```bash
wargames profile list --game redalert
wargames profile list --game flightgear
wargames profile list --game supertuxkart
wargames profile list --game zeroad
wargames profile list --game freeciv
wargames profile list --game doom
wargames profile list --game supertux
wargames profile list --game mindustry
wargames profile validate scenarios/redalert/profiles/protective.yaml
```

Full schema and the per-game field/primitive tables: [`docs/reward_profiles.md`](docs/reward_profiles.md).

## Custom Agents

An agent is just a program that stays running.

Subprocess agents use sampled mode: WarGames sends one observation, blocks on
one turn line, applies it, then sends the next observation. The protocol is
two newline-delimited JSON streams over stdin/stdout.

1. WarGames writes one observation JSON line to your program's stdin.
2. Your program writes one turn JSON line to stdout (`flush=True`).
3. WarGames applies the event or events in that turn and loops.

A trimmed observation looks like:

```json
{"frame":{"image_b64":"iVBORw0KGgo...","width":1280,"height":720},"history":[],"step_index":0,"elapsed_seconds":0.0}
```

The smallest agent that follows the protocol:

```python
import json
import sys

for line in sys.stdin:
    observation = json.loads(line)
    action = {"name": "wait", "arguments": {}}
    print(json.dumps(action), flush=True)
```

A turn can also be an array. WarGames applies the events in order before it
sends the next observation:

```python
turn = [
    {"name": "key_down", "arguments": {"key": "PageUp"}},
    {"name": "wait", "arguments": {"ms": 250}},
    {"name": "key_up", "arguments": {"key": "PageUp"}},
]
print(json.dumps(turn), flush=True)
```

Save that as `my_agent.py`, then add an agent config:

```yaml
id: my-agent
kind: subprocess
command: ["python", "my_agent.py"]
```

```bash
wargames run \
  --game flightgear \
  --mission flightgear.c172p.tutorial.takeoff \
  --agent my-agent \
  --agent-dir .
```

The `print(..., flush=True)` line is the whole send path. There is no API
client. WarGames is already watching stdout, reads that one line, and applies
it. A turn can contain up to 64 primitive events and at most five seconds of
explicit `wait` time. Action shapes are the ones listed under [Actions](#actions).

To stop the episode early, print one line:

```json
{"stop":true,"reason":"done"}
```

Two more sampled examples ship in this repo:

- [`examples/agents/wait_agent.py`](examples/agents/wait_agent.py): sends `wait` every step.
- [`examples/agents/circle_mouse.py`](examples/agents/circle_mouse.py): moves the mouse in a circle.

## End Reasons And Summary

When a mission ends, WarGames stops asking for actions, scores the terminal
reward, and prints a run summary (also written to `summary.json` when
recording is enabled). It does **not** send a final observation to the
subprocess.

| `end_reason` | Meaning |
|---|---|
| `objective_complete` | The game reported mission success. |
| `defeat` | The game reported mission failure. |
| `max_steps` | The run hit its step limit. |
| `wall_timeout` | The run hit its wall-clock limit. |
| `agent_stop` or custom reason | Your agent printed `{"stop":true,...}`. |
| `subprocess_closed` | Your agent process exited before returning a turn. |

Summary shape:

```json
{"run_id":"...","total_reward":1.0,"breakdown":{"terminal":1.0},"finished":true,"truncated":false,"end_reason":"objective_complete","steps":42,"duration_seconds":12.3}
```

## Timing Modes

WarGames has two timing modes:

| Mode | How frames and actions work | Use it for |
|---|---|---|
| Sampled | WarGames sends one observation, waits for one turn, applies one event or an event array, then sends the next observation. The game is still running while the model thinks, so the effective FPS depends on model latency. | Normal subprocess agents and most LLM/VLM agents. |
| Streaming | WarGames pushes frames at a fixed FPS. The model can keep reading frames and send event arrays back whenever it is ready. | Realtime models that watch continuously and act asynchronously. |

```text
SAMPLED  -  one frame in, one turn out, repeat

  time      WarGames                            Agent
  ----      --------                            -----
  0.00 s    frame 0  ----------------------->   [think 0.42 s]
  0.42 s    apply    <-----  turn 0     <-----
            frame 1  ----------------------->   [think 0.39 s]
  0.81 s    apply    <-----  turn 1     <-----
            frame 2  ----------------------->          ...

  Effective FPS = 1 / model_latency.
  The game keeps ticking while the model thinks.


STREAMING  -  server pushes frames at fixed FPS, agent acts asynchronously

  time      WarGames                            Agent
  ----      --------                            -----
  0.00 s    frame 0  ----------------------->   |
  0.10 s    frame 1  ----------------------->   |  buffering frames
  0.20 s    frame 2  ----------------------->   |
  0.30 s    frame 3  ----------------------->   |
            apply    <-----  events A   <-----  *  agent decides to act
  0.40 s    frame 4  ----------------------->   |
  0.50 s    frame 5  ----------------------->   |  thinking in parallel
            apply    <-----  events B   <-----  *  with incoming frames
  0.60 s    frame 6  ----------------------->        ...

  Frame cadence is fixed by --fps.
  Actions are async; the world never waits for the agent.
```

`wargames run --agent ...` always uses sampled mode. Your subprocess can be a
plain blocking Python script - no async required.

Streaming is a separate runtime that runs over WebSocket. A streaming client
opens a session, subscribes to frame events, keeps its own latest-frame
buffer, and sends `act` messages with one or more events whenever it decides
to act. The world keeps moving while the model thinks, so the agent has to
handle stale observations.

Run the WebSocket server:

```bash
pip install -e '.[server]'
wargames serve --game redalert --port 8000
```

Streaming client:

```python
import asyncio
import json

import websockets


async def main():
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        await ws.send(json.dumps({
            "op": "create_session",
            "mission": "redalert.soviet-01.normal",
            "mode": "streaming",
        }))
        created = json.loads(await ws.recv())
        session_id = created["session_id"]

        await ws.send(json.dumps({"op": "subscribe_frames", "session_id": session_id, "fps": 10}))

        frames_seen = 0
        while True:
            event = json.loads(await ws.recv())
            if event["event"] == "frame":
                frames_seen += 1
                if frames_seen % 10 == 0:
                    await ws.send(json.dumps({
                        "op": "act",
                        "session_id": session_id,
                        "events": [{"name": "wait", "arguments": {}}],
                    }))
            elif event["event"] == "action_result" and (event["finished"] or event["truncated"]):
                break


asyncio.run(main())
```

In WebSocket mode, frame events are only frames. Mission-end status comes back
on the next `action_result` after an `act` call:

```json
{"event":"action_result","finished":true,"truncated":false}
```

The full streaming example is in
[`examples/agents/streaming_ws_client.py`](examples/agents/streaming_ws_client.py).

For a visible control check, this repo ships `circle-mouse`:

```bash
wargames run \
  --game flightgear \
  --mission flightgear.c172p.tutorial.takeoff \
  --agent circle-mouse \
  --record full
```

## Prime RL

The Prime Intellect Verifiers adapter is `layerbrain/wargames`. Prime configs
live under `environments/prime/configs/<game>/`.

```bash
uv pip install -e ./environments/prime

prime eval run wargames \
  --config environments/prime/configs/freeciv/eval-earth-small.toml \
  -n 1 -r 1
```

| Game | Eval config | RL config |
|---|---|---|
| Red Alert | `environments/prime/configs/redalert/eval-soviet-01.toml` | `environments/prime/configs/redalert/rl-soviet-01.toml` |
| FlightGear | `environments/prime/configs/flightgear/eval-c172p-takeoff.toml` | `environments/prime/configs/flightgear/rl-c172p-takeoff.toml` |
| SuperTuxKart | `environments/prime/configs/supertuxkart/eval-lighthouse.toml` | `environments/prime/configs/supertuxkart/rl-lighthouse.toml` |
| 0 A.D. | `environments/prime/configs/zeroad/eval-arcadia.toml` | `environments/prime/configs/zeroad/rl-arcadia.toml` |
| Freeciv | `environments/prime/configs/freeciv/eval-earth-small.toml` | `environments/prime/configs/freeciv/rl-earth-small.toml` |

The `reward_profile` TOML field is the RL behavior dial - point it at any
profile under `scenarios/<game>/profiles/` (or a custom one). Set
`recorder_mode = "none"` for fast rollouts and `max_steps` to bound the
episode.

## Recording

```bash
wargames run \
  --game redalert \
  --mission redalert.soviet-01.normal \
  --agent scripted-wait \
  --record full \
  --video frames

wargames export <run-id> --out exports --video mp4
```

`--record summary_only` keeps just the run summary. `--record full` keeps
every observation, action, and reward breakdown. `--video frames` writes one
PNG per step; `wargames export ... --video mp4` stitches them.

## Tests

```bash
source venv/bin/activate
python -m unittest discover
```
