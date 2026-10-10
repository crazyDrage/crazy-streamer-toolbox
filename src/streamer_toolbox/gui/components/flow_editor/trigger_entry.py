from dataclasses import dataclass


@dataclass(frozen=True)
class TriggerEntry:
    """One line of the Add trigger window: `match` is the field a trigger of this kind is matched on, `example`
    what that field starts with, `fields` what the event gives a flow (the Start box's orange dots)."""
    kind: str
    icon: str
    title: str
    match: str
    example: str
    group: str
    info: str = ""
    fields: tuple[str, ...] = ()
