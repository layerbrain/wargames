from __future__ import annotations

_LETTERS = set("abcdefghijklmnopqrstuvwxyz")
_DIGITS = set("0123456789")
_SYMBOLS = set("[]-=;',./`\\")
_NAMED_KEYS = {
    "ArrowUp",
    "ArrowDown",
    "ArrowLeft",
    "ArrowRight",
    "Control",
    "Shift",
    "Alt",
    "Meta",
    "PageUp",
    "PageDown",
    "Home",
    "End",
    "Insert",
    "Delete",
    "Enter",
    "Escape",
    "Space",
    "Tab",
    "Backspace",
    *(f"F{index}" for index in range(1, 13)),
}

_X11_KEY_NAMES = {
    "ArrowUp": "Up",
    "ArrowDown": "Down",
    "ArrowLeft": "Left",
    "ArrowRight": "Right",
    "Control": "Control_L",
    "Shift": "Shift_L",
    "Alt": "Alt_L",
    "Meta": "Super_L",
    "PageUp": "Page_Up",
    "PageDown": "Page_Down",
    "Enter": "Return",
    "Escape": "Escape",
    "Space": "space",
}


def normalize_key(key: str) -> str:
    if key in _NAMED_KEYS:
        return key
    if len(key) == 1 and (key in _LETTERS or key in _DIGITS or key in _SYMBOLS):
        return key
    raise ValueError(f"unknown key: {key}")


def x11_key_name(key: str) -> str:
    return _X11_KEY_NAMES.get(normalize_key(key), key)
