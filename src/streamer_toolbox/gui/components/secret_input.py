from pathlib import Path

from nicegui import ui

from streamer_toolbox.core.connections.secret_file import SecretFile


class SecretInput:
    """The field on a connection's tab for its token, key, password or secret address: typed (or pasted) here
    and saved with its button, into the connection's own file (SecretFile). What is saved is never shown
    again, only that there is one. An empty field saved takes it away.

    After a save the connection still runs with the old one: the line below says to press Connect."""

    def __init__(self, secret: SecretFile | Path, label: str, what: str = "",
                 saved: str = "Saved. Press Connect to use it.") -> None:
        self._secret = secret if isinstance(secret, SecretFile) else SecretFile(secret, what or label.lower())
        self._saved = saved  # the note after a save (a plugin's key is used at once: "Saved.")
        with ui.row().classes("items-center no-wrap gap-2 w-full"):
            self._field = ui.input(label, password=True, password_toggle_button=True) \
                .props("dense outlined autocomplete=new-password").classes("flex-1")
            ui.button("Save", icon="key", on_click=self._save).props("no-caps unelevated dense")
        self._state = ui.label(self._text()).classes("text-xs opacity-70")

    def _text(self) -> str:
        return ("One is saved (not shown). Type a new one to replace it." if self._secret.read_or_empty()
                else "None saved yet.")

    def _save(self) -> None:
        self._secret.write(self._field.value or "")
        self._field.value = ""
        self._state.set_text(self._text())
        ui.notify(self._saved if self._secret.read_or_empty() else "Taken away.",
                  type="positive")
