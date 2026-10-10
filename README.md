# crazy-streamer-toolbox

> **AI agents should read [llms.txt](llms.txt) instead.**
>
> This software is made with the help of AI: the code is written with Claude Code.

One program for the things a stream needs glued together: buttons that do something in OBS, VTube Studio,
SAMMI, Mix It Up or on Twitch, flows that run when a viewer follows, subscribes or redeems, and alerts and
widgets on stream. You build everything by clicking; no code.

It runs on your own PC and shows its pages in a window or in your browser. Nothing is sent to a server of
ours: there is none.

## [⬇ Download crazy-streamer-toolbox][download]

| | |
|---|---|
| **Windows** (64 bit) | [crazy-streamer-toolbox-windows.zip][download-windows] |
| **Linux** | [crazy-streamer-toolbox-linux.zip][download-linux] |
| Every version | [Releases][releases] |

**Still in testing.** Most of it has not been tried by anyone but its author yet. Settings → What you see
starts on "Tested" and shows only what was checked; "Everything" shows all of it.

License: [Apache 2.0](LICENSE). If you pass it on or build on its code, keep the [NOTICE](NOTICE) file with it.

## Install

Nothing is installed on your PC. The toolbox lives in its own folder; to remove it, delete the folder.

### Windows

1. Download the Windows archive and unpack it anywhere you like (not inside `Program Files`: the toolbox
   writes its settings into its own folder).
2. Double-click **Start streamer-toolbox.bat**. It opens in its own window; closing the window stops it.
   **Start in the browser.bat** opens it as a browser tab instead.
3. The first time, Windows may show "Windows protected your PC": *More info* → *Run anyway*.

Python and every library it needs are in the archive.

### Linux

It was started on Ubuntu 24.04 without a screen (the pages answer), but not yet used on a real Linux desktop.

1. You need `python3` 3.12 or newer with `venv`, and a C compiler. On Debian / Ubuntu:
   `sudo apt install python3-venv python3-dev gcc`
2. Download the Linux archive, unpack it and run `./start-linux.sh` in its folder
   (`./start-linux-browser.sh` for a browser tab).
3. The first start gets the libraries from the internet into a `.venv` folder inside the toolbox's folder.

### What next

The archive's `README.md` is the user guide ([docs/USER_GUIDE.md](docs/USER_GUIDE.md) here): connecting
your programs, the first flow, alerts, widgets, backup.

## Help us testing the tool

Every box, trigger, tool and connection has a row in the test record, [docs/tested](docs/tested/README.md),
with three checks: **Works**, **Understandable**, **Usable**. Most rows are still empty.

1. In the toolbox: Settings → What you see → **Testing mode**. It shows only what still misses a check.
2. Pick something you use anyway (your OBS scenes, a Twitch redeem, an alert) and try it.
3. Tell us what happened in an [issue][issues]: the name of the box or trigger, what you did, what you
   expected, what you saw. "It works" is as useful as "it doesn't".

Please test on a testing profile or scene collection, not while you are live.

With the source code (see below) there is also a **test window** that lists every row and writes your ticks
into `docs/tested`, and a **test toolbox** with a ready flow for every box:
`docs/tested/test-window.bat` and `docs/tested/test-toolbox.bat` (Linux: the `.sh` files next to them).

## Help us improve the tool

Ideas, bugs and questions go into an [issue][issues]. For code:

1. Get the source and its libraries (Python 3.12 or newer):

   ```
   git clone <this repository>
   cd crazy-streamer-toolbox
   py -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   On Linux: `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt`

2. Start it with `start.bat` (Linux: `./start.sh`), and run the tests. They need no OBS and no accounts;
   every program is faked:

   ```
   $env:PYTHONPATH = "src;."; .venv\Scripts\python.exe -m unittest discover -s tests -t .
   ```

   On Linux: `PYTHONPATH=src:. .venv/bin/python -m unittest discover -s tests -t .`

3. Work on a branch and open a pull request. A branch named `test/<something>` gets the tests and both
   packages built by GitHub on every push; so does `main`.

The code rules are short: interfaces are `abc.ABC` classes in their own files, one class per file (tests and
fakes too), `pathlib` for paths, PEP 8, and it has to work on Windows and Linux.

| To read | |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | how the pieces fit, the folder map, how to add a connection |
| [docs/manual/dev/build.md](docs/manual/dev/build.md) | building the downloads yourself |
| [docs/manual](docs/manual/index.md) | the manual's source: user, plugin creator, tool developer |
| [llms.txt](llms.txt), [docs/ai](docs/ai/rules.md) | the same for AI agents, in small files |

## Plugin

A plugin is a folder in `plugins/` that adds its own boxes, triggers, connections, Tools tabs, pages or API
routes, without touching the toolbox's code. The toolbox finds it at start; the Plugins page shows what
loaded and why something didn't.

```
plugins/my_thing/
  plugin.json        info about the plugin
  main.py            the entry point: one class, register(ctx) adds everything
  lib/               the plugin's other Python classes
  resources/         pictures, default settings, JS, ...
```

- Start with [plugins/example](plugins/example/README.md): a guided tour with one of everything.
- [plugins/hello](plugins/hello) is the smallest one, [plugins/sammi_decks](plugins/sammi_decks) a real tool.
- The guide: [docs/PLUGINS.md](docs/PLUGINS.md).

[download]: https://github.com/crazyDrage/crazy-streamer-toolbox/releases/latest
[download-windows]: https://github.com/crazyDrage/crazy-streamer-toolbox/releases/latest/download/crazy-streamer-toolbox-windows.zip
[download-linux]: https://github.com/crazyDrage/crazy-streamer-toolbox/releases/latest/download/crazy-streamer-toolbox-linux.zip
[releases]: https://github.com/crazyDrage/crazy-streamer-toolbox/releases
[issues]: https://github.com/crazyDrage/crazy-streamer-toolbox/issues
