# WarGames Architecture

WarGames is a game environment runtime. Core owns universal CUA
actions, process/capture/input plumbing, mission specs, typed results, lobby
state, and WebSocket transport. Game packages own process launch, window lookup,
probes, world types, mission discovery, and any game-specific lobby topology.

## Boundaries

- `Observation` carries the public rendered frame: `frame: Frame | None`.
- `StepResult` is the trusted Python result: action, tick, frame, hidden
  snapshot, previous hidden snapshot, finished/truncated flags, and info.
- Hidden state is never serialized on the WebSocket.
- Rewards are evaluator-side utilities, not runtime/session state.
- The CLI exposes runtime commands: `missions`, `boot`, `control`, `serve`.
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

## Game Packages

Each game lives under `wargames/games/<game>/`.

- `backend.py` launches the game, wires input/capture/probe, and returns public
  observations plus trusted step results.
- `missions.py` discovers the shipped game content and exports WarGames missions.
- `profiles.py` loads reward profiles from `scenarios/<game>/profiles/`.
- `process.py` builds the game command and runtime environment.

Games are launched windowed with a fixed size. Linux correctness uses Xvfb +
XTEST, so the visible pointer is the virtual Xvfb pointer, not the user's real
desktop cursor.

## Mission Catalog

WarGames normalizes difficulty to:

```text
easy, normal, hard, extra_hard
```

Games only emit levels they actually support.

Extraction writes JSON manifests under:

```text
scenarios/<game>/missions/easy/
scenarios/<game>/missions/normal/
scenarios/<game>/missions/hard/
scenarios/<game>/missions/extra_hard/
```

## WebSocket Modes

`sampled`: the world keeps running. `observe` samples the latest frame, and
`act` applies one input event or one event array, then returns an `action_result`.

`streaming`: the world keeps running and `subscribe_frames` pushes public output
events at the requested FPS. Each event can include the latest frame and any
captured audio chunk. `act` can be sent asynchronously while output streams.

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
