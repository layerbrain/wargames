# Probe

Red Alert uses `SocketStateProbe`: a Unix-domain socket with 4-byte big-endian
length prefixes and msgpack payloads. The OpenRA trait connects to
`$PROBE_SOCK`, writes one frame per game tick, and Python decodes each payload
into `RedAlertWorld`.

The probe feeds reward and trace snapshots. Runtime clients use the standard
observation and action protocol.
