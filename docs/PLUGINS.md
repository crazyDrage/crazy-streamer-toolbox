# Writing a plugin

A plugin is a folder in `plugins/`. The toolbox finds it at start (restart after adding or changing one).
The Plugins page shows what loaded and why something didn't.

```
plugins/my_thing/
  plugin.json        info about the plugin
  main.py            the entry point: one class, register(ctx) adds everything
  lib/               the plugin's other Python classes
  resources/         pictures, default settings, JS, ... (served to the GUI)
```

Plugins are kept apart from the toolbox's own repository. The example plugins are planned as a repository of
their own: `example` (a guided tour: one of everything, with a README that walks through it; start there),
`hello` (the smallest), `sammi_decks` (a real tool: SAMMI decks as buttons).

## plugin.json

```json
{
  "id": "my_thing",
  "name": "My thing",
  "version": "0.1.0",
  "api_version": 2,
  "description": "What it does, one sentence",
  "author": "you"
}
```

- `id`: lowercase letters, digits and `_`. It's the folder's package name and the start of its actions
  (`my_thing.do_it`).
- `api_version`: 2 (1 still loads; 2 added connections, triggers, events and full boxes). A plugin made for
  a newer version than the toolbox knows isn't loaded (the Plugins page says why).
- Optional: `"main": "start.py"` if the entry file isn't `main.py`; `"class": "MyPlugin"` if main has more
  than one plugin class.

## main.py: the one entry point

Everything the plugin adds to the toolbox is collected in `register(ctx)`:

```python
"""The plugin's entry point: everything it adds to the toolbox is collected in register()."""
from streamer_toolbox.core.interfaces.plugin_context import PluginContext
from streamer_toolbox.core.interfaces.toolbox_plugin import ToolboxPlugin

from .lib.board import Board


class MyThingPlugin(ToolboxPlugin):
    def register(self, ctx: PluginContext) -> None:
        async def do_it(name: str = "chat") -> str:
            return f"did it for {name}"

        ctx.add_action("do_it", do_it, "What it does", label="Do it")      # a box in flows, a Live button, SAMMI
        ctx.add_tool("My thing", lambda: Board(ctx).build(), icon="build")  # a page under Tools
```

- Exactly one class in `main.py` must extend `ToolboxPlugin` (or name it in plugin.json).
- Classes in `lib/` are imported relatively: `from .lib.board import Board`; inside `lib/`: `from .other
  import Other`. One class per file, like the toolbox itself.
- A plugin that crashes while loading is skipped and shown on the Plugins page; the toolbox keeps running.

## What ctx can do

| ctx. | what it does |
|---|---|
| `add_action(name, handler, description, label, **box)` | an action `<id>.<name>`: a box in flows, a button on Live, callable from SAMMI / the API. Its parameters become the box's fields. `**box`: what a box can have besides (`group`, `options` = pickers, `outputs`, `hints`, `labels`, `files`, `ports`, `live`, `flow_only`; the table in `docs/ai/code/action.md`) |
| `add_json_boxes(folder, send, kinds)` | boxes without Python: every `*.json` file in `folder` holds boxes that are one request with fields each (the file's shape and the value kinds: "Boxes written as JSON" in `docs/ai/code/action.md`). Running a box calls your `async send(request, data)`. `kinds`: your own `ValueKind`s next to the global ones |
| `add_connection(connection)` | a program the toolbox talks to: its own tab under Connections, settings in `[<id>]` of toolbox.toml, on / off, started with the toolbox, its boxes hidden while it is off. A `ConnectionBase` subclass whose `id` is the plugin's id; one per plugin. How to write one: `docs/ai/code/connection.md` and `plugins/example/lib/lamp_connection.py` |
| `add_trigger(event, title, fields, icon, pick, example, description, choices)` | makes `<id>.<event>` something a flow can start on: `title` and `description` show in the Add trigger window, `fields` are the dots to wire from, `pick` is the field a trigger is matched on and `choices` (a list, or an async function that returns one) makes that input a dropdown |
| `publish(event, data)` | says that `<id>.<event>` happened: flows with that trigger start |
| `on_event(handler)` | hear every event of the toolbox: `async handler(kind, data)` |
| `add_tool(title, builder, icon, description)` | a tool under **Tools** (a card on its overview, an item in the side menu, its own page); `builder()` draws it with NiceGUI each time it opens |
| `add_page(title, builder, subpath, icon)` | a page of its own at `/plugins/<id>`, listed in the menu |
| `add_panel(title, builder, section)` | a card on Live, Connections or Settings |
| `add_router(router)` | FastAPI routes under `/api/plugins/<id>` |
| `run_action(name, **params)` | run any toolbox action: `await ctx.run_action("sammi.trigger_button", button_id="ID24")`, `"obs.switch_scene"`, `"flow.desktop"`, ... |
| `has_action(name)` | whether an action exists right now (e.g. SAMMI's are there only while its connection is loaded) |
| `resources` / `resource_url(name)` | the `resources/` folder, and a file's URL for the GUI: `ui.image(ctx.resource_url("logo.svg"))` |
| `settings()` / `save_settings(values)` | the plugin's settings: `resources/settings.json` are the defaults, what the streamer changes is kept in `config/plugins/<id>.json` (so replacing the plugin folder keeps them) |
| `ask_yes_no(question, timeout)` | a yes/no popup on every open toolbox screen; None if nobody answers |
| `add_static(folder)` | serve another folder (resources/ already is); also while running: the URL is `/plugin-static/<id>`, not under /static (that mount would hide it) |

Plugins load before the connections add their actions: call `run_action` / `has_action` when the plugin is
used (a button, a tool opening), not inside `register`. A plugin's own connection gets its saved settings
right after `register`, so don't read them in its `__init__`.

## Resources

- `resources/settings.json`: the default settings (optional).
- Pictures, JS for your own NiceGUI components (`class Badge(ui.element, component=<path to resources/x.js>)`,
  see `lib/hello_badge.py` of the `hello` example plugin), sounds, ...
- Files the plugin writes at runtime go to settings (`save_settings`), not into resources/.

## Installed plugins (pip)

A package can also register a plugin with the entry point group `streamer_toolbox.plugins`
(`name = "package.module:PluginClass"`). It has no resources folder (`ctx.resources` is None).

## Turning plugins on and off

**The switch on the Plugins page** turns a loaded plugin off or on, at once, without a restart. Off means:
its boxes are no longer offered in Add box and its triggers no longer in Add trigger. The plugin stays
loaded, so the boxes and triggers your flows already use stay and keep working until you delete them. Its
tool, cards and page stay too. (Kept in `config/plugins_off.json`.)

**Not loading a plugin at all**: without a `[plugins]` table in `config/toolbox.toml` every plugin found
loads. With `[plugins] enabled = ["hello", "sammi_decks"]` only those do; a flow's box from a plugin that
isn't loaded stops that flow.
