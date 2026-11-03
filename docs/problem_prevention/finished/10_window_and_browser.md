# 10 · The toolbox window or browser does something unexpected

## The problem

The toolbox runs as its own window, as a tab, and on the tablet. When closing it doesn't close it, links
open in the wrong place, or a page runs old code, he can't trust what he sees.

## What he told me, and what was wrong

| When | His words | What was wrong |
|---|---|---|
| round 12, 09-30 | "the X on the window should close the software, not just the window" | The window was a browser tab; closing it left the toolbox running |
| round 41, 10-08 | "the links open in the software browser, and not in the OS default one" | Links to outside pages opened inside the toolbox's own window |
| round 63, 10-26 | "Full screen does nothing" | The browser still ran the old `live_deck.js`: the toolbox let browsers keep its script files for an hour |
| round 64, 10-27 | Live full screen "has the top part of the tool", "the buttons canvas doesn't fit the screen", "no close button"; then "a border on the side and bottom" | Full screen showed the whole page (header, side list); the grid kept its page size; the close button sat under the header |

## What prevents it now

| What | How | Code |
|---|---|---|
| X closes the toolbox | the app window (start.bat) is its own Edge window; closing it stops the toolbox | `gui/services/app_window_page_opener.py` |
| Outside links open in the default browser | on this PC; on another device (phone) they open there | connection tabs |
| No old scripts | browsers ask for the toolbox's files each time (unchanged = a tiny "not modified") | static files |
| Full screen is only the buttons | header and side list hidden, the grid fills the screen, the close button on top, a small lip opens the pages | `gui/static/live_deck.css`, `live_deck_view.py` |

## How to check it again

- After a change to a script: open the page without a reload, the change must be there.
- Live: full screen, the grid must touch all four edges; the close button must work.
- GUI changes are checked with screenshots (desktop + phone width) before he sees them.
