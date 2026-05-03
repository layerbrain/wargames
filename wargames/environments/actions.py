from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCallSpec:
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class GameAction:
    id: str
    tool_calls: tuple[ToolCallSpec, ...]
    description: str = ""


@dataclass(frozen=True)
class ActionSet:
    game: str
    actions: tuple[GameAction, ...]

    def resolve(self, action: int | str) -> GameAction:
        if isinstance(action, bool):
            raise ValueError("action must be an integer index or action id")
        if isinstance(action, int):
            try:
                return self.actions[action]
            except IndexError as exc:
                raise ValueError(f"unknown {self.game} action index: {action}") from exc
        for candidate in self.actions:
            if candidate.id == action:
                return candidate
        raise ValueError(f"unknown {self.game} action id: {action}")

    def ids(self) -> tuple[str, ...]:
        return tuple(action.id for action in self.actions)


def action_set_for(game: str) -> ActionSet:
    try:
        return ACTION_SETS[game]
    except KeyError as exc:
        raise ValueError(f"no action set registered for game: {game}") from exc


def _tool(name: str, **arguments: object) -> ToolCallSpec:
    return ToolCallSpec(name=name, arguments=dict(arguments))


def _wait(ms: int = 100) -> GameAction:
    return GameAction("wait", (_tool("wait", ms=ms),), "Wait without sending input.")


def _tap(id: str, key: str, *, ms: int = 75, description: str = "") -> GameAction:
    return GameAction(
        id,
        (_tool("key_down", key=key), _tool("wait", ms=ms), _tool("key_up", key=key)),
        description,
    )


def _click(id: str, button: str = "left", *, description: str = "") -> GameAction:
    return GameAction(
        id,
        (_tool("mouse_down", button=button), _tool("wait", ms=50), _tool("mouse_up", button=button)),
        description,
    )


def _move_and_click(
    id: str, x: int, y: int, button: str = "left", *, description: str = ""
) -> GameAction:
    return GameAction(
        id,
        (
            _tool("move_mouse", x=x, y=y),
            _tool("mouse_down", button=button),
            _tool("wait", ms=50),
            _tool("mouse_up", button=button),
        ),
        description,
    )


def _scroll(id: str, dx: int, dy: int, *, description: str = "") -> GameAction:
    return GameAction(id, (_tool("scroll", dx=dx, dy=dy),), description)


DOOM_ACTIONS = ActionSet(
    "doom",
    (
        _wait(),
        _tap("forward", "ArrowUp", description="Move forward briefly."),
        _tap("backward", "ArrowDown", description="Move backward briefly."),
        _tap("turn_left", "ArrowLeft", description="Turn left briefly."),
        _tap("turn_right", "ArrowRight", description="Turn right briefly."),
        _tap("fire", "Control", description="Fire the equipped weapon."),
        _tap("use", "Space", description="Use doors and switches."),
    ),
)

SUPERTUX_ACTIONS = ActionSet(
    "supertux",
    (
        _wait(),
        _tap("left", "ArrowLeft", description="Move left briefly."),
        _tap("right", "ArrowRight", description="Move right briefly."),
        _tap("jump", "Space", description="Jump."),
        _tap("duck", "ArrowDown", description="Duck briefly."),
        _tap("action", "Control", description="Run or use the action key."),
    ),
)

MINDUSTRY_ACTIONS = ActionSet(
    "mindustry",
    (
        _wait(),
        _tap("up", "w", description="Move the player up."),
        _tap("down", "s", description="Move the player down."),
        _tap("left", "a", description="Move the player left."),
        _tap("right", "d", description="Move the player right."),
        _click("fire", description="Fire at the current pointer position."),
        _move_and_click("select_center", 640, 360, description="Select the center of the screen."),
        _move_and_click(
            "command_center",
            640,
            360,
            button="right",
            description="Issue a right-click command at the center of the screen.",
        ),
    ),
)

CRAFTIUM_ACTIONS = ActionSet(
    "craftium",
    (
        _wait(),
        _tap("forward", "w", description="Move forward briefly."),
        _tap("backward", "s", description="Move backward briefly."),
        _tap("left", "a", description="Move left briefly."),
        _tap("right", "d", description="Move right briefly."),
        _tap("jump", "Space", description="Jump."),
        _click("use", description="Use the current item."),
        _tap("inventory", "e", description="Open or close inventory."),
    ),
)

IKEMEN_ACTIONS = ActionSet(
    "ikemen",
    (
        _wait(),
        _tap("left", "ArrowLeft", description="Move left."),
        _tap("right", "ArrowRight", description="Move right."),
        _tap("jump", "ArrowUp", description="Jump."),
        _tap("crouch", "ArrowDown", description="Crouch."),
        _tap("punch", "a", description="Punch."),
        _tap("kick", "s", description="Kick."),
        _tap("special", "d", description="Use a special attack button."),
    ),
)

OPENSURGE_ACTIONS = ActionSet(
    "opensurge",
    (
        _wait(),
        _tap("left", "ArrowLeft", description="Move left briefly."),
        _tap("right", "ArrowRight", description="Move right briefly."),
        _tap("jump", "Space", description="Jump."),
        _tap("roll", "ArrowDown", description="Roll or crouch briefly."),
        _tap("look_up", "ArrowUp", description="Look up briefly."),
        _tap("action", "Control", description="Use the action button."),
    ),
)

REDALERT_ACTIONS = ActionSet(
    "redalert",
    (
        _wait(),
        _move_and_click("select_center", 640, 360, description="Select at the center of the screen."),
        _move_and_click(
            "command_center",
            640,
            360,
            button="right",
            description="Issue a right-click command at the center of the screen.",
        ),
        _tap("camera_up", "ArrowUp", description="Pan camera up."),
        _tap("camera_down", "ArrowDown", description="Pan camera down."),
        _tap("camera_left", "ArrowLeft", description="Pan camera left."),
        _tap("camera_right", "ArrowRight", description="Pan camera right."),
    ),
)

FLIGHTGEAR_ACTIONS = ActionSet(
    "flightgear",
    (
        _wait(),
        _tap("pitch_down", "ArrowUp", description="Pitch the nose down briefly."),
        _tap("pitch_up", "ArrowDown", description="Pitch the nose up briefly."),
        _tap("roll_left", "ArrowLeft", description="Roll left briefly."),
        _tap("roll_right", "ArrowRight", description="Roll right briefly."),
        _tap("throttle_up", "PageUp", description="Increase throttle."),
        _tap("throttle_down", "PageDown", description="Decrease throttle."),
        _tap("brake", "b", description="Apply brakes."),
    ),
)

SUPERTUXKART_ACTIONS = ActionSet(
    "supertuxkart",
    (
        _wait(),
        _tap("accelerate", "ArrowUp", description="Accelerate briefly."),
        _tap("brake", "ArrowDown", description="Brake briefly."),
        _tap("left", "ArrowLeft", description="Steer left briefly."),
        _tap("right", "ArrowRight", description="Steer right briefly."),
        _tap("fire", "Space", description="Use the kart item button."),
    ),
)

ZEROAD_ACTIONS = ActionSet(
    "zeroad",
    (
        _wait(),
        _move_and_click("select_center", 640, 360, description="Select at the center of the screen."),
        _move_and_click(
            "command_center",
            640,
            360,
            button="right",
            description="Issue a right-click command at the center of the screen.",
        ),
        _tap("camera_up", "ArrowUp", description="Pan camera up."),
        _tap("camera_down", "ArrowDown", description="Pan camera down."),
        _tap("camera_left", "ArrowLeft", description="Pan camera left."),
        _tap("camera_right", "ArrowRight", description="Pan camera right."),
    ),
)

FREECIV_ACTIONS = ActionSet(
    "freeciv",
    (
        _wait(),
        _move_and_click("select_center", 640, 360, description="Select at the center of the screen."),
        _move_and_click(
            "command_center",
            640,
            360,
            button="right",
            description="Issue a right-click command at the center of the screen.",
        ),
        _tap("end_turn", "Enter", description="End the current turn."),
        _tap("cancel", "Escape", description="Cancel the current selection or dialog."),
    ),
)

ACTION_SETS: dict[str, ActionSet] = {
    action_set.game: action_set
    for action_set in (
        REDALERT_ACTIONS,
        FLIGHTGEAR_ACTIONS,
        SUPERTUXKART_ACTIONS,
        ZEROAD_ACTIONS,
        FREECIV_ACTIONS,
        DOOM_ACTIONS,
        SUPERTUX_ACTIONS,
        MINDUSTRY_ACTIONS,
        CRAFTIUM_ACTIONS,
        IKEMEN_ACTIONS,
        OPENSURGE_ACTIONS,
    )
}


__all__ = ["ACTION_SETS", "ActionSet", "GameAction", "ToolCallSpec", "action_set_for"]
