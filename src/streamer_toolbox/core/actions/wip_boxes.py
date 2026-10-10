"""Boxes that are parked: built, but not doing what they should yet, so the toolbox doesn't offer them.

A parked box is left out of every list (the Add box window, the Live deck's picker, the SAMMI deck, the API's
list). Its code and its tests stay, and a flow that already has it keeps running and keeps showing it.

To see the parked boxes again, add this to config/toolbox.toml and restart. It is not on any screen on purpose:

    [wip]
    show = true

To park a box: add its action name here with the reason. To bring it back: take its line out."""

WIP_BOXES: dict[str, str] = {
    # VTube Studio's ItemPinRequest only pins an item by its middle. He needs the contact point he grabs the
    # item at (temp/requests/vtube_studio/001_pin_contact_point.md). Until VTS can do that, pinning is parked.
    "vts.add_pinned_item": "VTube Studio pins an item only by its middle",
    "vts.pin_item": "VTube Studio pins an item only by its middle",
    "vts.record_pin_spot": "only used by the pin boxes",
    "vts.unpin_item": "only used by the pin boxes",
}


def shows_wip(tables: dict) -> bool:
    """Whether the config file asks for the parked boxes ([wip] show = true)."""
    wip = tables.get("wip", {})
    return isinstance(wip, dict) and wip.get("show") is True
