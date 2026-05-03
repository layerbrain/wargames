from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioChunk:
    id: str
    captured_tick: int
    sample_rate: int
    channels: int
    sample_width: int
    duration_seconds: float
    audio_path: str | None = None
    audio_b64: str | None = None
    mime: str = "audio/x-raw;format=S16LE"


class NullAudioCapture:
    async def capture(self, *, tick: int) -> AudioChunk | None:
        return None


class FileAudioCapture:
    def __init__(
        self,
        path: str | Path,
        *,
        sample_rate: int = 48_000,
        channels: int = 2,
        sample_width: int = 2,
        max_chunk_bytes: int | None = None,
    ) -> None:
        self.path = Path(path)
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.max_chunk_bytes = max_chunk_bytes or self.bytes_per_second
        self._offset = 0

    def reset(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.unlink(missing_ok=True)
        self._offset = 0

    async def capture(self, *, tick: int) -> AudioChunk | None:
        if not self.path.exists():
            return None
        size = self.path.stat().st_size
        if size <= self._offset:
            return None
        start = self._offset
        if size - start > self.max_chunk_bytes:
            start = size - self.max_chunk_bytes
        with self.path.open("rb") as handle:
            handle.seek(start)
            data = handle.read(size - start)
        self._offset = size
        if not data:
            return None
        return AudioChunk(
            id=f"audio-{tick}",
            captured_tick=tick,
            sample_rate=self.sample_rate,
            channels=self.channels,
            sample_width=self.sample_width,
            duration_seconds=len(data) / self.bytes_per_second,
            audio_b64=base64.b64encode(data).decode(),
        )

    @property
    def bytes_per_second(self) -> int:
        return self.sample_rate * self.channels * self.sample_width
