# 05 · The flow editor loses what he typed, or doesn't do what he clicked

## The problem

Building a flow means many small edits. When a typed name quietly disappears, a click does nothing or the
editor shows something old, the flow that runs on stream isn't the one he built.

## What he told me, and what was wrong

| When | His words | What was wrong |
|---|---|---|
| round 12, 09-30 | "a box can't be deleted, Delete and X don't work" (chat) | The X only closed the panel; the Delete key only worked while the canvas had focus |
| round 12, 09-30 | "the small view of the box graph can't be moved if IO go too much to the right" | The Box window could be dragged out until only its buttons were left, and those can't be grabbed |
| round 13, 09-30 | "the list of `add a box` will close a category the first time I try to open a sub-sub category" | The list only knew the headings opened by that click, so it closed the one around it |
| round 13, 09-30 | "the connection between 2 boxes can't be removed sometimes" | Orange wires are dotted (most clicks hit a gap), and a picked wire didn't change colour |
| round 15, 10-01 | "the small graph in the flow edit screen is still buggy. No idea why it stops moving sometimes" | Dragging only worked on the canvas's own background (not the part that came into view after a zoom), and letting go outside the canvas never ended the drag |
| round 16, 10-01 | "folder creation doesn't work" (chat) | A new folder name only counted after Enter; clicking Move dropped it |
| round 41, 10-08 | Show alert: "if I add a value to the box, it will change the `text` to an input but doesn't connect" | A Start box dot dropped on "by name" pointed the field at all of Start, which has no dot to draw a wire from |
| round 41, 10-08 | StreamSocket event: "the input should not need an enter to confirm" | Trigger fields kept what was typed only on Enter |
| round 44, 10-11 | "changing the triggers should update the start box, and not wait until I load the page again" | The Start box was drawn once, when the flow opened |
| round 45, 10-12 | "the X on the wire is far left away from the wire, and not in the middle of the wire" | The × sat at a fixed spot of the wire's box, not on the wire |
| round 52, 10-16 | "`Name` will reset the value if I don't push enter and just click somewhere else" | Pick-or-type fields kept text only on Enter (the same kind of fault as round 16 and 41) |

## What prevents it now

| What | How | Code |
|---|---|---|
| Typed text stays | every pick-or-type field (variable names, scenes, keys, folders, trigger fields) takes what was typed when he clicks away, not only on Enter | `gui/components/keep_typed.py` |
| Delete a box | a red **Delete box** in its panel; the wires before and after are joined | flow editor |
| Windows stay reachable | the Box window always stays inside the flow area | flow editor |
| The canvas always drags | the whole area drags; letting go anywhere ends a drag (box, wire, view) | flow editor |
| Remove a wire | click near it (a finger width), it turns red, a red × appears where he clicked | flow editor |
| The Add box list keeps its headings | every open heading is known from the start; a click opens, a second click closes | `ActionCatalog` |
| A dropped dot gets its wire | the field takes the dot he dropped, only an empty field, and says so when none is empty | flow editor |
| The Start box is current | adding or deleting a trigger shows on it at once | flow editor |

## How to check it again

- Flow editor tests: `tests/gui/components/flow_editor/`.
- Rule for every new field: type, click somewhere else, the text must still be there.
- GUI changes are checked with screenshots before he sees them (`temp/gui_review/cdp_shot.py`).
