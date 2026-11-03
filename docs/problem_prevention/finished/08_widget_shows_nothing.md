# 08 · An imported widget shows nothing, or empty names

## The problem

A widget that works on StreamElements is imported, and in the toolbox it stays empty or shows blank
"latest follower / sub" labels on stream.

## What he told me, and what was wrong

| When | His words | What was wrong |
|---|---|---|
| round 25, 10-03 | the multichannel chat widget "doesn't work here, it does on StreamElements" (chat) | Its code uses jQuery (`$`); StreamElements' page brings jQuery, the toolbox's didn't, so the code stopped at the first message |
| round 27, 10-03 | "Some data can't be loaded in the widget, for example `{event.data.currency}`" | The `{...}` names were fine; the labels were empty because the toolbox only knew followers / subs / tips it had seen itself since it started |
| round 29, 10-04 | "anime_theme_package_stream_ended still doesn't show the latest sub name" (chat) | Twitch has no "latest subs" list, and the toolbox had seen none yet |

## What prevents it now

| What | How | Code |
|---|---|---|
| What StreamElements' page brings, the toolbox's brings too | jQuery is on every widget page (a file of the toolbox, no internet needed); chat messages say which channel they're from | `core/widgets/widget_page.py` |
| The latest follower is right from the start | it comes from Twitch itself | `core/widgets/latest_followers.py` |
| The latest sub / cheer / raid / tip | kept across restarts once seen; Overlay → Import → **Latest names** asks StreamElements once and never replaces what the toolbox saw itself | `streamelements_importer.py` |
| Subs missed while the toolbox was off | compared with Twitch's sub list and written into the record | `core/widgets/missed_subscribers.py` |

## How to check it again

- Tests: `tests/core/widgets/` (session, latest followers, missed subscribers, widget page).
- Import a widget and open its preview: the names must be filled, the chat must show a test message.
