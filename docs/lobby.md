# Lobby

`Lobby` is the multi-agent abstraction. Core defines the interface; each game
owns the topology.

Red Alert uses one backend session per player slot. Future games can map lobby
sessions to one process per player, one process with multiple input streams, or
turn-dispatched control on a shared surface.
