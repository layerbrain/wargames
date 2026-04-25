from __future__ import annotations

import base64
from pathlib import Path



def frame_base64(frame: object | None) -> str | None:
    if frame is None:
        return None
    image_b64 = getattr(frame, "image_b64", None)
    if image_b64:
        return str(image_b64)
    image_path = getattr(frame, "image_path", None)
    if image_path:
        path = Path(str(image_path))
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode("ascii")
    return None


def frame_data_url(frame: object | None) -> str | None:
    data = frame_base64(frame)
    if data is None:
        return None
    mime = getattr(frame, "mime", "image/png")
    return f"data:{mime};base64,{data}"
