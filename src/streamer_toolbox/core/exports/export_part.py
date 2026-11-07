from dataclasses import dataclass

# what can go into an export, in the order the windows list them
KINDS = {"alert": "Alert", "widget": "Widget", "event": "Event", "flow": "Flow", "variable": "Global variable",
         "button": "Live button"}


@dataclass(frozen=True)
class ExportPart:
    """One thing in an export window's list (his round 86: an export with everything connected): an alert (key
    = its id), a widget (its folder name), an event type, a flow (its file name), a global variable or a Live
    button ("<page>/<number>"). `why`: how it is connected to what he picked ("sends the event cheer");
    `ticked`: in the export unless he unticks it. A part that is only offered (a Live button, another alert on
    the same event) starts unticked."""

    kind: str
    key: str
    title: str
    why: str = ""
    ticked: bool = True

    @property
    def id(self) -> tuple[str, str]:
        return self.kind, self.key

    @property
    def label(self) -> str:
        return f"{KINDS.get(self.kind, self.kind)}: {self.title}"
