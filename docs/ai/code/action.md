# Adding a box / action to the toolbox itself

Read `docs/ai/code/rules.md` first. An action is one thing: a box in the flow editor, a button on the Live
page, a button in the SAMMI deck and `POST /action/<name>`.

## The short version

```python
class ThingActions:
    """One class per group of boxes; it gets what it needs in __init__."""

    def add_to(self, actions: ActionRegistry) -> None:
        actions.add("thing.do", self.do, "What it does, in the streamer's words", "Do the thing",
                    group="Things", hints={"seconds": "How long, e.g. 2 or 0.5"})

    async def do(self, name: str, seconds: float = 2) -> dict[str, Any]:
        ...
```

- The name is `<category>.<what>`. The category (before the dot) is where it sits in the Add box window; a
  new category needs a title in `CATEGORY_TITLES` (`core/actions/registered_action.py`).
- The handler's parameters are the box's fields. A default makes a field optional. The return value is the
  box's result (other boxes wire from it); `-> None` means no result dot.
- Raise with a message the streamer understands; it shows on the box and comes back over the API.
- Where the class lives: a connection's boxes in `connections/<id>/`, anything else in `core/<area>/`. Call
  its `add_to(actions)` from the connection's `add_actions`, or from `assembly/toolbox_assembly.py` (`assembly/own_boxes.py` for boxes that belong to no program).
- Test it by running the action through an `ActionRegistry` (`await actions.run("thing.do", name="x")`).

## What `actions.add` can do

| Argument | What it gives the box |
|---|---|
| `group="..."` | its sub category in the Add box window |
| `options={"scene": provider}` | a picker for that field; `provider` is async and gives a list, or a dict value → label |
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
| `capture`, `fills`, `live_hints`, `editors`, `entries`, `port_fields`, `data_outputs` | see "Actions and the flow editor" in `docs/ARCHITECTURE.md` |
| `typed=("value",)` | fields that take any kind of value and keep it: what is typed by hand is read once (0.5 → number, true → yes, JSON → list / object; "007", "+49" stay text); a wired value keeps its kind |

## Boxes written as JSON

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
  (else the file's), `flow_only`. A field: `name`, and maybe `kind` (default `text`), `label`, `hint`,
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
