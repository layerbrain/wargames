from __future__ import annotations

import asyncio
import os
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Iterable

from wargames.core.control.events import (
    InputEvent,
    KeyEvent,
    MouseEvent,
    ScrollEvent,
    Target,
    WaitEvent,
    x11_button,
)
from wargames.core.control.keys import x11_key_name
from wargames.core.errors import DependencyMissing


class InputInjector(ABC):
    @abstractmethod
    async def send(self, target: Target, event: InputEvent) -> None: ...

    async def send_many(self, target: Target, events: Iterable[InputEvent]) -> None:
        for event in events:
            await self.send(target, event)


class RecordingInjector(InputInjector):
    def __init__(self) -> None:
        self.events: list[tuple[Target, InputEvent]] = []

    async def send(self, target: Target, event: InputEvent) -> None:
        self.events.append((target, event))


def _x11_keysym(key: str) -> int:
    from Xlib import XK  # type: ignore[import-not-found]

    name = x11_key_name(key)
    keysym = XK.string_to_keysym(name)
    if keysym == 0 and len(key) == 1:
        keysym = ord(key)
    if keysym == 0:
        raise ValueError(f"unknown X11 key: {key}")
    return int(keysym)


def _x11_window_id(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return int(value, 0)


class XTestInjector(InputInjector):
    async def send(self, target: Target, event: InputEvent) -> None:
        if isinstance(event, WaitEvent):
            await asyncio.sleep(event.ms / 1000)
            return
        try:
            from Xlib import X, display  # type: ignore[import-not-found]
            from Xlib.ext import xtest  # type: ignore[import-not-found]
        except Exception as exc:
            raise DependencyMissing("python-xlib is required for Linux XTEST injection") from exc
        disp = display.Display(target.display)
        try:
            root = disp.screen().root
            if isinstance(event, MouseEvent):
                if event.kind == "move":
                    if event.x is None or event.y is None:
                        raise ValueError("move mouse events require x and y")
                    xtest.fake_input(disp, X.MotionNotify, x=event.x, y=event.y, root=root)
                else:
                    await asyncio.sleep(0.02)
                    kind = X.ButtonPress if event.kind == "down" else X.ButtonRelease
                    xtest.fake_input(disp, kind, x11_button(event.button), root=root)
                disp.sync()
                return
            if isinstance(event, KeyEvent):
                code = disp.keysym_to_keycode(_x11_keysym(event.key))
                kind = X.KeyPress if event.kind == "down" else X.KeyRelease
                xtest.fake_input(disp, kind, code)
                disp.sync()
                return
            if isinstance(event, ScrollEvent):
                button = 4 if event.dy > 0 else 5
                for _ in range(abs(event.dy)):
                    xtest.fake_input(disp, X.ButtonPress, button, root=root)
                    xtest.fake_input(disp, X.ButtonRelease, button, root=root)
                disp.sync()
        finally:
            disp.close()


class XdotoolInjector(InputInjector):
    async def send(self, target: Target, event: InputEvent) -> None:
        if isinstance(event, WaitEvent):
            await asyncio.sleep(event.ms / 1000)
            return
        window = str(target.window_id) if target.window_id is not None else None
        env = None
        if target.display:
            env = os.environ.copy()
            env["DISPLAY"] = target.display
        if isinstance(event, MouseEvent):
            if event.kind == "move":
                if event.x is None or event.y is None:
                    raise ValueError("move mouse events require x and y")
                cmd = ["xdotool", "mousemove", str(event.x), str(event.y)]
            else:
                action = "mousedown" if event.kind == "down" else "mouseup"
                cmd = ["xdotool", action, str(x11_button(event.button))]
                if window is not None:
                    cmd[2:2] = ["--window", window]
        elif isinstance(event, KeyEvent):
            action = "keydown" if event.kind == "down" else "keyup"
            cmd = ["xdotool", action, x11_key_name(event.key)]
            if window is not None:
                cmd[2:2] = ["--window", window]
        elif isinstance(event, ScrollEvent):
            cmd = ["xdotool", "click", "4" if event.dy > 0 else "5"]
            if window is not None:
                cmd[2:2] = ["--window", window]
        else:
            return
        await asyncio.to_thread(subprocess.run, cmd, check=True, env=env)
