"""Which connections this copy of the toolbox leaves out, and what goes with them.

LEFT_OUT names connections that are left out always (none today). A connection that is left out gets no tab,
no boxes and no triggers; its code and its tests stay.

The same question, "does anything here publish this event?", also hides the triggers of connections that are
switched off (the flow editor), so both are answered here.

A build that only offers what was tested (release_marker) adds to both at start with leave_out(): the
connections and the single triggers nobody has ticked off in the test list yet."""
from collections.abc import Collection

LEFT_OUT: frozenset[str] = frozenset()
_untested: dict[str, frozenset[str]] = {"connections": frozenset(), "triggers": frozenset()}

# an event's first word → who publishes it, where that isn't a connection of the same name
OWNERS = {"heartrate": ("pulsoid", "hyperate"), "key": ("keyboard",)}


def owners(kind: str) -> tuple[str, ...]:
    """The connections (ids, or box categories: "vts") that publish the event `kind`."""
    first = kind.partition(".")[0]
    return OWNERS.get(first, (first,))


def gone(kind: str, missing: Collection[str]) -> bool:
    """True when every connection that could publish `kind` is in `missing`. Events no connection owns
    (timer, custom, tip, follow, ...) are never gone."""
    return all(owner in missing for owner in owners(kind))


def leave_out(connections: Collection[str], triggers: Collection[str] = ()) -> None:
    """Also leaves these connections (ids) and these single triggers (event kinds) out, from now on."""
    _untested["connections"] = frozenset(connections)
    _untested["triggers"] = frozenset(triggers)


def left_out_connections() -> frozenset[str]:
    """The ids of every connection this copy leaves out."""
    return LEFT_OUT | _untested["connections"]


def left_out(kind: str) -> bool:
    """True when this copy of the toolbox has no connection that publishes `kind`, or leaves that trigger out."""
    return kind in _untested["triggers"] or gone(kind, left_out_connections())
