# Before you edit the toolbox's code

Applies to everything under `src/` and `tests/`. Short on purpose; the deep reference is
`docs/ARCHITECTURE.md`.

## Rules

- **One class per file**, named after the class (`flow_runner.py` → `FlowRunner`). Tests and fakes too.
- **Interfaces are `abc.ABC` classes in `core/interfaces/`**, one per file, separate from what implements them.
- Data are (frozen) dataclasses. `pathlib` for paths. PEP 8. No over-engineering: no layer nobody asked for.
- A folder holds one kind of thing. What only one class uses goes in a sub folder named after it
  (`connections/obs/` holds what `obs_connection.py` uses).
- `core/` knows no service. Anything about OBS, Twitch, ... lives under `connections/`.
- Write code like the code around it: its naming, its comment density, plain words in texts the streamer reads.
- A new library goes into `requirements.txt` and is installed into the project's `.venv` only.

## Where things are

```
src/streamer_toolbox/
  __main__.py     startup: builds everything, one place where the pieces are wired together
  core/           shared building blocks (actions, flows, events, alerts, widgets, points, config, ...)
  connections/    one class per service + a sub folder with what it uses
  api/            the HTTP API and the overlay pages' routes
  gui/            pages/, components/, static/, services/
  plugins/        the plugin loader (the plugins themselves are in /plugins)
  devtools/       box_gen (class generator for REST services), package (the archive to send people)
tests/            mirrors src; fakes in tests/fakes/, builders in tests/helpers/
```

## Tests

```
$env:PYTHONPATH = "src;."; .venv\Scripts\python.exe -m unittest discover -s tests -t .
```

- Nothing talks to a real program or service. HTTP services are faked with `httpx.MockTransport`, websockets
  with a small local server (`tests/fakes/fake_*_server.py`), OBS with `FakeConnectableObsClient`.
- Every new class gets a test file at the mirrored path (`tests/core/flows/test_flow_runner.py`).
- If the run hangs, a test waits for a connection that is off: a connection is off unless its settings say
  `"enabled": True`.
- Run the whole suite before you say something works. Say plainly what was only tested against a fake.

## Things that bite

- `config/` is the streamer's: settings, tokens, flows. Never in a test, never in a commit. Tests use
  `tempfile`.
- A connection's `configure()` with a partial dict falls back to the defaults for the rest.
- GUI (NiceGUI): a dialog opened inside a `ui.refreshable` that a timer refreshes is destroyed by the
  refresh; open it in an element outside. After a refresh, don't use `ui.*` calls that need the page from
  the handler of an element inside the refreshed part.
- Objects handed to a page builder are shared by every open page. Keep per-page things local.
- An action handler's parameters are the box's fields and the API's parameters. Renaming one breaks the
  streamer's saved flows.
- What goes into the packed archive is decided in `devtools/package/packager.py` (only tracked files, only the
  listed folders).
