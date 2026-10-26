# Adding a box / action to the toolbox itself

Read `docs/ai/code/rules.md` first. An action is one thing: a box in the flow editor, a button on the Live
page, a button in the SAMMI deck and `POST /action/<name>`.

## The short version

Every box is one Box class in its own file (`core/interfaces/box.py`), in the `boxes/` folder next to the
group that adds it:

```python
class DoThing(Box):
    name = "do"                        # the part after the dot: "thing.do"
    label = "Do the thing"
    help = "What it does, in the streamer's words"
    group = "Things"
    hints = {"seconds": "How long, e.g. 2 or 0.5"}

    async def run(self, name: str, seconds: float = 2) -> dict[str, Any]:
        ...


class ThingActions:
    """One group of boxes; it gets what they need in __init__ and hands it to them."""

    def add_to(self, actions: ActionRegistry) -> None:
        for box in (DoThing(), ...):
            actions.add_box(box, "thing")
```

- The full name is `<category>.<name>`; `add_box(box, "thing")` puts the category in front. The category is
  where it sits in the Add box window; a new one needs a title in `CATEGORY_TITLES`
  (`core/actions/registered_action.py`).
- The parameters of `run` are the box's fields. A default makes a field optional. The return value is the
  box's result (other boxes wire from it); `-> None` means no result dot.
- Raise with a message the streamer understands; it shows on the box and comes back over the API.
- Every option below is an attribute of `Box`. One that needs the box's own data (a picker asking the
  program) is set in `__init__`: `self.options = {"scene": self.scene_names}`. A fixed list:
  `options = {"op": fixed_choices(["+", "-"])}` (`core/actions/fixed_choices.py`).
- Boxes of one group that share something (the program's client, helpers, pickers) subclass the group's
  base class in `boxes/<group>_box.py` (e.g. `ListBox`, `ObsAudioBox`). A group that keeps state of its own
  (chat memory, sound player, VTS items) stays a service: its boxes are handed the service and call it.
- Where it lives: a connection's boxes in `connections/<id>/boxes/`, anything else in `core/<area>/boxes/`.
  The group's `add_to(actions)` is called from the connection's `add_actions`, or from
  `assembly/toolbox_assembly.py` (`assembly/own_boxes.py` for boxes that belong to no program).
- Test it by running the box through an `ActionRegistry` (`await actions.run("thing.do", name="x")`) or its
  `run` directly (`await DoThing().run("x")`).
- `actions.add(name, handler, ...)` is still there underneath (JSON boxes, flows as boxes and plugins of
  api_version 1 to 3 use it); new boxes are classes.

## What a box can have (a `Box` attribute, an `actions.add` keyword)

| Argument | What it gives the box |
|---|---|
| `group="..."` | its sub category in the Add box window |
| `options={"scene": provider}` | a picker for that field; `provider` is async and gives a list, or a dict value â†’ label |
| `hints`, `labels` | one help line / another name per field |
| `files={"file": MEDIA_TYPES}` | the field picks a file on the PC |
| `colors=("color",)` | the field gets a colour picker with alpha next to it (writes hex like `#FF8800`, or `#FF880080` when not solid; typing still works) |
| `lights={"picked": self.light_part}` | with `many`: the window gets a switch and a colour; while on, `await light(choice, colour)` is called for the row under the mouse and `light("", colour)` when none is (the program shows which one it is) |
| `many={"picked": self.part_names}` | the field takes several of a list: a button opens a window to tick them (click, or hold the mouse and move over rows); the field holds them as text, separated by commas |
| `shown={"address": ("way", ("mail",))}` | the field is only in the form while the field `way` (a dropdown through `options`) holds one of those values: a box with two ways shows only the chosen way's fields. An empty chooser counts as its default. The handler must ignore the other way's values |
| `outputs={"width": "number"}` | the keys its result always has, so fields can pick them |
| `ports=("then", "else")` | several run outputs; the handler returns the port's name (or True / False) |
| `live=True` | a reading action without parameters that fields can use as a Live value |
| `flow_only=True` | only inside flows: not on Live, not in the SAMMI deck, **not over the API** |
| `capture="obs.get_x"` | a "Save current" button: that action stores the program's state under the same fields |
| `fills={"request": provider}`, `live_hints={"data": provider}` | setting a field fills others (only empty ones or the last fill), and a hint worked out from the box's values |
| `editors={"animation": "vts_animation"}` | the field keeps a value of its own, edited in its own window (a `FieldEditor`; a plugin adds one with `ctx.add_field_editor`) |
| `entries=("stop",)` | extra run dots on the left: a wire arriving while the box runs is passed to it (`BoxSignals`: `ctx.box_signals()` in a plugin, `.has("stop")`, `await .wait_for(seconds, "stop")`); it doesn't start the box. The box's own dot is drawn "start" then |
| `toggles=("switch",)` | entries that start the box when it isn't running (Loop's switch) |
| `port_fields="case"` | a field the box can have any number of (case_1, case_2, ...), each also a run output, before `ports` |
| `entry_fields="value"` | a field the box can have any number of, each with a run dot of its own; only that line is read (Choose value) |
| `value_lines="values"` | lines of name + typed value, each a data output of its own (Value) |
| `named_lines=True` | every param that isn't the handler's own is a line he names, each with a data dot, handed over as `**values` (End) |
| `data_only=True` | no run dots: it runs whenever a wired field needs its value (Value, Get variable, Get viewer value, Calculate, Round, Clamp, Random number, Get from list / object). Only for the toolbox's own values and pure calculations: a box that asks a program keeps its run wire |
| `join=True` | runs once every run wire into it has arrived (Wait for all) |
| `ends_flow=True` | reaching it lets the flow's box in another flow go on; the dict it gives (its `named_lines`) becomes that box's orange dots (End) |
| `gives_back="name"` | its result is given back by the flow under the text in that field (Flow output) |
| `once_per_flow=True` | a flow takes one of it; Add box, paste and duplicate say no to a second (End) |
| `retrigger="if_started_again"` | that field ("nothing", "restart", "add") says what a new start of the flow does while the box waits: the handler gets the run's `Retrigger` (`ctx.retrigger()`, `await .wait(seconds, mode)`) (Wait) |
| `variable_fields=("name",)` | the field holds a variable's own name: it gets a variable picker, and renaming the variable renames it (Set variable) |
| `keys_of="object"` | the keys of what is wired into (or typed in) that field become the box's data dots, following the wire and kept on the box (`FlowNode.outputs`) for when nothing is known (Object values) |
| `alongside="if_already_looping"` | a box with `entries` runs once at a time per flow; this field set to `"alongside"` gives every run its own copy (a stop from a run goes to its own copy, from a run without one to all) (Loop) |
| `offered=False` | left out of the Add box window; it still runs everywhere else (a flow switched off as a box) |
| `typed=("value",)` | fields that take any kind of value and keep it: what is typed by hand is read once (0.5 â†’ number, true â†’ yes, JSON â†’ list / object; "007", "+49" stay text); a wired value keeps its kind |
| an async generator handler | yields port names one after the other ("each", ..., "done"), or `(port, value)` to give the box a value for that round (Loop's round); rounds don't count toward the run limit |

Every one of these is also an attribute of the `Box` class (below), with the same default: the toolbox's own
boxes (Loop, End, Wait, Choose value, ...) use nothing a plugin can't, and `tests/plugins/test_plugin_parity.py`
fails when a new option misses a row here or an attribute on `Box`, or when a box is treated by its name.

## A box as a class (`Box`)

The same box, written the way plugins write them (`core/interfaces/box.py`); one class per file:

```python
class DoThing(Box):
    name = "do"                       # "<owner>.do": the owner goes in front when it is added
    label = "Do the thing"
    help = "What it does, in the streamer's words"
    group = "Things"
    hints = {"seconds": "How long, e.g. 2 or 0.5"}

    async def run(self, name: str, seconds: float = 2) -> dict[str, Any]:
        ...
```

`actions.add_box(DoThing(), "thing")` registers it as `thing.do` (a connection's `boxes()` are added this way
with its id; a plugin's `ctx.add(box)` with the plugin's id). New boxes may be written either way; the
toolbox's own are still `actions.add` calls in groups (`LogicActions`, ...) and move over bit by bit.

## Boxes written as JSON

(For a web API there is a simpler shape that needs no `send` at all: web boxes, `core/web/web_boxes.py`, the
"A plugin without code" part of `docs/PLUGINS.md`.)

For a box that is only "send this request with these fields", no class is needed: `JsonBoxes(folder,
kinds).add_to(actions, "<category>", send)` (core/actions/json_boxes.py) reads every `*.json` file of a folder
and makes real boxes of them; `send(request, data)` is the program's own way to send. A plugin uses
`ctx.add_json_boxes(folder, send, kinds)`. The example in the code: `connections/obs/boxes/` (one file per sub
group), loaded in `ObsConnection.add_actions`.

```json
{"group": "Windows",
 "boxes": [{"name": "open_source_projector", "label": "Open source projector",
            "help": "Opens a projector for a source or a scene",
            "request": "OpenSourceProjector",
            "fixed": {},
            "fields": [{"name": "source", "send_as": "sourceName", "kind": "obs.scene_item"},
                       {"name": "monitor", "send_as": "monitorIndex", "kind": "whole_number",
                        "optional": true, "default": -1, "hint": "-1 = a window"}]}]}
```

- A box: `name`, `request`, and maybe `label`, `help`, `fields`, `fixed` (data every request carries), `group`
  (else the file's), `flow_only`, `outputs` (the keys the answer always has: data dots). A field: `name`, and maybe `kind` (default `text`), `label`, `hint`,
  `optional`, `default`, `send_as` (the program's name for it), `choices`.
- An optional field that is empty is not sent; a field that is not optional must be filled in.
- **Value kinds** (core/values: `ValueKind`, `ValueKinds`) say how a field is typed and what is sent. Always
  there: `text`, `number`, `whole_number`, `yes_no`, `color`, `list`, `object` (the last two as JSON text, or
  from a variable), `file`, `folder`, `image`, `sound`, `video`, `media`. `"kind": "choice"` with `"choices":
  [...]` is a short fixed list.
- **Special kinds** are added by the connection or plugin under a name and then used from JSON:
  `ValueKind("obs.scene", "OBS scene", extra="options", setting=requests.scene_names)` (`extra` is the
  `actions.add` keyword the field goes into, `setting` what it gets). OBS has `obs.scene`, `obs.source`,
  `obs.scene_item`. A value that needs its own window or its own logic (a VTube Studio animation) still needs
  Python; JSON can only name a kind that exists.
- A box that does more than one request (asks first, waits, works something out, gives named outputs) stays a
  class. Classes are the fast way for now; the JSON way is where it goes.
- A wrong file stops the start with the file's name, the box and the field in the message.

## Rules for boxes

- **Anything that writes files, starts programs or sends web requests must be `flow_only=True`.** API callers
  must not get those.
- Names in, IDs looked up: the streamer types or picks a name, the code finds the ID.
- Never rename a parameter or an action that exists: saved flows hold the names.
- **A box that doesn't do what it should yet is parked, not deleted:** add its action name and the reason to
  `WIP_BOXES` in `core/actions/wip_boxes.py`. It is then in no list (Add box, Live, SAMMI deck, API list);
  flows that have it keep running. `[wip] show = true` in `config/toolbox.toml` shows the parked boxes again
  (not on any screen on purpose).
- One box does one thing. Several small boxes that can be wired beat one box with ten fields.
