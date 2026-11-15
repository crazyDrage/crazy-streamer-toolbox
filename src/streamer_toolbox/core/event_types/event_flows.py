from dataclasses import replace

from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import DONE, START, FlowWire

SEND = "event.send."  # + <event>: its box (EventActions)
ONLY_TO = "only_to"  # the box's field that sends to one widget or alert only
FOLDER = "Events"  # where the event types' own flows are listed
TRIGGER, BOX = "t1", "n1"
# values a default type's trigger doesn't give: boxes before the Send box ask for them, one after the other
# (his 11-14: the chat's profile picture, "only the default that will get added"; it is kept on this PC, the
# media buffer). type → (value, the boxes as (id, action, fields), what the value is)
ASKED: dict[str, tuple[str, tuple[tuple[str, str, dict[str, str]], ...], str]] = {
    "chat": ("picture", (
        # the platform is the filter: another platform's chatter gets "" at once, and "" is kept as nothing
        ("n2", "twitch.profile_picture", {"user": f"${{box.{TRIGGER}.user_id}}",
                                          "platform": f"${{box.{TRIGGER}.platform}}"}),
        ("n3", "media.keep_locally", {"url": "${box.n2.picture}", "name": f"${{box.{TRIGGER}.user_login}}"}),
    ), "${box.n3.address}"),
}
# an event type that comes with the toolbox → the trigger its flow starts on and that trigger's match. A gifted
# sub isn't a sub here: the gifter's gift event covers them (five gifts are one alert, as before round 78)
TRIGGERS: dict[str, tuple[str, dict[str, str]]] = {
    "chat": ("chat", {}), "chat_deleted": ("twitch.chat_deleted", {}), "follow": ("follow", {}),
    "sub": ("sub", {"gift": "false"}), "resub": ("resub", {}), "gift": ("gift", {}), "cheer": ("cheer", {}),
    "raid": ("raid", {}), "tip": ("tip", {}), "redeem": ("redeem", {}),
    "community_gift": ("gift", {}), "superchat": ("youtube.superchat", {}), "member": ("youtube.member", {}),
    "charity": ("streamelements.activity", {"type": "charityCampaignDonation"}),
    "merch": ("streamelements.activity", {"type": "merch"}),
}


def action_name(event: str) -> str:
    return f"{SEND}{event}"


class EventFlows:
    """The flows that send events (his round 78: one flow per event type). An event type's own flow, in the
    folder Events: its trigger's Start box (a follow on any platform, ...) wired into its Send box, each value
    from the trigger's field of the same name; one he made himself has only the Manual Start (he wires what
    fills it). The toolbox makes a type's flow once (when something first uses it); he changes it like any
    flow, and one he deleted isn't made again by itself."""

    def __init__(self, flows: FlowLibrary, events: EventTypeStore) -> None:
        self._flows = flows
        self._events = events

    def sending(self, event: str) -> list[tuple[str, str]]:
        """(the flow's label, its only_to: "" = to everyone) for each Send box of this event in a flow."""
        wanted = action_name(event)
        return [(flow.label, str(node.params.get(ONLY_TO, "") or "")) for flow in self._flows.all()
                for node in flow.nodes if node.action == wanted]

    def make(self, kind: EventType) -> str:
        """The event type's own flow; its name."""
        name = self._flows.free_name(f"event {kind.name}")
        self._flows.save(self._built(kind, name))
        self._events.mark_flow_made(kind.name)
        return name

    def own_flow(self, event: str) -> Flow | None:
        """The flow that sends the event: the one labelled "Event: <name>", else the first that sends it."""
        wanted, label = action_name(event), f"Event: {event}".casefold()
        sending = [flow for flow in self._flows.all() if any(node.action == wanted for node in flow.nodes)]
        named = [flow for flow in self._flows.all() if flow.label.casefold() == label]
        return (named or sending or [None])[0]

    def add_default(self, event: str) -> str:
        """A connection's "Add default flows" (his 11-14): the default type back if he deleted it, shown, and its
        own flow made new; the flow's name. Its flow there already: nothing new ("")."""
        kind = self._default_type(event)
        if kind is None or self.own_flow(event) is not None:
            return ""
        return self.make(kind)

    def update_default(self, event: str) -> str:
        """His yes to "update the existing flows": the type's own flow made new in the place of the one there
        (its name and on/off stay); the flow's name."""
        kind = self._default_type(event)
        there = self.own_flow(event)
        if kind is None:
            return ""
        if there is None:
            return self.make(kind)
        self._flows.save(replace(self._built(kind, there.name), enabled=there.enabled), there.name)
        self._events.mark_flow_made(kind.name)
        return there.name

    def _default_type(self, event: str) -> EventType | None:
        kind = self._events.restore_default(event)
        if kind is not None:
            self._events.show(event)
        return self._events.get(event)

    def _built(self, kind: EventType, name: str) -> Flow:
        trigger, match = TRIGGERS.get(kind.name, ("", {})) if kind.default else ("", {})
        asking: tuple[FlowNode, ...] = ()
        if trigger:
            params = {v.name: f"${{box.{TRIGGER}.{v.name}}}" for v in kind.values}
            triggers = (FlowTrigger(trigger, dict(match), TRIGGER, (320.0, 40.0)),)
            wires = (FlowWire(TRIGGER, "out", BOX),)
            said = f"on every {kind.name}" + (", from any platform" if "." not in trigger else "")
            value, chain, filled = ASKED.get(kind.name, ("", (), ""))
            if value in params:  # Start → the boxes that ask, one after the other → Send
                params[value] = filled
                asking = tuple(FlowNode(box, action, dict(fields), box=(620.0 + 300.0 * at, 40.0))
                               for at, (box, action, fields) in enumerate(chain))
                ids = [TRIGGER, *(node.id for node in asking), BOX]
                # the Start box leaves by "out", a box by "done"
                wires = tuple(FlowWire(a, "out" if a == TRIGGER else DONE, b) for a, b in zip(ids, ids[1:]))
        else:
            params, triggers, wires = {}, (), (FlowWire(START, "out", BOX),)
            said = "when this flow is started (a button, another flow, a trigger you add); fill its values"
        return Flow(
            # right of the Manual Start and Input boxes, which stay at the left edge
            name, f"Event: {kind.name}",
            (*asking, FlowNode(BOX, action_name(kind.name), params, box=(620.0 + 300.0 * len(asking), 40.0))),
            wires, triggers, description=f"Sends the event {kind.name!r} (Overlay → Events) to every widget and "
                                         f"alert that uses it, {said}. Made by the toolbox; change it like any "
                                         "flow.", folder=FOLDER, as_box=False)

    def make_once(self, event: str) -> str:
        """The event type's own flow, unless the toolbox made it before or a flow sends it already; its name, or
        "" when none was made."""
        kind = self._events.get(event)
        if kind is None or self._events.flow_made(event) or self.sending(event):
            return ""
        return self.make(kind)

    def hide_folder(self) -> None:
        """The folder Events out of the Flows page's list (his "hide in list" for the toolbox's own flows)."""
        self._flows.folder_settings.set_hidden(FOLDER, True)

    def renamed_event(self, old: str, new: str) -> int:
        """An event type got another name: the flows send it with its new box. How many flows changed."""
        return self._change(action_name(old), lambda node: replace(node, action=action_name(new)))

    def renamed_value(self, event: str, old: str, new: str) -> int:
        """A value of the event type got another name: its field in the Send boxes too."""
        def rename(node: FlowNode) -> FlowNode:
            return replace(node, params={(new if key == old else key): value for key, value in node.params.items()})
        return self._change(action_name(event), rename)

    def _change(self, action: str, change) -> int:
        changed = 0
        for flow in self._flows.all():
            if any(node.action == action for node in flow.nodes):
                nodes = tuple(change(node) if node.action == action else node for node in flow.nodes)
                self._flows.save(replace(flow, nodes=nodes), flow.name)
                changed += 1
        return changed
