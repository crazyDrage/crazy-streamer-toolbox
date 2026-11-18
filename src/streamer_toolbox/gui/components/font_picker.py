from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.fonts.kept_font import KeptFont

ALL_DEVICES, THIS_MACHINE = "🌐", "🖥"  # his 11-18: a symbol for "all devices" / "on this machine only"


class FontPicker:
    """The font field of every text (widget designer, event lists, alerts; his 11-18): the toolbox's fonts
    (Settings → Fonts), each marked 🌐 all devices or 🖥 on this machine only, plus the one the text has now. A
    name can still be typed (a font of this PC the list doesn't have yet: no mark).

    `source` is set once at start (the assembly: FontLibrary.fonts), so every field reaches the same list."""

    source: Callable[[], list[KeptFont]] = staticmethod(lambda: [])

    @classmethod
    def build(cls, value: str, on_change: Callable[[str], None], label: str = "Font",
              empty: str = "") -> ui.select:
        """empty: what no font means (shown as the empty choice), e.g. "The overlay's own"."""
        options = {font.family: f"{ALL_DEVICES if font.everywhere else THIS_MACHINE}  {font.family}"
                   for font in cls.source()}
        if empty:
            options = {"": empty, **options}
        if value and value not in options:
            options[value] = value
        return ui.select(options, value=value, label=label, new_value_mode="add-unique",
                         on_change=lambda e: on_change(str(e.value or ""))) \
            .props("use-input input-debounce=0") \
            .tooltip(f"{ALL_DEVICES} all devices (hosted by the toolbox) · {THIS_MACHINE} on this machine only. "
                     "Settings → Fonts adds more")
