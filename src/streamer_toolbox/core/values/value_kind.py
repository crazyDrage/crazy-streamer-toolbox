from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValueKind:
    """A kind of value a box field can hold, by name: "color", "file", "number", or a special one a connection
    or plugin adds ("obs.scene"). It says how the field is typed in the box form and what is sent.

    `annotation` is the Python type the form goes by (text field, number field, switch) and `default` what an
    empty field holds. `extra` names the box extra the field gets (a RegisteredAction keyword: "colors",
    "files", "options", "many", "editors") and `setting` what that extra gets for the field (the file endings,
    the provider of the choices, the editor's kind). `parse` turns the field's value into what is sent (JSON
    text into a list); it raises ValueError when the value doesn't fit."""

    name: str
    title: str
    annotation: Any = str
    default: Any = ""
    extra: str = ""
    setting: Any = None
    parse: Callable[[Any], Any] | None = None

    def sent(self, value: Any) -> Any:
        """The field's value as the program gets it."""
        return self.parse(value) if self.parse is not None else value
