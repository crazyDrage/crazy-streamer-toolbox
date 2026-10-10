from collections.abc import Callable

from nicegui import ui


class FolderField:
    """A folder name: opens the list of folders to pick from, and whatever is typed counts too (no Enter needed,
    a plain select only takes a new name after Enter). `value` is the folder ("" = none).

    How: the select shows the chosen folder as its input text (fill-input), so typing edits it, and what's typed
    while the field has focus is the value right away (a dialog's Move may close it before the blur arrives).
    Leaving the field keeps the typed text in the select; the browser then puts the old text back into the input,
    and that echo comes after the blur, so it's ignored. Text that arrives without focus (when it's drawn) too."""

    def __init__(self, folders: list[str], value: str = "", label: str = "Folder",
                 on_change: Callable[[str], None] | None = None) -> None:
        self._folders = list(folders)
        self.value = value
        self._label = label
        self._on_change = on_change
        self._typed: str | None = None  # the input's text while it has focus; None = not editing
        self._select: ui.select | None = None

    def build(self) -> ui.select:
        options = self._folders + ([self.value] if self.value and self.value not in self._folders else [])
        self._select = ui.select(options, value=self.value or None, label=self._label, with_input=True,
                                 new_value_mode="add-unique", clearable=True) \
            .props("hide-selected fill-input input-debounce=0 outlined dense options-dense")
        self._select.on("focus", lambda: setattr(self, "_typed", self.value))
        self._select.on("input-value", self._input)
        self._select.on("blur", self._commit)
        self._select.on_value_change(lambda e: self._set(e.value or ""))
        return self._select

    def _input(self, e) -> None:
        if self._typed is not None:  # typed while focused (the echo after a blur doesn't count)
            self._typed = e.args if isinstance(e.args, str) else ""
            self._set(self._typed)

    def _commit(self) -> None:
        """Keeps a typed name in the select too, so it still shows after leaving the field."""
        self._typed = None
        if self.value and self.value not in self._select.options:
            self._select.set_options([*self._select.options, self.value])
        if (self._select.value or "") != self.value:
            self._select.set_value(self.value or None)

    def _set(self, text: str) -> None:
        if text.strip() != self.value:
            self.value = text.strip()
            if self._on_change:
                self._on_change(self.value)
