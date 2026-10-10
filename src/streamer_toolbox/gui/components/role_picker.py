from collections.abc import Callable

from nicegui import ui

from streamer_toolbox.core.flows.role_match import ROLE_TITLES, ROLES_HELP, roles_text


class RolePicker:
    """Who may start a trigger: a dropdown with one checkbox per role (plain viewers, subs, VIPs, mods, you).
    Its button says what is ticked ("Everyone", "VIPs, Mods"). `on_change` gets the ticked roles."""

    def __init__(self, roles: list[str], on_change: Callable[[list[str]], None] | None = None,
                 note: str = "") -> None:
        self.roles = list(roles)
        self._on_change = on_change
        with ui.dropdown_button(roles_text(self.roles), icon="groups", auto_close=False) \
                .props("flat dense no-caps").classes("shrink-0") as self._button:
            with ui.column().classes("gap-0 p-2"):
                for role, title in ROLE_TITLES.items():
                    ui.checkbox(title, value=role in self.roles,
                                on_change=lambda e, r=role: self._tick(r, e.value)).props("dense").classes("py-1")
                # the help stands in the list, not in a tooltip: a tooltip would lie over the checkboxes
                ui.label(f"Nothing ticked = everyone. {ROLES_HELP} {note}".strip()) \
                    .classes("text-xs opacity-60 pt-1 max-w-[16rem]")

    def _tick(self, role: str, on: bool) -> None:
        self.roles = [r for r in ROLE_TITLES if (on if r == role else r in self.roles)]
        self._button.set_text(roles_text(self.roles))
        if self._on_change:
            self._on_change(self.roles)
