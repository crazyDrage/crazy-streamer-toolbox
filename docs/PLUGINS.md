# Writing a plugin

A plugin is a folder in `plugins/`. The toolbox finds it at start (restart after adding or changing one).
The Plugins page shows what loaded and why something didn't. Its **New plugin** button makes a folder that
loads as it is, with a first box that works (with code or without; then restart the toolbox).

There are two kinds:

- **A plugin without code**: `plugin.json` and a `boxes/` folder of JSON files. Each box calls a web API: an
  address, its inputs, its outputs. For "talk to that web service" without knowing Python. See
  [A plugin without code](#a-plugin-without-code).
- **A plugin with code**: `plugin.json` and `main.py`. It can add every kind of thing the toolbox has: boxes,
  triggers, a connection, tools, pages, cards, listeners, field windows, API routes.

```
plugins/my_thing/
  plugin.json        info about the plugin
  main.py            the entry point: one class, register(ctx) adds everything
  lib/               the plugin's other classes, one per file
  resources/         pictures, default settings, JS, ... (served to the GUI)
  boxes/             (a plugin without code: only this and plugin.json)
```

Plugins are kept apart from the toolbox's own repository. The example plugins are planned as a repository of
their own: `example` (a guided tour: one of every kind, with a README that walks through it; start there),
`hello` (small), `jokes` (no code, a web API), `sammi_decks` (a real tool: SAMMI decks as buttons).

## plugin.json

```json
{
  "id": "my_thing",
  "name": "My thing",
  "version": "0.1.0",
  "api_version": 4,
  "description": "What it does, one sentence",
  "author": "you"
}
```

- `id`: lowercase letters, digits and `_`. It's the folder's package name and the start of its boxes'
  names (`my_thing.do_it`).
- `api_version`: 4. Plugins made for 1 to 3 still load (they use the older `ctx.add_*` calls, see the end).
  A plugin made for a newer version than the toolbox knows isn't loaded (the Plugins page says why).
- Optional: `"main": "start.py"` if the entry file isn't `main.py`; `"class": "MyPlugin"` if main has more
  than one plugin class.

## A plugin with code

### main.py: the one entry point

Every kind of thing a plugin can add has **one class** (in `streamer_toolbox.core.interfaces`). You write a
class of that kind, one per file in `lib/`, and `register(ctx)` adds them with `ctx.add(...)`:

```python
"""The plugin's entry point: everything it adds is added in register(), one class per thing."""
from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin

from .lib.shout import Shout
from .lib.board import Board


class MyThingPlugin(ToolboxPlugin):
    def register(self, ctx: PluginContext) -> None:
        ctx.add(Shout())        # a box in flows, a Live button, SAMMI, the API
        ctx.add(Board(ctx))     # a page under Tools
```

- Exactly one class in `main.py` must extend `ToolboxPlugin` (or name it in plugin.json).
- `async def start(self)` and `async def stop(self)` (both optional): start what the plugin runs itself (a
  timer, a socket) and let go of it again. start() is called when the toolbox has started and when the plugin
  is switched on again; stop() when it is switched off and when the toolbox closes. Adding things is only in
  `register`. Its connection is started and stopped by the toolbox like every connection.
- Classes in `lib/` are imported relatively: `from .lib.board import Board`; inside `lib/`: `from .other
  import Other`. One class per file, the file named after the class.
- A plugin that crashes while loading is skipped and shown on the Plugins page; the toolbox keeps running.

### What a plugin can add: one class per kind

| Kind | Class | What it is | Fill in |
|---|---|---|---|
| a box | `Box` | a box in flows, a button on Live, in the SAMMI deck, `POST /action/<id>.<name>` | `name`, `label`, `help`, options, `async run(...)` |
| a trigger | `Trigger` | something that can start a flow; `fire(data)` starts the flows that have it | `event`, `title`, `fields`, maybe `pick`, `choices`, `description` |
| a connection | `ConnectionBase` | a program the toolbox talks to: its own tab under Connections, settings, on / off; it brings its own boxes | `id`, `title`, `icon`, `fields()`, `test()`, `start()`, `stop()`, `boxes()` |
| a tool | `Tool` | a page under Tools (a card on its overview, an item in the side menu) | `title`, `icon`, `description`, `build()` |
| a page | `Page` | a page of its own at `/plugins/<id>`, listed in the side list of the Plugins tab | `title`, `icon`, maybe `subpath`, `build()` |
| a card | `Panel` | a card: `"connections"` on Connections, `"live"` / `"settings"` under Plugins → your plugin | `title`, `section`, `build()` |
| a listener | `Listener` | hears every event of the toolbox (a follow, a redeem, another plugin's trigger) | `async heard(kind, data)` |
| a field window | `FieldEditor` | a field kind with its own window (like the VTube Studio animation); add the class, not one of it | `kind`, `build()`, `text(value)` |
| API routes | FastAPI's `APIRouter` | your own addresses under `/api/plugins/<id>` | the routes |

All of them: `ctx.add(thing)`. It gives back the full name where there is one (`"my_thing.shout"`).

### A box

```python
from streamer_toolbox.core.interfaces.box import Box


class Shout(Box):
    name = "shout"                      # its full name is "my_thing.shout"; saved flows hold it: never rename
    label = "Shout"                     # its title
    help = "Makes a text loud"          # one line under it
    outputs = {"text": "text"}          # the keys of the result: dots other boxes wire from
    hints = {"text": "What to shout"}   # one line of help under a field

    async def run(self, text: str = "hello", times: int = 1) -> dict[str, str]:
        return {"text": " ".join([text.upper() + "!"] * times)}
```

- The parameters of `run` are the box's fields. A default makes a field optional; the type (`str`, `int`,
  `float`, `bool`) decides the input.
- What `run` returns is the box's result. `-> None`: no result.
- To refuse, `raise` with words the streamer understands; the text shows on the box.
- Every option a box can have is an attribute of `Box`, with its default and a comment: the editor shows
  them all (pickers, file fields, colours, several outputs, extra run dots like a Loop's stop, ...). What each
  one does: the table in `docs/ai/code/action.md`. The toolbox's own boxes (Loop, End, Wait, ...) use nothing
  a Box class can't.
- An option that needs the box's own data (a picker that asks the program) is set in `__init__`:
  `self.options = {"color": self.color_names}`.
- While it runs in a flow: `self.signals()` (what arrived at its `entries`, e.g. a stop) and
  `self.started_again()` (with `retrigger`: a new start of the flow stretches its wait).

### A trigger

```python
class LampBlinked(Trigger):
    event = "blinked"                   # its full name is "my_thing.blinked"
    title = "Lamp blinked"              # its name in the Add trigger window
    fields = ("times", "color")         # the dots a flow wires from

# in register():  blinked = LampBlinked(); ctx.add(blinked)
# when it happens: blinked.fire({"times": 3, "color": "red"})
```

### A connection

How to write one: `docs/ai/code/connection.md` and `plugins/example/lib/lamp_connection.py`. Its `id` must be
the plugin's id (it names its settings table in toolbox.toml and its boxes); one per plugin. Its `boxes()`
gives its Box classes: their names get the id in front by themselves, and they are hidden while it is off.

### What a plugin can use

| ctx. | what it does |
|---|---|
| `run_action(name, **params)` | run any toolbox action: `await ctx.run_action("obs.switch_scene", scene="Desktop")` |
| `has_action(name)` | whether an action exists right now (e.g. SAMMI's only while its connection is loaded) |
| `ask_yes_no(question, timeout)` | a yes/no popup on every open toolbox screen; None if nobody answers |
| `secret(name, label, hint)` | a key, token or password: a field on the plugin's card under Plugins where the streamer types it (never shown again, kept in `config/secrets/<id>_<name>.txt`, encrypted while a login is set). `.read()` gives it or says where to type it; `.hide(text)` takes it out of a text before it is shown or logged |
| `settings()` / `save_settings(values)` | the plugin's settings: `resources/settings.json` are the defaults, what the streamer changes is kept in `config/plugins/<id>.json` (so replacing the plugin folder keeps them) |
| `resources` / `resource_url(name)` | the `resources/` folder, and a file's URL for the GUI: `ui.image(ctx.resource_url("logo.svg"))` |
| `add_static(folder)` | serve another folder; the URL is `/plugin-static/<id>` |
| `add_json_boxes(folder, send, kinds)` | boxes for your own program written as JSON: each is one request with fields, and running it calls your `async send(request, data)` ("Boxes written as JSON" in `docs/ai/code/action.md`) |
| `add_web_boxes(folder)` | web boxes (see below) from a folder of your choice |
| `plugin_id` | the plugin's id |

Plugins load before the connections add their boxes: call `run_action` / `has_action` when the plugin is used
(a button, a tool opening), not inside `register`. A plugin's own connection gets its saved settings right
after `register`, so don't read them in its `__init__`.

## A plugin without code

`plugin.json` and a `boxes/` folder, nothing else. Every `*.json` file in `boxes/` holds boxes that call a web
API:

```json
{
  "group": "Jokes",
  "boxes": [
    {
      "name": "of_type",
      "label": "Joke of a type",
      "help": "Gets a random joke of one type",
      "target": {"method": "GET", "url": "https://official-joke-api.appspot.com/jokes/{type}/random"},
      "input": [{"name": "type", "kind": "choice", "choices": ["general", "programming", "dad"]}],
      "output": {"setup": "0.setup", "punchline": "0.punchline"}
    }
  ]
}
```

- **target**: where it goes. `url` (http:// or https://), `method` (GET, POST, PUT, PATCH, DELETE; default
  GET), maybe `headers` (`{"Authorization": "Bearer {secret.key}"}`).
- **input**: the box's fields. Each has a `name`, and maybe `kind` (`text` (default), `number`,
  `whole_number`, `yes_no`, `color`, `list`, `object`, `file`, or `choice` with `choices`), `label`, `hint`,
  `optional`, `default`, `send_as` (the API's own name for it).
  - `{name}` in the url or a header is that field's value.
  - The other fields are sent: after the `?` for GET and DELETE, as a JSON body for the rest.
  - An optional field left empty isn't sent; one that isn't optional must be filled in.
- **keys**: `{secret.name}` in the url or a header is a key the streamer types on the plugin's card under
  Plugins (a field appears there by itself). It is never in the file and never in a box, and it is taken out
  of error messages. The file may say how the field reads:
  `"secrets": {"key": {"label": "API key", "hint": "On your account page → API"}}` (next to `"boxes"`).
- **output**: the box's data dots, and where each value is in the answer: `"punchline"`, `"items.0.name"`
  (a dot between steps, a number for the place in a list). Without `output`, the box has one dot, `answer`,
  with the whole answer.
- Web boxes are only for flows (anything that sends web requests is). An answer of 400 and up fails the box
  with the status and the start of the answer.
- A wrong file stops the plugin with the file, the box and what's wrong on the Plugins page.

`plugins/jokes/` is a whole one. A plugin with code can have web boxes too: `ctx.add_web_boxes(folder)`.

## Installed plugins (pip)

A package can also register a plugin with the entry point group `streamer_toolbox.plugins`
(`name = "package.module:PluginClass"`). It has no resources folder (`ctx.resources` is None).

## Turning plugins on and off

**The switch on the Plugins page** turns a loaded plugin off or on, at once, without a restart. Off stops
everything of it: its `stop()` is called and its connection stops; its boxes don't run, also in your flows
(the flow stops at that box and says the plugin is off); its triggers start no flow; its listeners hear
nothing; its tool, cards, page and connection tab are gone; it isn't offered in Add box or Add trigger. Your
flows keep its boxes and triggers: switch it on again and everything works as before (its `start()` is
called, its connection starts if it was on). (Kept in `config/plugins_off.json`.)

**Not loading a plugin at all**: without a `[plugins]` table in `config/toolbox.toml` every plugin found
loads. With `[plugins] enabled = ["hello", "sammi_decks"]` only those do; a flow's box from a plugin that
isn't loaded stops that flow.

## The older way (api_version 1 to 3)

Before api_version 4, everything was added with its own ctx call, and a box's options were keywords. These
still work, so older plugins keep loading; new plugins use the classes and `ctx.add`.

| older | now |
|---|---|
| `ctx.add_action(name, handler, description, label, **box)` | a `Box` class |
| `ctx.add_trigger(event, title, fields, ...)` + `ctx.publish(event, data)` | a `Trigger` class + `fire(data)` |
| `ctx.add_connection(c)` | `ctx.add(c)` |
| a connection's `add_actions(actions)` | its `boxes()` |
| `ctx.add_tool` / `add_page` / `add_panel` | a `Tool` / `Page` / `Panel` class |
| `ctx.on_event(handler)` | a `Listener` class |
| `ctx.add_field_editor(kind, editor)` | `ctx.add(EditorClass)` with `kind` set |
| `ctx.add_router(router)` | `ctx.add(router)` |
| `ctx.box_signals()` / `ctx.retrigger()` | `self.signals()` / `self.started_again()` in the Box |
