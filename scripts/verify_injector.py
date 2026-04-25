from __future__ import annotations

import asyncio

from wargames.core.control.cua import ClickAction
from wargames.core.control.events import Target, WindowRect
from wargames.core.control.injector import RecordingInjector
from wargames.core.control.lower import lower_cua


async def main() -> None:
    target = Target(pid=None, window_id=None, rect=WindowRect(10, 20, 800, 600))
    injector = RecordingInjector()
    await injector.send_many(target, lower_cua(ClickAction(id="verify", x=5, y=6), target.rect))
    for _, event in injector.events:
        print(event)


if __name__ == "__main__":
    asyncio.run(main())
