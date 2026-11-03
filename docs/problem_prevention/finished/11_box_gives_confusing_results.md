# 11 · A box gives back something that doesn't fit the next box

## The problem

One box's result goes into the next box. When the result is wrapped in extra parts, or holds a value the
next box can't use, the flow fails on stream with an error he can't read.

## What he told me, and what was wrong

| When | His words | What was wrong |
|---|---|---|
| round 21, 10-02 | "input from boxes always include `@keys`, `@text`. ... which makes no sense if I only get one text item back" | Every result had helper values, also a single text or number |
| round 21, 10-02 | "`create source` gives back an item_id in an object · `get source settings` is getting an error if I give it the ID from `create source`" | Get source settings wants the source's name; OBS's own error didn't say that |

## What prevents it now

| What | How |
|---|---|
| Helpers only where they mean something | a text, number or yes/no has none; an object has @keys, @kinds, @count, @text; a list @kinds, @count, @first, @last, @text |
| Create source gives what the next box needs | `source` (the name), `scene` and `item_id`; the whole result works too |
| A wrong value says what's wrong | an `item_id` where a name belongs says so, instead of OBS's error |

## How to check it again

- Box tests: `tests/connections/obs/`, `tests/core/flows/`.
- The test record (`docs/tested/`): every box is tried for "works, understandable, usable".
