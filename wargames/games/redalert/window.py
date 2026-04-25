from __future__ import annotations

import asyncio
from pathlib import Path

from wargames.core.control.events import Target, WindowRect
from wargames.core.errors import WindowNotFound


async def locate_window(*, pid: int, display: str | None = None, width: int = 1280, height: int = 720) -> Target:
    target = _locate_platform_window(pid=pid, display=display)
    if target is not None:
        return _normalize_target(target, width=width, height=height)
    return Target(pid=pid, window_id=None, rect=WindowRect(x=0, y=0, width=width, height=height), display=display)


async def wait_for_window(
    *,
    pid: int,
    display: str | None = None,
    width: int = 1280,
    height: int = 720,
    timeout: float = 30.0,
) -> Target:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        target = _locate_platform_window(pid=pid, display=display)
        if target is not None:
            return _normalize_target(target, width=width, height=height)
        if asyncio.get_running_loop().time() >= deadline:
            raise WindowNotFound(f"OpenRA window did not appear for pid {pid}")
        await asyncio.sleep(0.05)


def _locate_platform_window(*, pid: int, display: str | None) -> Target | None:
    for candidate in _candidate_pids(pid):
        target = _locate_x11_window(pid=candidate, display=display)
        if target is not None:
            return Target(pid=pid, window_id=target.window_id, rect=target.rect, display=target.display)
    return None


def _candidate_pids(pid: int, proc_root: Path = Path("/proc")) -> tuple[int, ...]:
    seen: set[int] = set()
    ordered: list[int] = []
    stack = [pid]
    while stack:
        current = stack.pop(0)
        if current in seen:
            continue
        seen.add(current)
        ordered.append(current)
        children = proc_root / str(current) / "task" / str(current) / "children"
        try:
            stack.extend(int(value) for value in children.read_text().split())
        except (OSError, ValueError):
            pass
    return tuple(ordered)


def require_window(target: Target) -> Target:
    if target.pid is None:
        raise WindowNotFound("missing pid for OpenRA target")
    return target


def _normalize_target(target: Target, *, width: int, height: int) -> Target:
    expected_area = width * height
    actual_area = target.rect.width * target.rect.height
    if actual_area >= expected_area // 2:
        return target
    return Target(pid=target.pid, window_id=None, rect=WindowRect(x=0, y=0, width=width, height=height), display=target.display)


async def focus_window(target: Target) -> None:
    if target.pid is None:
        return
    await _focus_x11_window(target)


async def _focus_x11_window(target: Target) -> None:
    if target.window_id is None:
        return
    try:
        from Xlib import X, display as xdisplay  # type: ignore[import-not-found]
    except Exception:
        return

    disp = xdisplay.Display(target.display)
    try:
        window = disp.create_resource_object("window", int(target.window_id))
        window.configure(stack_mode=X.Above)
        window.set_input_focus(X.RevertToParent, X.CurrentTime)
        disp.sync()
    except Exception:
        return
    finally:
        disp.close()


def _locate_x11_window(*, pid: int, display: str | None) -> Target | None:
    try:
        from Xlib import display as xdisplay  # type: ignore[import-not-found]
    except Exception:
        return None

    disp = xdisplay.Display(display)
    try:
        atom = disp.intern_atom("_NET_WM_PID")
        root = disp.screen().root
        candidates = _find_x11_windows(root, root, atom, pid)
        if not candidates:
            return None
        window, rect = _largest_window(candidates)
        return Target(pid=pid, window_id=window.id, rect=rect, display=display)
    finally:
        disp.close()


def _largest_window(candidates: list[tuple[object, WindowRect]]) -> tuple[object, WindowRect]:
    return max(candidates, key=lambda item: item[1].width * item[1].height)


def _find_x11_windows(window: object, root: object, atom: int, pid: int) -> list[tuple[object, WindowRect]]:
    found: list[tuple[object, WindowRect]] = []
    try:
        prop = window.get_full_property(atom, 0)  # type: ignore[attr-defined]
        if prop is not None and int(prop.value[0]) == pid:
            geometry = window.get_geometry()  # type: ignore[attr-defined]
            position = window.translate_coords(root, 0, 0)  # type: ignore[attr-defined]
            found.append(
                (
                    window,
                    WindowRect(
                        x=int(position.x),
                        y=int(position.y),
                        width=int(geometry.width),
                        height=int(geometry.height),
                    ),
                )
            )
    except Exception:
        pass
    try:
        children = window.query_tree().children  # type: ignore[attr-defined]
    except Exception:
        return found
    for child in children:
        found.extend(_find_x11_windows(child, root, atom, pid))
    return found
