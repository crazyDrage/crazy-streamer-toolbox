# 09 · The alert editor doesn't do what he set

## The problem

He sets up an alert in its Settings window (where the words sit, how big the picture is), and the preview
doesn't follow, or shows something that looks like part of the alert. What goes on stream is then a guess.

## What he told me, and what was wrong

| When | His words | What was wrong |
|---|---|---|
| round 25, 10-03 | "On the picture" does nothing; it should spawn the text as a draggable box (chat) | The preview never got the change after the window redrew itself |
| round 26, 10-03 | "I can't resize the picture I added in the resub alert. I can add a percentage, but not resize in the preview window." (chat) | There was no handle; and at 100 % his card was as wide as an alert may be, so the box was taller than the picture and a handle would hang in the empty part |
| round 26, 10-03 | "There is a `still here` under the picture that I can't get away." (chat) | It was the test viewer's example message, which looked like words of the alert |

## What prevents it now

| What | How | Code |
|---|---|---|
| The preview follows every change | each piece of the words can sit on the picture and be dragged in the preview; the spot is saved | `gui/static/overlay/alerts.js` (`?edit=1`), `alert_settings_dialog.py` |
| The picture can be resized in the preview | a round handle on its corner; the box is exactly the picture; words on the picture grow with it | same |
| Examples look like examples | the example message reads "(their message shows here)", and the hint under the preview says name, amount and message are examples | same |

## How to check it again

- Tests: `tests/gui/components/alerts_tool/`, `tests/core/alerts/`.
- Overlay → Alerts → Settings: drag a piece, resize the picture, close and open again: both must stay.
