# Problem prevention

Things crazyDrage asked to check and fix **before** they go wrong on stream.

- `wip/`: problems being worked on (something is still open).
- `finished/`: problems that are prevented and tested; nothing open.
- `CURRENT.md`: what is being worked on right now.

One file per problem, numbered (the number stays when it moves). Each says:

- **The problem**: what could go wrong, in plain words.
- **What we found**: how it was checked, with numbers.
- **What prevents it now**: what was built, and where the code is.
- **How to check it again**: a test or a command that shows it still works.
- **Still open**: what isn't covered yet (empty in `finished/`).

When he names a new "check this before it happens", it gets a file in `wip/` and a line below.

| # | Problem | Where |
|---|---|---|
| 01 | [The alerts / widget overlay loses its line to the toolbox](wip/01_overlay_line_drops.md) | wip |
| 02 | [Tokens and keys readable on disk](finished/02_keys_on_disk.md) | finished |
| 03 | [The toolbox uses too much power on the streaming PC](wip/03_toolbox_uses_too_much.md) | wip |
| 04 | [A program doesn't connect, or connects badly](finished/04_connections_dont_connect.md) | finished |
| 05 | [The flow editor loses what he typed, or doesn't do what he clicked](finished/05_flow_editor_loses_input.md) | finished |
| 06 | [A flow runs forever and can't be stopped](finished/06_flow_runs_forever.md) | finished |
| 07 | [A widget's code sends data away or takes over the page](finished/07_widget_code_sends_data_away.md) | finished |
| 08 | [An imported widget shows nothing, or empty names](finished/08_widget_shows_nothing.md) | finished |
| 09 | [The alert editor doesn't do what he set](finished/09_alert_editor_does_nothing.md) | finished |
| 10 | [The toolbox window or browser does something unexpected](finished/10_window_and_browser.md) | finished |
| 11 | [A box gives back something that doesn't fit the next box](finished/11_box_gives_confusing_results.md) | finished |

04-11 are what he found and told me (rounds 3-64), gathered on 2026-10-29 from `temp/feedback/`. Not in the
list: wishes and new ideas (those are features, not problems), and what wasn't fixed (VTube Studio pins
an item by its middle: VTS's API has no other point; parked in round 37).
