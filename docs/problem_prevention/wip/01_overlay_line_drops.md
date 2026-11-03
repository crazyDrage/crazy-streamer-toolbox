# 01 · The alerts / widget overlay loses its line to the toolbox

His words (2026-10-27): "I am suspecting that the connections between the OBS source and the toolbox alert
drop over time."

## The problem

The alerts page and each widget page in OBS (a Browser source) hold one line (a WebSocket) to the toolbox.
If that line breaks, alerts and events don't show, and nobody notices until a viewer asks.

## What we found

Tested with `temp/alert_soak/soak.py`: a demo toolbox, headless Chrome as the OBS page, and a relay in between
that can freeze or cut the line.

- **A line that drops without a word was never noticed.** A sleeping PC, a router, a VPN or a stalled OBS can
  do that. The page's socket said "open" forever, and every later alert was lost until the source was
  refreshed.
- A toolbox restart was fine: the page was back within 2 s.
- 300 alerts at once: all arrived, in order.
- 24 h tests (alert every 1-20 min, every 3 h, one alert after 24 h of silence): 144 of 144 arrived, the line
  never dropped by itself.
- Memory: about 90 MB at rest, about 111 MB after 1000 alerts, then flat (not a leak).

## What prevents it now

| What | How | Code |
|---|---|---|
| The toolbox says "still here" | `alive` every 15 s when nothing else was sent | `api/overlay_line.py` |
| The page notices a dead line | 40 s without any message: it drops the line and connects again | `gui/static/overlay/alerts.js`, `widget.js` |
| The page reconnects | every 2 s after the line closed | same |
| The toolbox notices a dead page | the page answers every message (`got`); no answer in 1 s ends the line | `api/overlay_line.py` |
| The toolbox knows what didn't arrive | unconfirmed alerts, or alerts with no page listening, are noted: red line on the Overlay page, a warning in the log | `AlertQueue.missed`, `WidgetHub.missed` |
| A page that comes back gets what it missed | every message has a number; the page says its last one and gets the rest (alerts up to 60 s old, widget events up to 10 min, the last 1000 kept) | `core/overlay/sent_messages.py` |
| A refreshed OBS source goes on | the page keeps its last number in the browser | `alerts.js`, `widget.js` |
| A toolbox restart | off (default): the waiting alerts are cleared. Overlay → "Keep alerts through a restart": the line is kept in `alert_backup.json` and goes on with the same numbers | `core/alerts/alert_backup.py` |

## How to check it again

- Tests: `tests/api/test_overlay_line.py`, `tests/core/overlay/test_sent_messages.py`,
  `tests/core/alerts/test_alert_backup.py`, `tests/api/test_overlay_router.py`.
- Freeze and cut, in Chrome (4 min):
  `.venv/Scripts/python.exe temp/alert_soak/soak.py --port 8890 --minutes 4 --every 20 --freeze-at 1 --freeze-for 60 --cut-at 2.5`
  Lost alerts must show up as "reached ... late" in the run's toolbox log.
- A restart with "keep" on: `--restart-at 1`, with `"keep_through_restart": true` in the run folder's `alerts.json`.

## Still open

- Not tried with real OBS yet (needs him there).
- How old an alert may be and still show (now 60 s), and whether the page should give up after 20 s instead
  of 40 s: `temp/feedback/round_64.md`, question 8.
