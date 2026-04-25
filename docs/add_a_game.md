# Add A Game

Add a package under `wargames/games/<name>/` with:

- `backend.py`
- `world.py`
- `missions.py`
- `probe.py`
- `rewards.py`
- optional `process.py`, `window.py`, `lobby.py`, and `transport/`

The game backend accepts `ArenaAction`. Do not add game-specific actions to
core. Game-specific semantics belong in the game's world, mission, probe, and
evaluator utilities.
