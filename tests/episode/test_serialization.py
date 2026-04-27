from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from unittest import TestCase

from wargames.core.capture.frame import Frame
from wargames.episode.serialization import agent_observation_to_dict
from wargames.evaluation.task import TaskSpec
from wargames.harness.agent import AgentObservation, PublicEvent, ToolCall


class AgentObservationSerializationTests(TestCase):
    def test_agent_observation_exposes_image_b64_not_image_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "frame.png"
            image.write_bytes(b"frame-bytes")
            observation = AgentObservation(
                task=TaskSpec(
                    id="redalert.soviet-01.normal.seed-000000",
                    game="redalert",
                    mission_id="redalert.soviet-01.normal",
                    seed=0,
                ),
                frame=Frame(
                    id="frame-1",
                    width=1280,
                    height=720,
                    captured_tick=1,
                    image_path=str(image),
                ),
                tools=(),
                history=(),
                step_index=0,
                elapsed_seconds=0.0,
            )

            payload = agent_observation_to_dict(observation)

        self.assertEqual(base64.b64encode(b"frame-bytes").decode(), payload["frame"]["image_b64"])
        self.assertNotIn("image_path", payload["frame"])
        self.assertNotIn("tools", payload)

    def test_agent_history_exposes_actions_not_tool_call_field(self) -> None:
        observation = AgentObservation(
            task=TaskSpec(
                id="redalert.soviet-01.normal.seed-000000",
                game="redalert",
                mission_id="redalert.soviet-01.normal",
                seed=0,
            ),
            frame=None,
            tools=(),
            history=(PublicEvent(step=0, tool_call=ToolCall("wait", {}), tick=1),),
            step_index=1,
            elapsed_seconds=0.1,
        )

        payload = agent_observation_to_dict(observation)

        self.assertEqual({"name": "wait", "arguments": {}}, payload["history"][0]["action"])
        self.assertNotIn("tool_call", payload["history"][0])
