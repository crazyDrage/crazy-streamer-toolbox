from typing import Any

MODIFIERS = {"ctrl": "ctrl", "ctrl_l": "ctrl", "ctrl_r": "ctrl", "alt": "alt", "alt_l": "alt", "alt_r": "alt",
             "alt_gr": "alt", "shift": "shift", "shift_l": "shift", "shift_r": "shift", "cmd": "win",
             "cmd_l": "win", "cmd_r": "win"}
ORDER = ("ctrl", "alt", "shift", "win")


class KeyName:
    """Names for keys the way a flow trigger writes them: "f23", "space", "a", "ctrl+shift+k". Works on pynput's
    key objects (a Key with .name, or a KeyCode with .char / .vk) without importing pynput."""

    @staticmethod
    def modifier(key: Any) -> str:
        """"ctrl" / "alt" / "shift" / "win" for a modifier key, else ""."""
        return MODIFIERS.get(getattr(key, "name", "") or "", "")

    @staticmethod
    def base(key: Any) -> str:
        name = getattr(key, "name", None)
        if name:  # a special key: f1..f24, space, enter, media_play_pause, ...
            return name
        vk = getattr(key, "vk", None)
        if isinstance(vk, int) and (0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A):  # digits and letters, also with ctrl
            return chr(vk).lower()
        char = getattr(key, "char", None)
        if char and char.isprintable():
            return char.lower()
        return f"vk{vk}" if vk is not None else "unknown"

    @classmethod
    def of(cls, key: Any, held: set[str]) -> str:
        """The full name with the modifiers held down, in a fixed order: "ctrl+alt+shift+win+<key>"."""
        return cls.join(held, cls.base(key))

    @staticmethod
    def join(held: list[str] | set[str], base: str) -> str:
        """"ctrl+shift+k" from the modifiers and the key, the modifiers in the fixed order."""
        return "+".join([m for m in ORDER if m in held] + [base])

    @staticmethod
    def parts(name: str) -> tuple[list[str], str]:
        """The other way round: "ctrl+shift+k" → (["ctrl", "shift"], "k"); the key "+" itself stays whole."""
        text = name.strip().lower()
        held = []
        while "+" in text[:-1] and text.split("+", 1)[0] in ORDER:
            modifier, text = text.split("+", 1)
            held.append(modifier)
        return [m for m in ORDER if m in held], text

    @staticmethod
    def is_text(name: str) -> bool:
        """A single printable character without modifiers: what typing produces (never shown or logged)."""
        return len(name) == 1
