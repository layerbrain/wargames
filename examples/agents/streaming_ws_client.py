from __future__ import annotations

import argparse
import asyncio
import json


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://127.0.0.1:8000/ws")
    parser.add_argument("--mission", default="redalert.soviet-01.normal")
    args = parser.parse_args()

    try:
        import websockets
    except Exception as exc:
        raise SystemExit("install the server extra first: pip install -e '.[server]'") from exc

    async with websockets.connect(args.url) as ws:
        await ws.send(
            json.dumps({"op": "create_session", "mission": args.mission, "mode": "streaming"})
        )
        created = json.loads(await ws.recv())
        session_id = created["session_id"]

        await ws.send(json.dumps({"op": "subscribe_frames", "session_id": session_id, "fps": 10}))

        frames_seen = 0
        while True:
            event = json.loads(await ws.recv())
            if event["event"] == "frame":
                frames_seen += 1
                if frames_seen % 10 == 0:
                    await ws.send(
                        json.dumps(
                            {
                                "op": "act",
                                "session_id": session_id,
                                "events": [{"name": "wait", "arguments": {}}],
                            }
                        )
                    )
            elif event["event"] == "action_result" and (event["finished"] or event["truncated"]):
                break


if __name__ == "__main__":
    asyncio.run(main())
