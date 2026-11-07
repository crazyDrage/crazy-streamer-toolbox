from collections.abc import Callable

from nicegui import ui


class AccountPicker:
    """Which accounts may start a trigger (his plan of 2026-11-05, answer 120): a dropdown with one checkbox per
    account that listens; nothing ticked = every one of them. Its button says what is ticked. Shown only when
    more than one account listens, or when the trigger names accounts already (rule 29)."""

    def __init__(self, accounts: list[str], picked: list[str],
                 on_change: Callable[[list[str]], None] | None = None,
                 labels: dict[str, str] | None = None) -> None:
        self.picked = [name for name in picked]
        self._accounts = list(dict.fromkeys([*accounts, *picked]))  # one that stopped listening stays visible
        self._on_change = on_change
        with ui.dropdown_button(self._text(), icon="person", auto_close=False) \
                .props("flat dense no-caps").classes("shrink-0") as self._button:
            with ui.column().classes("gap-0 p-2"):
                for name in self._accounts:
                    label = name if name in accounts else f"{name} (doesn't listen now)"
                    label = (labels or {}).get(name, label)
                    ui.checkbox(label, value=name in self.picked,
                                on_change=lambda e, n=name: self._tick(n, e.value)).props("dense").classes("py-1")
                ui.label("Nothing ticked = every account that listens. Which one heard it is in the trigger's "
                         "\"account\" dot.").classes("text-xs opacity-60 pt-1 max-w-[16rem]")

    def _text(self) -> str:
        return ", ".join(self.picked) if self.picked else "Any account"

    def _tick(self, name: str, on: bool) -> None:
        self.picked = [n for n in self._accounts if (on if n == name else n in self.picked)]
        self._button.set_text(self._text())
        if self._on_change:
            self._on_change(self.picked)
