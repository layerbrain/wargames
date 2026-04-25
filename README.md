# WarGames

WarGames runs games as computer-use environments. A client sees pixels and sends
mouse, keyboard, text, scroll, and wait actions. The first game backend is
OpenRA Red Alert.

WarGames is for local Linux/Xvfb execution. On macOS, the CLI starts the Linux
runtime box for Red Alert and opens a viewer so you can watch the game.

## Install

From the project root:

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[server]"
```

Red Alert needs a working OpenRA source checkout with the WarGames probe
installed. Point WarGames at it:

```bash
export LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT=/path/to/openra-source
export LAYERBRAIN_WARGAMES_REDALERT_OPENRA_BINARY=/path/to/openra-source/launch-game.sh
```

On macOS, Docker must be running. WarGames hides the Docker invocation behind the
CLI.

## List Missions

```bash
wargames missions --game redalert
```

Filter by normalized difficulty:

```bash
wargames missions --game redalert --difficulty normal
```

Extract a visible catalog into difficulty folders:

```bash
wargames missions --game redalert --extract --output scenarios/redalert/missions
```

Difficulty folders are `easy`, `normal`, `hard`, and `extra_hard`. A game only
places missions in difficulties it actually supports.

## Boot And Watch

Start Red Alert and keep the mission running:

```bash
wargames boot --game redalert --mission redalert.soviet-01.normal --watch
```

Use `--no-watch` when you do not need a viewer:

```bash
wargames boot --game redalert --mission redalert.soviet-01.normal --no-watch
```

## Send Actions

`wargames control` reads one JSON tool call per line and returns one JSON result
per line. Coordinates are integer pixels in the 1280x720 game frame.

```bash
printf '%s\n' \
  '{"name":"wait","arguments":{}}' \
  '{"name":"click","arguments":{"x":1246,"y":31}}' \
  '{"name":"click","arguments":{"x":202,"y":376}}' \
| wargames control --game redalert --mission redalert.soviet-01.normal --actions -
```

Supported tools:

- `wait`
- `move_mouse`
- `click`
- `double_click`
- `drag`
- `key`
- `type_text`
- `scroll`

All coordinate arguments must be integers. Normalized floats are rejected.

## WebSocket Server

Start the local WebSocket transport:

```bash
wargames serve --game redalert --host 127.0.0.1 --port 8000
```

Connect to:

```text
ws://127.0.0.1:8000/ws
```

Create a session:

```json
{"op":"create_session","game":"redalert","mission":"redalert.soviet-01.normal","seed":42,"mode":"sampled"}
```

Observe the latest frame:

```json
{"op":"observe","session_id":"..."}
```

Send an action:

```json
{"op":"act","session_id":"...","tool_call":{"name":"click","arguments":{"x":640,"y":360}}}
```

Subscribe to realtime frame pushes:

```json
{"op":"subscribe_frames","session_id":"...","fps":10}
```

Stop frame pushes and delete the session:

```json
{"op":"unsubscribe_frames","session_id":"..."}
{"op":"delete","session_id":"..."}
```

The WebSocket surface returns frames and action results only. Hidden world state
is not serialized over the wire.

## Configuration

Common environment variables:

```bash
export LAYERBRAIN_WARGAMES_XVFB_RESOLUTION=1280x720
export LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE=1280x720
export LAYERBRAIN_WARGAMES_REDALERT_OPENRA_ROOT=/path/to/openra-source
export LAYERBRAIN_WARGAMES_REDALERT_OPENRA_BINARY=/path/to/openra-source/launch-game.sh
export LAYERBRAIN_WARGAMES_REDALERT_OPENRA_SUPPORT_DIR=/tmp/wargames/openra-support
```

The default input path uses `xdotool` inside the Linux/Xvfb runtime because it is
the path verified against OpenRA. `xtest` remains available for environments that
accept native XTEST events:

```bash
export LAYERBRAIN_WARGAMES_INJECTOR_TRANSPORT=xtest
```

## Troubleshooting

If the viewer is black, wait a few seconds for the mission to finish loading.

If OpenRA cannot find Red Alert assets, run the Linux runtime once with network
access. It installs the OpenRA quick-install content into the configured support
directory.

If clicks do not land, check that the frame size matches the coordinate space:

```bash
export LAYERBRAIN_WARGAMES_XVFB_RESOLUTION=1280x720
export LAYERBRAIN_WARGAMES_REDALERT_OPENRA_WINDOW_SIZE=1280x720
```

## Tests

```bash
source venv/bin/activate
python -m unittest discover -v
```
