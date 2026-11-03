# 03 · The toolbox uses too much power on the streaming PC

His words: "does it put load on the computer?" (2026-10-09), "I just want to make sure the toolbox doesn't
need much power" (2026-10-27), "It is important that we don't use too much resources, but still have a
working tool." (2026-10-29)

## The problem

The toolbox runs on the PC that streams. Every bit of processor time or memory it takes is missing for OBS,
the game and VTube Studio, and shows as dropped frames or stutter.

## What we found

- Memory: about 80 MB is only loading the program (Python 8, asyncio 7.5, FastAPI 18, NiceGUI 28, the
  toolbox's own 796 files 18.5); about 90 MB at rest. 1000 alerts: up to 111 MB, then flat (Python keeps what
  it used; not a leak).
- Processor: under 1 % of one core for the toolbox, also with alerts and widgets running.
- The alerts and widgets are drawn by OBS's Browser sources (each a small Chrome page), not by the toolbox.
  One source for everything instead of one per widget would save mostly memory there.

## What prevents it now

| What | How |
|---|---|
| Measure, don't guess | anything that runs often, downloads or starts a program gets processor time, memory and download size in numbers before it is called fine |
| Nothing heavy while he's live | tests, builds and long checks wait until he's off stream |
| Limits on what is kept | the alert line keeps 1000 sent messages (1.5 MB), the activity log 20 runs, missed alerts 20 |
| Web requests in one place | `core/web/web_client.py` |

## How to check it again

- Memory per import step and at rest: `temp/alert_soak/soak.py` writes the toolbox's memory into every line of
  its log; a long run shows whether it stays flat.
- Processor: Task Manager → Details → the `python.exe` that listens on the toolbox's port.

## Still open

- Working first, lean second (his 10-29 words). Later: load connections that are switched off only when they
  are used (about 10-15 MB). `temp/OPEN.md` point 101.
- One Browser source for all widgets (an overlay made of layers): measure in OBS first (`round_64.md`
  question 6).
