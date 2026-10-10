# Starting the toolbox, and checking that it runs

## Is it running?

`GET http://127.0.0.1:8850/actions` from the same PC. An answer (200, or 401 / 403) means it runs. No
connection means it doesn't, or it uses another port: `[api] port` in `config/toolbox.toml`.

## Starting it

Ask the streamer first if they may be live: a start connects to their programs.

| Where you are | How |
|---|---|
| The packed archive (a folder with `python/` in it) | `Start streamer-toolbox.bat` (own window) or `Start in the browser.bat` |
| The repository | `start.bat` or `start-browser.bat` |
| Without a window (for an agent) | add `--open none`, e.g. `start.bat --open none` |
| By hand, repository, PowerShell | `$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m streamer_toolbox --open none` |

Options: `--port 8851` (overrides the settings file), `--config <path to a toolbox.toml>`,
`--plugins <folder>`, `--open none|browser|window`.

It is ready when `GET /actions` answers; that takes a few seconds. Closing the toolbox's own window stops it.

## What a start does

- Reads `config/toolbox.toml`. Without that file: listens on 127.0.0.1:8850 only, loads every plugin, lets
  anything on this PC call the API without a token.
- Connects to every connection that is switched on. All are off until the streamer pressed Connect on the
  connection's tab once, so a fresh toolbox talks to nothing.
- The dashboard is at `http://127.0.0.1:8850/`. It is made for people; use the API (`docs/ai/use/api.md`).

## Settings

`config/toolbox.example.toml` shows every setting with a comment. A change in `toolbox.toml` needs a restart
(Settings → Restart in the dashboard), except what the dashboard's Connections tabs save themselves.

All the streamer's data is inside the toolbox's folder (`config/`). Nothing is installed on the PC.
