# streamer-toolbox

> **AI agents should read [llms.txt](llms.txt) instead.**
>
> This software is made with the help of AI: the code is written with Claude Code.

License: [Apache 2.0](LICENSE). If you pass it on or build on its code, keep the [NOTICE](NOTICE) file with it.

Python tools that take over SAMMI / Mix It Up logic step by step. How the pieces fit: `docs/ARCHITECTURE.md`.

Code rules: interfaces are `abc.ABC` classes in their own files, one class per file (tests too).

For people who just want to use it: `docs/USER_GUIDE.md`. The archive to send them (own Python, every
library, a start script to double-click) is built with
`$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m streamer_toolbox.devtools.package` → `build/streamer-toolbox.zip`.

The docs as their own download (the manual as web pages, three parts: user, plugin creator, tool developer;
plus the files for AI agents): `.venv\Scripts\python.exe -m pip install -r requirements-docs.txt` once, then
`$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m streamer_toolbox.devtools.package docs` →
`build/streamer-toolbox-docs.zip`. The manual's source is `docs/manual/`.

Setup: `.venv\Scripts\python.exe -m pip install -r requirements.txt` (not while live).

Run the toolbox (GUI + HTTP API, http://127.0.0.1:8850 by default) by double-clicking:

- `start.bat`: opens the dashboard in its own window (Edge or Chrome app window; a browser tab if neither exists).
- `start-browser.bat`: opens the dashboard as a tab in the default browser.

Closing the dashboard keeps the toolbox running for SAMMI and Kit; close the console window to stop it. Both
scripts pass extra options on (`start.bat --port 8851`, `start.bat --open none`). Without the scripts:

```
$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m streamer_toolbox [--open browser|window]
```

Settings live in `config/toolbox.toml` (gitignored, holds tokens); copy `config/toolbox.example.toml` to start.
Without it the toolbox listens on 127.0.0.1 only, loads every plugin, lets anything on this PC call, and has OBS off.

- `[plugins] enabled`: which plugin ids load (others show as "disabled" on the Plugins page).
- `[callers.<name>]`: who may call the API. `token = "..."` (sent as `Authorization: Bearer ...` or
  `X-Toolbox-Token`) or `local = true` (from this PC, no token; refused if the request carries a browser `Origin`).
  `allow` = action names or patterns (`"hello.*"`, `"*"`); callers only see and run those, anything else is 404.
- `[obs]`: off by default. With `enabled = true`, each `[obs.fit.<name>]` becomes an action
  `obs.fit_<name>(video_path)`. The toolbox connects to OBS only when such an action runs, never at startup.

- `POST /action/<name>` (optional JSON body = parameters, read as JSON whatever the Content-Type) runs an action;
  `GET /actions` lists the caller's actions with their parameters.
- SAMMI deck: with the toolbox running, `$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m streamer_toolbox.connections.sammi`
  writes `build/sammi_toolbox_deck.json` (one HTTP Request button per action; required parameters are sent as SAMMI
  variables of the same name, e.g. `/$video_path$/`). Import it in SAMMI with Paste Deck. The Connections page
  also has Copy deck / Download deck file buttons, without the command line.

GUI areas (sidebar on desktop, bottom tabs on phone and tablet):
- **Live**: every action as a big button, grouped by plugin; actions that need a value ask for it first. Recent
  runs (from the GUI, SAMMI or Kit) on the side. The yes/no question pops up on every open screen.
- **Connections**: one sub-tab each. Toolbox (API address, callers and tokens, New token helper; changed in
  `config/toolbox.toml`, then restart), then OBS, SAMMI (with the deck), Mix It Up, VTube Studio: status,
  on/off, **Connect** (tests, then saves and connects; no restart).
- **Tools**: one tab per tool a plugin adds (SAMMI decks: your decks as buttons).
- **Plugins**: one card per plugin (loaded, failed with the reason, or disabled).
- **Settings**: theme (dark, light, like the device) and where the settings file is.

- Plugins live in `plugins/<id>/`: `plugin.json` (info), `main.py` (the one `ToolboxPlugin`, whose `register(ctx)`
  adds everything: actions, Tools tabs, pages, panels, API routes), `lib/` (other classes) and `resources/`
  (pictures, default settings). Guide: `docs/PLUGINS.md`; examples `plugins/hello/` and `plugins/sammi_decks/`.
  A plugin that fails to load is
  listed on the Plugins page and skipped.

Folder map and how to add a connection: `docs/ARCHITECTURE.md`.

Run the tests (no OBS connection needed; OBS calls are faked):

```
$env:PYTHONPATH = "src;."; .venv\Scripts\python.exe -m unittest discover -s tests -t .
```
