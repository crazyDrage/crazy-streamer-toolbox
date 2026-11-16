from dataclasses import replace

from streamer_toolbox.core.event_types.event_type import EventType
from streamer_toolbox.core.event_types.event_type_store import EventTypeStore
from streamer_toolbox.core.flows.flow import Flow
from streamer_toolbox.core.flows.flow_input import FlowInput
from streamer_toolbox.core.flows.flow_library import FlowLibrary
from streamer_toolbox.core.flows.flow_node import FlowNode
from streamer_toolbox.core.flows.flow_trigger import FlowTrigger
from streamer_toolbox.core.flows.flow_wire import DONE, START, FlowWire
from streamer_toolbox.core.variables.variable_store import VariableStore

SEND = "event.send."  # + <event>: its box (EventActions)
ONLY_TO = "only_to"  # the box's field that sends to one widget or alert only
FOLDER = "Events"  # where the event types' own flows are listed
TRIGGER, BOX = "t1", "n1"
LIST, CHECK = "n7", "n8"  # a main flow's Set variable (the list) and List has (is the platform in it)
HELPER = "flow:"  # + a HELPERS key: a box's action that is that helper flow (its name is found when it is made)
# his round 90: one main flow per event type for every platform, and a flow of its own for a platform that needs
# more (the chat's Twitch profile picture and emotes). The main flow leaves out the platforms listed in the
# variable event_<type>_platforms_with_own_flow; making a platform flow puts its platform there. A new platform
# later is a new flow and a name in the list: the main flow, maybe changed by him, stays as it is.
# type → platform → (its trigger, its title, the values only it gives → what they are, its boxes as (id, action,
# fields, place), the wires as (from, port, to, its run dot)). The Start box is TRIGGER, the Send box BOX.
PlatformFlow = tuple[str, str, dict[str, str], tuple[tuple[str, str, dict[str, str], tuple[float, float]], ...],
                     tuple[tuple[str, str, str, str], ...]]
PLATFORM_FLOWS: dict[str, dict[str, PlatformFlow]] = {
    "chat": {"twitch": ("twitch.chat", "Twitch", {"picture": "${box.n2.picture}",
                                                  "emoji_dict": "${box.n2.emoji_dict}"}, (
        # his 11-16: the picture and the emotes in a flow of their own, used as a box ("we use it multiple times")
        ("n2", f"{HELPER}twitch_pfp_and_chat_emotes", {"user_id": f"${{box.{TRIGGER}.user_id}}",
                                                       "user_login": f"${{box.{TRIGGER}.user_login}}",
                                                       "emotes": f"${{box.{TRIGGER}.emotes}}",
                                                       "message": f"${{box.{TRIGGER}.message}}"}, (620.0, 40.0)),
    ), (
        (TRIGGER, "out", "n2", ""), ("n2", DONE, BOX, ""),
    ))},
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


def twitch_pfp_and_chat_emotes(name: str) -> Flow:
    """His 11-16: "twitch pfp and chat emotes", a flow used as a box by the Twitch flows that need them. In:
    user_id, user_login, emotes, message (none of them needed). Out: picture (the profile picture's address, kept
    on this PC and remembered 10 minutes; "" without a user id) and emoji_dict (the Twitch emotes and the BetterTTV
    ones as an emoji dictionary, joined from one of each, their pictures kept on this PC; {} without emotes). A missing one is left out, never a failure. Each input is a
    wire from the Input box (his 11-16: "connect the box from the flow input box", to see it better)."""
    nodes = (
        FlowNode("n1", "logic.if", {"left": "${box.input.user_id}", "op": "!=", "right": ""},
                 note="no user id: no picture", box=(320.0, 40.0)),
        FlowNode("n2", "cache.value", {"key": "${box.input.user_id}", "value": "${box.n4.address}", "max_age": "10",
                                       "most": "1000"}, box=(620.0, 40.0)),
        FlowNode("n3", "twitch.profile_picture", {"user_id": "${box.input.user_id}"}, box=(620.0, 300.0)),
        FlowNode("n4", "media.keep_locally", {"url": "${box.n3.picture}", "name": "${box.input.user_login}"},
                 box=(920.0, 300.0)),
        FlowNode("n5", "logic.choose", {"values": 2, "value_1": "${box.n2.value}", "value_2": ""},
                 note="the picture, or none", box=(1220.0, 40.0)),
        FlowNode("n6", "twitch.emotes", {"emotes": "${box.input.emotes}"}, box=(1520.0, 40.0)),
        FlowNode("n8", "twitch.bttv_emotes", {"message": "${box.input.message}"}, box=(1820.0, 40.0)),
        # his 11-16: a dictionary of each, then the two together (Twitch's win: its own emote of the same word)
        FlowNode("n9", "object.join", {"first": "${box.n8.emoji_dict}", "second": "${box.n6.emoji_dict}"},
                 box=(1820.0, 300.0)),
        FlowNode("n7", "logic.end", {"picture": "${box.n5}", "emoji_dict": "${box.n9}"}, box=(2120.0, 40.0)),
    )
    wires = (FlowWire(START, "out", "n1"), FlowWire("n1", "then", "n2"), FlowWire("n1", "else", "n5", "value_2"),
             FlowWire("n2", "found", "n5", "value_1"), FlowWire("n2", "no_value", "n3"), FlowWire("n3", DONE, "n4"),
             FlowWire("n4", DONE, "n2", "set"), FlowWire("n5", DONE, "n6"), FlowWire("n6", DONE, "n8"),
             FlowWire("n8", DONE, "n7"))
    return Flow(name, "Twitch pfp and chat emotes", nodes, wires,
                description="A Twitch viewer's profile picture and the emotes of their message, as a box for the "
                            "Twitch flows that need them (Event: chat · Twitch). Gives picture (kept on this PC, "
                            "remembered 10 minutes) and emoji_dict (its Twitch and BetterTTV emotes as an emoji "
                            "dictionary: one of each, joined). A user id, emotes or message it doesn't get are left "
                            "out. Made by the toolbox; change it like any flow.",
                inputs=(FlowInput("user_id", ""), FlowInput("user_login", ""), FlowInput("emotes", ""),
                        FlowInput("message", "")),
                folder=FOLDER, as_box=True, start_box=(20.0, 40.0), input_box=(20.0, 300.0))


# the flows the platform flows use as a box: key → how it is made (his 11-16)
HELPERS = {"twitch_pfp_and_chat_emotes": twitch_pfp_and_chat_emotes}


def list_name(event: str) -> str:
    """The variable naming the platforms that have a flow of their own for this event type (his round 90)."""
    return f"event_{event}_platforms_with_own_flow"


class EventFlows:
    """The flows that send events (his round 78: one flow per event type). An event type's own flow, in the
    folder Events: its trigger's Start box (a follow on any platform, ...) wired into its Send box, each value
    from the trigger's field of the same name; one he made himself has only the Manual Start (he wires what
    fills it). The toolbox makes a type's flow once (when something first uses it); he changes it like any
    flow, and one he deleted isn't made again by itself.

    His round 90: the main flow is for every platform except those in the variable list_name(type); a platform
    that needs more (PLATFORM_FLOWS) gets a flow of its own, "Event: chat · Twitch", made with the main one, and
    its name goes into that list (`variables`)."""

    def __init__(self, flows: FlowLibrary, events: EventTypeStore, variables: VariableStore | None = None) -> None:
        self._flows = flows
        self._events = events
        self._variables = variables

    def sending(self, event: str) -> list[tuple[str, str]]:
        """(the flow's label, its only_to: "" = to everyone) for each Send box of this event in a flow."""
        wanted = action_name(event)
        return [(flow.label, str(node.params.get(ONLY_TO, "") or "")) for flow in self._flows.all()
                for node in flow.nodes if node.action == wanted]

    def make(self, kind: EventType) -> str:
        """The event type's own flow (and its platform flows); the main flow's name."""
        name = self._flows.free_name(f"event {kind.name}")
        self._flows.save(self._built(kind, name))
        self._make_platform_flows(kind)
        self._events.mark_flow_made(kind.name)
        return name

    def _make_platform_flows(self, kind: EventType) -> None:
        """Each platform flow of a default type, made new in the place of one there (its name and on/off stay),
        and its platform put into the list. Not for a type without the value only that flow gives."""
        if not kind.default:
            return
        values = {v.name for v in kind.values}
        for platform, made in PLATFORM_FLOWS.get(kind.name, {}).items():
            if not values & set(made[2]):
                continue
            label = f"Event: {kind.name} · {made[1]}"
            there = next((f for f in self._flows.all() if f.label.casefold() == label.casefold()), None)
            name = there.name if there else self._flows.free_name(f"event {kind.name} {platform}")
            flow = self._platform_built(kind, name, label, made)
            self._flows.save(replace(flow, enabled=there.enabled) if there else flow, name)
            self._listed(kind.name, platform)

    def _helper(self, key: str) -> str:
        """The helper flow's name: made new in the place of the one there (its name and on/off stay)."""
        made = HELPERS[key]
        label = made("x").label
        there = next((f for f in self._flows.all() if f.label.casefold() == label.casefold()), None)
        name = there.name if there else self._flows.free_name(label)
        flow = made(name)
        self._flows.save(replace(flow, enabled=there.enabled) if there else flow, name)
        return name

    def _listed(self, event: str, platform: str) -> None:
        if self._variables is None:
            return
        name = list_name(event)
        there = self._variables.get(name)
        platforms = list(there) if isinstance(there, list) else ([there] if there not in (None, "") else [])
        if not any(str(p).casefold() == platform for p in platforms):
            self._variables.set(name, [*platforms, platform])

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
        self._make_platform_flows(kind)
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
            own = {value for made in PLATFORM_FLOWS.get(kind.name, {}).values() for value in made[2]}  # only theirs
            params = {v.name: f"${{box.{TRIGGER}.{v.name}}}" for v in kind.values if v.name not in own}
            triggers = (FlowTrigger(trigger, dict(match), TRIGGER, (320.0, 40.0)),)
            wires = (FlowWire(TRIGGER, "out", BOX),)
            said = f"on every {kind.name}" + (", from any platform" if "." not in trigger else "")
            if "." not in trigger:  # any platform: not those with a flow of their own (the list)
                said += f" except those in the variable {list_name(kind.name)} (they have a flow of their own)"
                asking = (FlowNode(LIST, "var.set", {"name": list_name(kind.name), "value": "[]",
                                                     "only_if_new": True}, box=(620.0, 40.0)),
                          FlowNode(CHECK, "list.contains", {"items": f"${{box.{LIST}}}",
                                                            "value": f"${{box.{TRIGGER}.platform}}"},
                                   box=(920.0, 40.0)))
                wires = (FlowWire(TRIGGER, "out", LIST), FlowWire(LIST, DONE, CHECK), FlowWire(CHECK, "else", BOX))
        else:
            params, triggers, wires = {}, (), (FlowWire(START, "out", BOX),)
            said = "when this flow is started (a button, another flow, a trigger you add); fill its values"
        return Flow(
            # right of the Manual Start and Input boxes, which stay at the left edge
            name, f"Event: {kind.name}",
            (*asking, FlowNode(BOX, action_name(kind.name), params,
                               box=(max((node.box[0] for node in asking), default=320.0) + 300.0, 40.0))),
            wires, triggers, description=f"Sends the event {kind.name!r} (Overlay → Events) to every widget and "
                                         f"alert that uses it, {said}. Made by the toolbox; change it like any "
                                         "flow.", folder=FOLDER, as_box=False)

    def _platform_built(self, kind: EventType, name: str, label: str, made: PlatformFlow) -> Flow:
        trigger, title, own, boxes, wired = made
        params = {v.name: own.get(v.name, f"${{box.{TRIGGER}.{v.name}}}") for v in kind.values}
        value = " and ".join(v.name for v in kind.values if v.name in own)
        asking = tuple(FlowNode(box, f"flow.{self._helper(action[len(HELPER):])}" if action.startswith(HELPER)
                                else action, dict(fields), box=place) for box, action, fields, place in boxes)
        return Flow(name, label, (*asking, FlowNode(BOX, action_name(kind.name), params,
                                                    box=(max(n.box[0] for n in asking) + 300.0, 40.0))),
                    tuple(FlowWire(*wire) for wire in wired), (FlowTrigger(trigger, {}, TRIGGER, (320.0, 40.0)),),
                    description=f"Sends the event {kind.name!r} (Overlay → Events) on every {kind.name} from "
                                f"{title}, with its {value}. {title} is in the variable {list_name(kind.name)}, so "
                                f"\"Event: {kind.name}\" leaves it to this flow. Made by the toolbox; change it "
                                "like any flow.", folder=FOLDER, as_box=False)

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
