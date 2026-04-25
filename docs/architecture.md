# WarGames Architecture

WarGames is a primitive game environment runtime. Core owns universal CUA
actions, process/capture/input plumbing, mission specs, typed results, lobby
state, and WebSocket transport. Game packages own process launch, window lookup,
probes, world types, mission discovery, and any game-specific lobby topology.

## Boundaries

- `Observation` is pixels only: `frame: Frame | None`.
- `StepResult` is the trusted Python result: action, tick, frame, hidden
  snapshot, previous hidden snapshot, finished/truncated flags, and info.
- Hidden state is never serialized on the WebSocket.
- Rewards are evaluator-side utilities, not runtime/session state.
- The CLI has primitive commands only: `missions`, `boot`, `control`, `serve`.
- Test doubles are injected by tests; production config has no fake mode.

## Core Layout

```text
wargames/core/
  backend/
  capture/
  control/
  missions/
  process/
  runtime/
  transport/ws/
  world/
```

`core/control/cua.py` defines the universal action dataclasses. `core/control/tools.py`
defines the universal CUA tool schema and strict parser used by transports and
harnesses.

## Red Alert

Red Alert lives under `wargames/games/redalert/`.

- `backend.py` launches OpenRA, wires input/capture/probe, and returns primitive
  observations/results.
- `missions.py` discovers OpenRA campaign and skirmish maps.
- `catalog.py` defines curated mission suites.
- `lobby.py` manages 2-8 player lobby setup and readiness.
- `openra/` contains the C# state-export trait and build patch.

OpenRA is launched windowed with a fixed size. Linux correctness uses Xvfb +
XTEST, so the visible pointer is the virtual Xvfb pointer, not the user's real
desktop cursor.

## Mission Catalog

WarGames normalizes difficulty to:

```text
easy, normal, hard, extra_hard
```

Games only emit levels they actually support. Red Alert currently emits
`easy`, `normal`, and `hard` for campaign missions that expose those native map
options; skirmish maps default to `normal`.

Extraction writes JSON manifests under:

```text
scenarios/redalert/missions/easy/
scenarios/redalert/missions/normal/
scenarios/redalert/missions/hard/
scenarios/redalert/missions/extra_hard/
```

## WebSocket Modes

`sampled`: the world keeps running. `observe` samples the latest frame, and
`act` applies one action then returns an `action_result`.

`streaming`: the world keeps running and `subscribe_frames` pushes frame events
at the requested FPS. `act` can be sent asynchronously while frames stream.

## Verification

Fast checks:

```bash
source venv/bin/activate
python -m unittest discover -v
```

Manual live checks:

```bash
wargames boot --game redalert --mission redalert.soviet-01.normal --watch
printf '%s\n' '{"name":"wait","arguments":{}}' | \
  wargames control --game redalert --mission redalert.soviet-01.normal --actions -
wargames serve --game redalert --port 8000
```
