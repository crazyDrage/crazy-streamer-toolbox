# Adding a connection (the toolbox talks to a new program or service)

Read `docs/ai/code/rules.md` first. Good small examples to copy: `connections/vnyan_connection.py` (send
only), `connections/rumble_connection.py` (reads, publishes events), `connections/sammi_connection.py` (an
HTTP API with pickers).

## Steps

1. `connections/<id>_connection.py`: `class <Name>Connection(ConnectionBase)` with
   - `id` (also its table in `toolbox.toml` and its tab), `title`, `icon` (a Material icon name);
   - `__init__`: `super().__init__({<default settings>}, settings)`. `enabled` is added for you and is
     **off** by default: a connection never talks to anything until the streamer pressed Connect;
   - `fields()`: what the tab asks for (`SettingField`; `secret=True` for passwords and tokens);
   - `start()`, `stop()`, `test(settings)`. `test` returns a `ConnectionStatus` and may ask the streamer
     something once (a login, a pairing popup). `start` never does, and never raises: a failure goes into
     the status;
   - `add_actions(actions)`: its boxes, named `<id>.<what>`, each with a `group` (see
     `docs/ai/code/action.md`);
   - `retry_when_down = True` if it should connect by itself once the program is started later.
2. Everything else it needs goes into `connections/<id>/`, one class per file: the client, the actions class,
   the event mapping.
3. Add it to the `ConnectionManager([...])` list in `__main__.py`, giving it `config.tables.get("<id>", {})`.
4. Events: take the `EventBus` in `__init__`, `publish("<id>.<what>", {...})`, and list the event's fields
   (`docs/ai/code/events.md`).
5. Tests: `tests/connections/test_<id>_connection.py`, the service faked. Pass `"enabled": True` in the test's
   settings.
6. Docs: a line in `docs/USER_GUIDE.md` (what the streamer has to switch on in the program), the folder map in
   `docs/ARCHITECTURE.md`.

The Connections page gets the tab by itself. Settings are saved into `[<id>]` in `toolbox.toml` when Connect
succeeds.

## How it has to behave

- An action of a switched-off connection raises `NotConnectedError` with words the streamer can act on
  ("X is switched off under Connections → X").
- An action of a connection that is on but failed tries again, so a program started after the toolbox works.
- Secrets (tokens, keys) go into their own file next to the settings (`config/<id>_token.txt`), never into
  `toolbox.toml`, never into a log or an error text.
- New permissions on the streamer's account (scopes, write access) are asked at Connect and are the
  streamer's decision; don't make them required for what already works.
- If you couldn't try it with the real program, say so in the class's docstring and on its tab, and name
  what is a guess.

## A REST service with many answers

`devtools/box_gen` writes the answer dataclasses, the actions class, a fake and a test from a JSON spec with
example answers: `docs/PLAN_box_maker.md`.
