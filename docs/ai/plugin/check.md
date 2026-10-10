# Plugins: is it one, does it load, does it work

How to write one is in `docs/PLUGINS.md`. Copy `plugins/example/` as a start: it has one of everything and
its `README.md` walks through it (`plugins/hello/` is the smallest one).

## Plugin, or a change to the toolbox?

| Your idea | Where it goes |
|---|---|
| An action (with pickers, outputs, hints), a tool tab, a page, a card, an API route of your own | plugin |
| The toolbox should talk to a new program: its own tab under Connections, its boxes, its events as triggers | plugin (`ctx.add_connection`, `ctx.add_trigger`, `ctx.publish`), `api_version` 2 |
| Glue between actions that already exist | plugin, or just a flow in the dashboard |
| A program that should ship with the toolbox itself | the toolbox's code: `docs/ai/code/connection.md` |
| One of the events every platform has (follow, sub, chat as the common event), alerts for it, a box with its own editor window | the toolbox's code: `docs/ai/code/events.md`, `docs/ai/code/action.md` |

A plugin only gets `ctx` (PluginContext). What it can't do: take anything away again while the toolbox runs
(a changed plugin needs a restart), and add more than one connection.

## It doesn't load

The dashboard's Plugins page lists every plugin: loaded, failed (with the reason) or disabled. The same
reason is in the console the toolbox was started from. Usual causes:

- `plugin.json`: one of `id`, `name`, `version`, `api_version` is missing; `api_version` isn't 1; or `id`
  isn't lowercase letters, digits and `_`, starting with a letter.
- `ctx.add_connection`: the connection's `id` isn't the plugin's id.
- `main.py` has no class that extends `ToolboxPlugin`, or more than one without `"class"` in plugin.json.
- An import inside the plugin isn't relative. Use `from .lib.board import Board`.
- `config/toolbox.toml` has `[plugins] enabled = [...]` and your id isn't in it.
- A library the plugin needs isn't installed in the toolbox's Python.

Plugins are read at start. After any change: restart the toolbox (Settings → Restart).

## Common mistakes

- Calling `ctx.run_action` / `ctx.has_action` inside `register()`. Plugins load before the connections add
  their actions, so nothing is there yet. Call them when the plugin is used (a button, a tool opening).
- Writing files into `resources/`. Use `ctx.save_settings`; it lands in `config/plugins/<id>.json` and
  survives replacing the plugin folder.
- An action that blocks. Handlers are `async`; a long blocking call freezes the whole toolbox.
- A crash in an action is fine: the caller gets the error text. Raise with a message a streamer understands.

## Testing it without the streamer's toolbox

- Unit test: the repository has `tests/fakes/fake_plugin_context.py` (FakePluginContext: records what a
  plugin registers (also its connection, triggers and what it publishes), answers yes/no questions with a
  preset; `tests/plugins/test_example_plugin.py` shows it whole). Build your plugin class, call
  `register(FakePluginContext("my_thing", ActionRegistry()))`, then run the actions through
  `ctx.run_action`.
- Real run on a second port, away from the streamer's settings:
  `python -m streamer_toolbox --port 8851 --config <an empty folder>/toolbox.toml --open none`, then
  `GET http://127.0.0.1:8851/actions` and `POST /action/<id>.<name>` (`docs/ai/use/api.md`). With no settings
  file every connection is off, so nothing reaches the streamer's programs.
