# Realtime

The Python-side step path is designed to stay below 16ms:

- idempotency lookup: dictionary access
- CUA lowering: pure function
- injection: XTEST into a dedicated Xvfb display
- probe: socket `readexactly` + msgpack
- rewards: pure functions over adjacent hidden snapshots

OpenRA's own 25 ticks per second is the floor for Red Alert missions.

The watch path uses `ffplay` + `x11grab` against the same Xvfb display with
mouse drawing enabled. That stream is for humans; it does not change the
agent-facing observation boundary.
