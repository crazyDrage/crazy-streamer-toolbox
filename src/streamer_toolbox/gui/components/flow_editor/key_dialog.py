from nicegui import ui

from streamer_toolbox.connections.keyboard.browser_key import BrowserKey
from streamer_toolbox.connections.keyboard.key_name import ORDER, KeyName
from streamer_toolbox.gui.components.keep_typed import keep_typed

MODIFIER_TITLES = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}
KEYS = [*(f"f{n}" for n in range(1, 25)), *"abcdefghijklmnopqrstuvwxyz", *"0123456789", "space", "enter", "esc",
        "tab", "backspace", "delete", "insert", "home", "end", "page_up", "page_down", "up", "down", "left",
        "right", "caps_lock", "num_lock", "scroll_lock", "print_screen", "pause", "menu", "media_play_pause",
        "media_next", "media_previous", "media_volume_mute", "media_volume_up", "media_volume_down"]
# the next key pressed on the page goes to the element as a "tbkey" event; the page itself doesn't act on it
LISTEN = """(() => {
    const target = getHtmlElement(%d);
    const once = (e) => {
        if (["Control", "Shift", "Alt", "Meta", "AltGraph"].includes(e.key)) return;
        e.preventDefault();
        e.stopPropagation();
        window.removeEventListener("keydown", once, true);
        target.dispatchEvent(new CustomEvent("tbkey", {detail: {
            code: e.code, key: e.key, ctrl: e.ctrlKey, alt: e.altKey, shift: e.shiftKey, win: e.metaKey}}));
    };
    window.addEventListener("keydown", once, true);
})()"""


class KeyDialog:
    """The window that picks the key of a Key trigger: tick Ctrl / Alt / Shift / Win and pick the key from a
    list, or press "Press the key" and then the key itself (with what is held down). The page only listens for
    one key after that button, so typing elsewhere is never read."""

    def __init__(self, current: str) -> None:
        self._held, self._base = KeyName.parts(current)

    async def pick(self) -> str | None:
        """Opens the window; the key's name ("ctrl+shift+k"), or None when it was closed without Use."""
        with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-3"):
            ui.label("Which key starts the flow").classes("text-lg font-semibold")
            self._name = ui.label().classes("font-mono text-base text-primary")
            ui.label("Choose it").classes("text-sm font-semibold")
            with ui.row().classes("items-center gap-4"):
                self._ticks = {m: ui.checkbox(title, value=m in self._held, on_change=self._show).props("dense")
                               for m, title in MODIFIER_TITLES.items()}
            self._key = ui.select(list(dict.fromkeys([*KEYS, *([self._base] if self._base else [])])),
                                  value=self._base or None, label="Key", with_input=True,
                                  new_value_mode="add-unique", on_change=self._show) \
                .props("outlined dense options-dense").classes("w-full")
            keep_typed(self._key)
            ui.separator()
            ui.label("Or press it").classes("text-sm font-semibold")
            with ui.row().classes("items-center gap-3") as catcher:
                self._listen = ui.button("Press the key", icon="keyboard", on_click=lambda: self._wait(catcher)) \
                    .props("no-caps outline")
                self._hint = ui.label("Click the button, then press the key (also with Ctrl, Alt, Shift).") \
                    .classes("text-xs opacity-70")
            catcher.on("tbkey", lambda e: self._pressed(e.args.get("detail") or {}), args=["detail"])
            ui.label("The key works in every window on this PC, not only here. A single letter or digit "
                     "without Ctrl / Alt / Win is not read (that is typing).").classes("text-xs opacity-60")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat no-caps")
                ui.button("Use", on_click=lambda: dialog.submit(self._chosen() or None)).props("unelevated no-caps")
            self._show()
        result = await dialog
        dialog.delete()
        return result

    def _chosen(self) -> str:
        base = str(self._key.value or "").strip().lower()
        return KeyName.join([m for m, tick in self._ticks.items() if tick.value], base) if base else ""

    def _show(self) -> None:
        self._name.set_text(self._chosen() or "no key yet")

    def _wait(self, catcher: ui.element) -> None:
        self._listen.props("color=warning")
        self._hint.set_text("Press the key now…")
        ui.run_javascript(LISTEN % catcher.id)

    def _pressed(self, key: dict) -> None:
        self._listen.props(remove="color")
        base = BrowserKey.base(str(key.get("code") or ""), str(key.get("key") or ""))
        if not base:
            self._hint.set_text("That key has no name here. Press it with Connections → Keyboard open: its "
                                "name shows there as Last special key, and you can type it into Key.")
            return
        self._hint.set_text("Got it. Press the button again for another key.")
        for modifier in ORDER:
            self._ticks[modifier].set_value(bool(key.get(modifier)))
        if base not in self._key.options:
            self._key.set_options([*self._key.options, base])
        self._key.set_value(base)
        self._show()
