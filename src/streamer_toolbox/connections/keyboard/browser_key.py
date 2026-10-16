NAMED = {"Space": "space", "Enter": "enter", "NumpadEnter": "enter", "Escape": "esc", "Tab": "tab",
         "Backspace": "backspace", "Delete": "delete", "Insert": "insert", "Home": "home", "End": "end",
         "PageUp": "page_up", "PageDown": "page_down", "ArrowUp": "up", "ArrowDown": "down", "ArrowLeft": "left",
         "ArrowRight": "right", "CapsLock": "caps_lock", "NumLock": "num_lock", "ScrollLock": "scroll_lock",
         "PrintScreen": "print_screen", "Pause": "pause", "ContextMenu": "menu",
         "MediaPlayPause": "media_play_pause", "MediaTrackNext": "media_next",
         "MediaTrackPrevious": "media_previous", "AudioVolumeMute": "media_volume_mute",
         "VolumeMute": "media_volume_mute", "AudioVolumeUp": "media_volume_up", "VolumeUp": "media_volume_up",
         "AudioVolumeDown": "media_volume_down", "VolumeDown": "media_volume_down"}


class BrowserKey:
    """A key as a browser's keydown event tells it (its `code` and `key`), under the name a flow trigger writes
    (KeyName, the names the keyboard listener gives): KeyK → "k", Digit5 → "5", F23 → "f23", ArrowUp → "up"."""

    @staticmethod
    def base(code: str, key: str) -> str:
        """The key's name without modifiers, or "" for one this list doesn't know (the number pad, a key only
        some keyboards have): its name shows under Connections → Keyboard when it is pressed."""
        if code in NAMED:
            return NAMED[code]
        if len(code) == 4 and code.startswith("Key"):
            return code[3].lower()
        if len(code) == 6 and code.startswith("Digit"):
            return code[5]
        if code[:1] == "F" and code[1:].isdigit():
            return code.lower()
        if code.startswith("Numpad"):
            return ""
        return key.lower() if len(key) == 1 and key.isprintable() and key != " " else ""
