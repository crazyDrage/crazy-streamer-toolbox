import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from streamer_toolbox.core.actions.numbered_fields import numbered_fields

ActionHandler = Callable[..., Awaitable[Any]]
# values, value → label, or group → {value → label} (the field gets a group picker, e.g. SAMMI buttons by deck)
OptionsProvider = Callable[[], Awaitable[list[str] | dict[str, str] | dict[str, dict[str, str]]]]
FillProvider = Callable[[Any], dict[str, Any]]  # a field's new value → values for other fields
HintProvider = Callable[[Mapping[str, Any]], str]  # the box's values → one field's hint
LightProvider = Callable[[str, str], Awaitable[None]]  # (choice, colour): show it lit in the program; "" = none

CATEGORY_TITLES = {"obs": "OBS", "vts": "VTube Studio", "sammi": "SAMMI", "mixitup": "Mix It Up",
                   "twitch": "Twitch", "flow": "Flows", "logic": "Logic", "var": "Variables", "sound": "Sound",
                   "file": "Files", "list": "Lists", "json": "JSON", "popup": "Popups", "data": "Data",
                   "video": "Video", "object": "Objects", "text": "Text", "web": "Web",
                   "system": "Programs", "time": "Time", "viewer": "Viewers",
                   "alert": "Alerts", "tip": "Tips", "widget": "Widgets",
                   "vnyan": "VNyan", "warudo": "Warudo", "veadotube": "veadotube mini",
                   "tits": "T.I.T.S.", "streamerbot": "Streamer.bot", "firebot": "Firebot",
                   "lumia": "Lumia Stream", "voicemod": "Voicemod", "heartrate": "Heart rate",
                   "discord": "Discord"}


@dataclass(frozen=True)
class RegisteredAction:
    """An action by name.

    For the flow editor: `group` is its sub category in the Add menu (category = the part before the dot);
    `options` offer choices for a parameter (e.g. the OBS scenes for "scene"); `capture` names an action that
    stores the current state under the same parameters (the "Save current" button); `ports` are the box's
    outputs when it chooses one (an If: ("then", "else"); the handler returns True for the first, False for the
    second); `flow_only` actions only make sense inside a flow and aren't offered on Live, in SAMMI or the API;
    a `join` box runs once all wires into it have arrived (Wait for all); a `live` action reads a value and needs
    no parameters, so a box field can use it directly as a Live value (${get.vts.get_model}); `outputs` names the fields its result always has ({name: kind},
    e.g. Video info's width / height / seconds), each an extra data output next to "result"; `port_fields` names
    a field the box can have any number of (Switch: "case" → case_1, case_2, ...), each one also an output, before
    `ports` (see ports_for); `labels` / `hints` give a field a readable name and one line of help in the box form
    (without a label the name is shown with spaces, "if_started_again" → "If started again"); `editors` gives a
    field a value the box keeps itself, edited in its own window ({field: kind}, e.g. "animation" →
    "vts_animation"; the kind also names its folder of saved files); `entries` are extra run dots on the box's
    left (a Loop's "stop"): a wire arriving there while the box runs is passed to it (BoxSignals), it doesn't
    start it; `toggles` names entries that do start it when it isn't running (a Loop's "switch": stops it if it
    loops, else starts it; his round 55). `offered=False` leaves the box out of the Add box window (a flow
    he switched off as a box, his round 56); it still runs everywhere else. `ends_flow`: reaching the box lets
    the flow's box in another flow go on, and a dict it gives (its `named_lines`) becomes that box's orange dots
    (End). `gives_back` names the field whose text is the name the box's result is given back under (Flow
    output: "name"). `once_per_flow`: a flow takes one such box (End). `retrigger` names the field that says
    what a new start of the flow does while the box runs ("nothing", "restart", "add"; Wait's
    if_started_again): the handler gets the Retrigger (PluginContext.retrigger). `variable_fields` hold a
    variable's own name (Set variable's name): renaming the variable renames them too.
    `keys_of` names a field whose value's keys become the box's data dots, following what is wired into it
    (Object values, his round 60). A box with `entries` runs once at a time per flow (a second run that reaches it
    stops there); `alongside` names the field that can say ALONGSIDE (core/flows/box_signals.py): then every run
    gets its own copy of the box (Loop's if_already_looping, his round 63). Every one of these is a
    keyword of ActionRegistry.add and PluginContext.add_action, so a plugin can make the same boxes (his round
    56; tests/test_plugin_parity.py keeps it so). `fills` fill other fields when a field is set ({field: provider(value) → {other field: value}}, the
    Raw request's data template for the request picked): only a field that is empty or still holds the last fill
    is changed, so typed values stay; `live_hints` give a field a hint worked out from the box's values (what the
    picked request needs); `files` marks the fields that hold a file on this PC ({field: the endings it takes},
    core/files/file_types: () = any file, FOLDER = a folder): the box form gets a button that opens the file window;
    `colors` names the fields that hold a colour: the form gets a colour picker next to the field (it writes hex
    like #FF8800, or #FF880080 with alpha; typing still works); `many` gives a field that takes several of a list a
    window to tick them in ({field: provider of the list}; the field holds them as text, separated by commas);
    `lights` lets that window show in the program which one the mouse is on ({field: light(choice, colour)},
    light("", colour) takes it away again: the part of the model under the mouse lights up); `shown` hides a
    field unless another field (a dropdown that chooses between ways) holds one of the given values ({field:
    (chooser, (values, ...))}, see shows): the form only shows what the chosen way uses. `typed` names the fields
    that take any kind of value and keep it (Set variable's value): what is typed into one by hand is read for
    what it holds (0.5 → a number, true → yes, JSON → a list or object; "007" and "+49" stay text, see
    box_value.understand). A value that comes by wire keeps the kind it has. `value_lines` names the parameter
    that holds named values typed into the box ({name: value}, the Value box): each line is a data output of its
    own, and each value is read like a `typed` field. A `data_only` box only gives values: it has no run dots,
    so no run wire leads into or out of it; it runs whenever a field wired to it needs its value (Value, Get
    variable; his round 52). `entry_fields` names a field the box can have any number of (End: "name" → name_1,
    name_2, ...), each with a run dot of its own on the left: a run wire into one starts the box, and only that
    field is read, handed to the handler under the plain name (name=...). The box's normal run dot isn't drawn; a
    wire into it counts as the first one (Choose value; his round 53). `named_lines`: the box's params beyond its
    handler's own are lines he names (End's values, his round 54): each one a field of its own with a data dot on
    the left, read like a `typed` field and handed to the handler under its name (**values).

    `is_tested`, `is_understandable` and `is_usable` are his three checks of the box (works, understandable,
    usable). No box sets them itself: they are read from the test record at start (TestGate), and TestView
    decides with them whether the Add box window offers the box.
    """

    name: str
    handler: ActionHandler
    description: str
    label: str = ""
    options: dict[str, OptionsProvider] = field(default_factory=dict)
    capture: str = ""
    group: str = ""
    ports: tuple[str, ...] = ()
    flow_only: bool = False
    join: bool = False
    live: bool = False
    outputs: dict[str, str] = field(default_factory=dict)
    port_fields: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    hints: dict[str, str] = field(default_factory=dict)
    editors: dict[str, str] = field(default_factory=dict)
    entries: tuple[str, ...] = ()
    fills: dict[str, FillProvider] = field(default_factory=dict)
    live_hints: dict[str, HintProvider] = field(default_factory=dict)
    files: dict[str, tuple[str, ...]] = field(default_factory=dict)
    colors: tuple[str, ...] = ()
    many: dict[str, OptionsProvider] = field(default_factory=dict)
    lights: dict[str, LightProvider] = field(default_factory=dict)
    shown: dict[str, tuple[str, tuple[str, ...]]] = field(default_factory=dict)
    typed: tuple[str, ...] = ()
    value_lines: str = ""
    data_only: bool = False
    entry_fields: str = ""
    named_lines: bool = False
    toggles: tuple[str, ...] = ()
    offered: bool = True
    ends_flow: bool = False
    gives_back: str = ""
    once_per_flow: bool = False
    retrigger: str = ""
    variable_fields: tuple[str, ...] = ()
    keys_of: str = ""
    alongside: str = ""
    is_tested: bool = False
    is_understandable: bool = False
    is_usable: bool = False

    def ports_for(self, params: Mapping[str, Any]) -> tuple[str, ...]:
        """A box's outputs: `ports`, after one per numbered field if it has port_fields."""
        if not self.port_fields:
            return self.ports
        return (*numbered_fields(self.port_fields, params), *self.ports)

    def entry_lines(self, params: Mapping[str, Any]) -> list[str]:
        """The run dots of a box with entry_fields, one per numbered field (name_1, name_2, ...); else none."""
        return numbered_fields(self.entry_fields, params) if self.entry_fields else []

    def starts_at(self, params: Mapping[str, Any]) -> list[str]:
        """The extra run dots a wire into can start the box: its lines (entry_fields) and its toggles."""
        return [*self.entry_lines(params), *self.toggles]

    def lines_named(self, params: Mapping[str, Any]) -> list[str]:
        """The lines he named (named_lines: the params that aren't the handler's own), in their order; else none."""
        if not self.named_lines:
            return []
        own = {n for n, p in inspect.signature(self.handler).parameters.items() if p.kind != p.VAR_KEYWORD}
        return [key for key in params if key not in own]

    def shows(self, name: str, params: Mapping[str, Any]) -> bool:
        """False for a field that `shown` hides with the box's values as they are. A chooser that is empty counts
        as its default; one that is only known when the box runs (a variable, a wire) hides nothing."""
        if name not in self.shown:
            return True
        chooser, values = self.shown[name]
        value = params.get(chooser, "")
        if value in ("", None):
            value = inspect.signature(self.handler).parameters[chooser].default
        return value in values or str(value).startswith("${")

    def choosers(self) -> set[str]:
        """The fields other fields' showing depends on."""
        return {chooser for chooser, _ in self.shown.values()}

    def filled(self, params: Mapping[str, Any], name: str, value: Any) -> dict[str, Any]:
        """The box's values after `name` is set to `value`, with what `fills` gives for it (see the class)."""
        new = dict(params)
        old_value, new[name] = new.get(name, ""), value
        if name not in self.fills:
            return new
        before = self.fills[name](old_value) if old_value not in ("", None) else {}
        for other, filling in self.fills[name](value).items():
            if new.get(other) in ("", None) or new.get(other) == before.get(other):
                new[other] = filling
        return new

    @property
    def category(self) -> str:
        """The part before the first dot ("hello" for "hello.greet"): the plugin id, or "obs" for OBS actions."""
        return self.name.split(".", 1)[0] if "." in self.name else "toolbox"

    @property
    def category_title(self) -> str:
        return CATEGORY_TITLES.get(self.category, self.category.replace("_", " ").capitalize())

    @property
    def title(self) -> str:
        """What a button shows: the given label, else the name after the category ("fit_raid_clip" -> "Fit raid clip")."""
        if self.label:
            return self.label
        words = self.name.split(".", 1)[-1].replace("_", " ").replace(".", " ").strip()
        return words[:1].upper() + words[1:]
