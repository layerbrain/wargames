# Rewards

WarGames keeps reward computation outside the runtime. `Rubric` and
`RubricEntry` remain available as evaluator utilities: each entry receives the
previous and current hidden snapshots and returns a scalar. WebSocket clients
receive only frames and action results; hidden state and reward attribution stay
in trusted in-process harnesses.
