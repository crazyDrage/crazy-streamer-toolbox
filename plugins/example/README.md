# The example plugin: a tour

This plugin adds one of everything a plugin can add. Its "program" is a pretend lamp, so it works with
nothing installed. Copy the folder, rename it, and delete what you don't need.

## Try it first

1. Restart the toolbox (plugins are read at start).
2. **Connections → Example lamp → Connect.** It is off until you do, like every connection.
3. **Tools → Example lamp**: set a colour, press Blink.
4. **Flows → New flow → Add box → Example lamp**: add "Blink lamp", press Test run.
5. A second flow: under Triggers press **Add trigger** and pick **"Example lamp blinked"** (group
   "Example"; its colour field is a dropdown), add any box behind it (a popup, a sound). Now blink the lamp
   from the tool: the second flow starts.

## The folder

```
plugins/example/
  plugin.json              who the plugin is (id, name, version)
  main.py                  THE ENTRY POINT: register(ctx) adds everything, numbered 1 to 9
  lib/
    pretend_lamp.py        the "program". In a real plugin: the class that talks to it
    lamp_connection.py     the connection: its tab, Connect, start / stop
    lamp_actions.py        the boxes
    lamp_tool.py           the page under Tools and the card on Live
    event_counter.py       listens to the toolbox's events
  resources/
    settings.json          default settings
    lamp.svg               a picture
```

One class per file, and the file is named after the class. Inside the plugin, import with a dot:
`from .lib.pretend_lamp import PretendLamp` (in `lib/`: `from .pretend_lamp import PretendLamp`).

## How the pieces talk to each other

```
            you press Connect            a flow runs a box            the lamp blinked
                  │                            │                            │
        LampConnection.test/start        LampActions.blink ──────► ctx.publish("blinked", …)
                  │                            │                            │
                  └────────► PretendLamp ◄─────┘                  flows with that trigger start
                           (the program)
```

- **`PretendLamp`** knows the lamp and nothing about the toolbox.
- **`LampConnection`** is what the toolbox knows: a tab, settings, on / off, a status.
- **`LampActions`** are the things a flow can do with the lamp. The connection hands them out.
- **`main.py`** wires them together and adds the rest.

## What `ctx` can do (the numbers are the comments in `main.py`)

| # | You want | You write | Where it shows |
|---|---|---|---|
| 1 | something that starts a flow | `ctx.add_trigger("blinked", "Example lamp blinked", fields=(...), choices=(...))` and later `ctx.publish("blinked", {...})` | Triggers → Add trigger (group "Example") |
| 2 | a program with its own tab | `ctx.add_connection(LampConnection(...))` | Connections |
| 3 | a box | `ctx.add_action("shout", shout, "what it does", label="Shout")` | Add box, Live, SAMMI deck, API |
| 4 | to ask yes / no | `await ctx.ask_yes_no("Blink?")` | a popup on every open screen |
| 4 | to run another action | `await ctx.run_action("obs.switch_scene", scene="Desktop")` | |
| 5 | to hear what happens | `ctx.on_event(handler)` | |
| 6 | a tool under Tools | `ctx.add_tool("Example lamp", builder)` | Tools |
| 6 | a card | `ctx.add_panel("Example lamp", builder, section="live")` | Live, Connections or Settings |
| 6 | a page of your own | `ctx.add_page("Example plugin", builder)` | the menu |
| 7 | an address for other programs | `ctx.add_router(router)` | `/api/plugins/example/lamp` |
| 8 | to remember something | `ctx.settings()`, `ctx.save_settings({...})` | `config/plugins/example.json` |
| 9 | a picture or other file | `ctx.resource_url("lamp.svg")` | from `resources/` |

## A box, in short (`lib/lamp_actions.py`)

```python
async def set_color(self, color: str) -> dict[str, str]:      # parameters = the box's fields
    self._need_on()                                           # refuse clearly while the lamp is off
    before = self._lamp.set_color(color)
    return {"color": self._lamp.color, "before": before}      # the result other boxes can wire from
```

and its registration:

```python
actions.add("example.set_color", self.set_color, "Changes the lamp's colour", "Set lamp colour",
            options={"color": self.color_names},              # a picker for the field
            outputs={"color": "text", "before": "text"},      # the result's keys, as dots on the box
            hints={"color": "One of the lamp's colours"})     # one line of help under the field
```

More a box can have (`group`, `live`, `files`, several outputs with `ports`, ...): the table in
`docs/ai/code/action.md`.

## A connection, in short (`lib/lamp_connection.py`)

| The toolbox asks | You answer in |
|---|---|
| Who are you? | `id`, `title`, `icon` |
| What do you need to know? | `fields()` |
| Can you reach the program? (the Connect button) | `test(settings)` → a `ConnectionStatus` |
| Go / stop | `start()`, `stop()` |
| What can you do? | `add_actions(actions)` |

Rules: off until the streamer presses Connect. `start()` never raises; a problem goes into the status.
A box of a switched-off connection raises `NotConnectedError` with words that say where to switch it on.

## From here to a real program

Replace `PretendLamp` with a class that really talks to the program. Good ones to copy from the toolbox:

- web requests to a program on the PC: `src/streamer_toolbox/connections/firebot_connection.py`
- a websocket that stays open, with answers and events: `connections/websocket/request_socket.py` and
  `connections/tits_connection.py`
- a token or key in its own file: `core/connections/secret_file.py`

## Testing without the toolbox

`tests/plugins/test_example_plugin.py` loads this plugin with a stand-in for `ctx` and runs its boxes:

```
$env:PYTHONPATH = "src;."; .venv\Scripts\python.exe -m unittest tests.plugins.test_example_plugin
```

## When it doesn't load

The toolbox's **Plugins** page lists every plugin with the reason it failed. More: `docs/PLUGINS.md` and
`docs/ai/plugin/check.md`.
