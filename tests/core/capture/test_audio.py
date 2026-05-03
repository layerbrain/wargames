from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from wargames.core.capture.audio import FileAudioCapture, NullAudioCapture


class AudioCaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_null_audio_capture_returns_no_public_audio(self) -> None:
        self.assertIsNone(await NullAudioCapture().capture(tick=1))

    async def test_file_audio_capture_returns_new_bytes_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "game.pcm"
            capture = FileAudioCapture(path, sample_rate=4, channels=1, sample_width=1)
            capture.reset()
            path.write_bytes(b"abcd")

            first = await capture.capture(tick=3)
            second = await capture.capture(tick=4)

        assert first is not None
        self.assertEqual("audio-3", first.id)
        self.assertEqual(1.0, first.duration_seconds)
        self.assertEqual(base64.b64encode(b"abcd").decode(), first.audio_b64)
        self.assertIsNone(second)

    async def test_file_audio_capture_keeps_latest_window_when_buffer_is_large(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "game.pcm"
            capture = FileAudioCapture(path, sample_rate=4, channels=1, sample_width=1, max_chunk_bytes=3)
            capture.reset()
            path.write_bytes(b"abcdef")

            chunk = await capture.capture(tick=5)

        assert chunk is not None
        self.assertEqual(base64.b64encode(b"def").decode(), chunk.audio_b64)
